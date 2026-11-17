
use std::io::Read;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicU8, Ordering};
use std::sync::mpsc::{sync_channel, Receiver, SyncSender, TryRecvError};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use anyhow::{anyhow, Result};
use symphonia::core::audio::SampleBuffer;
use symphonia::core::codecs::{DecoderOptions, CODEC_TYPE_NULL};
use symphonia::core::errors::Error as SymError;
use symphonia::core::formats::{FormatOptions, FormatReader, SeekMode, SeekTo};
use symphonia::core::io::{MediaSource, MediaSourceStream, ReadOnlySource};
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

use super::tasofro::{Member, MemberReader};

impl MediaSource for MemberReader {
    fn is_seekable(&self) -> bool {
        true
    }
    fn byte_len(&self) -> Option<u64> {
        Some(self.len())
    }
}

#[derive(Clone)]
pub enum Input {
    Pcm { path: PathBuf, offset: u64, length: u64, channels: u16, bits: u16, rate: u32 },
    File(PathBuf),
    Member(Member),
    Stream { url: String, user_agent: String },
}

const BLOCK_FRAMES: usize = 2048;

trait Decoder: Send {
    fn rate(&self) -> u32;
    fn read(&mut self, out: &mut Vec<f32>, frames: usize) -> Result<usize>;
    fn seek(&mut self, frame: u64) -> Result<()>;
}


struct PcmDecoder {
    file: std::fs::File,
    offset: u64,
    length: u64,
    channels: usize,
    bytes: usize,
    rate: u32,
    pos: u64,
    buf: Vec<u8>,
}

impl PcmDecoder {
    fn frame_bytes(&self) -> u64 {
        (self.channels * self.bytes) as u64
    }
}

impl Decoder for PcmDecoder {
    fn rate(&self) -> u32 {
        self.rate
    }
    fn read(&mut self, out: &mut Vec<f32>, frames: usize) -> Result<usize> {
        use std::io::{Seek, SeekFrom};
        let fb = self.frame_bytes();
        let remaining = self.length.saturating_sub(self.pos) / fb;
        let n = (frames as u64).min(remaining) as usize;
        if n == 0 {
            return Ok(0);
        }
        self.buf.resize(n * fb as usize, 0);
        self.file.seek(SeekFrom::Start(self.offset + self.pos))?;
        self.file.read_exact(&mut self.buf).map_err(|_| anyhow!("The BGM archive ended before the selected track finished."))?;
        self.pos += n as u64 * fb;
        let sample = |b: &[u8]| -> f32 {
            match b.len() {
                1 => (b[0] as f32 - 128.0) / 128.0,
                2 => i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0,
                3 => (i32::from_le_bytes([0, b[0], b[1], b[2]]) >> 8) as f32 / 8_388_608.0,
                _ => i32::from_le_bytes([b[0], b[1], b[2], b[3]]) as f32 / 2_147_483_648.0,
            }
        };
        for frame in self.buf.chunks_exact(fb as usize) {
            let l = sample(&frame[..self.bytes]);
            let r = if self.channels > 1 { sample(&frame[self.bytes..2 * self.bytes]) } else { l };
            out.push(l);
            out.push(r);
        }
        Ok(n)
    }
    fn seek(&mut self, frame: u64) -> Result<()> {
        self.pos = (frame * self.frame_bytes()).min(self.length);
        Ok(())
    }
}


struct SymDecoder {
    format: Box<dyn FormatReader>,
    decoder: Box<dyn symphonia::core::codecs::Decoder>,
    track_id: u32,
    rate: u32,
    pending: Vec<f32>,
    skip_until: Option<u64>,
    seekable: bool,
}

impl SymDecoder {
    fn open(source: Box<dyn MediaSource>, ext: Option<&str>, seekable: bool) -> Result<Self> {
        let mss = MediaSourceStream::new(source, Default::default());
        let mut hint = Hint::new();
        if let Some(ext) = ext {
            hint.with_extension(ext);
        }
        let probed = symphonia::default::get_probe()
            .format(&hint, mss, &FormatOptions { enable_gapless: true, ..Default::default() }, &MetadataOptions::default())
            .map_err(|e| anyhow!("Unsupported audio data ({e})"))?;
        let format = probed.format;
        let track = format
            .tracks()
            .iter()
            .find(|t| t.codec_params.codec != CODEC_TYPE_NULL)
            .ok_or_else(|| anyhow!("No audio track found"))?;
        let rate = track.codec_params.sample_rate.unwrap_or(44100);
        let track_id = track.id;
        let decoder = symphonia::default::get_codecs()
            .make(&track.codec_params, &DecoderOptions::default())
            .map_err(|e| anyhow!("Unsupported audio codec ({e})"))?;
        Ok(SymDecoder { format, decoder, track_id, rate, pending: Vec::new(), skip_until: None, seekable })
    }

    fn decode_packet(&mut self) -> Result<bool> {
        loop {
            let packet = match self.format.next_packet() {
                Ok(p) => p,
                Err(SymError::IoError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => return Ok(false),
                Err(SymError::ResetRequired) => {
                    self.decoder.reset();
                    continue;
                }
                Err(e) => return Err(anyhow!("{e}")),
            };
            if packet.track_id() != self.track_id {
                continue;
            }
            let ts = packet.ts();
            let decoded = match self.decoder.decode(&packet) {
                Ok(d) => d,
                Err(SymError::DecodeError(_)) => continue,
                Err(SymError::IoError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => return Ok(false),
                Err(e) => return Err(anyhow!("{e}")),
            };
            let spec = *decoded.spec();
            let frames = decoded.frames();
            if frames == 0 {
                continue;
            }
            let mut sb = SampleBuffer::<f32>::new(decoded.capacity() as u64, spec);
            sb.copy_interleaved_ref(decoded);
            let ch = spec.channels.count().max(1);
            let mut skip = 0usize;
            if let Some(target) = self.skip_until {
                if ts + frames as u64 <= target {
                    continue;
                }
                skip = target.saturating_sub(ts) as usize;
                self.skip_until = None;
            }
            for frame in sb.samples().chunks_exact(ch).skip(skip) {
                let l = frame[0];
                let r = if ch > 1 { frame[1] } else { l };
                self.pending.push(l);
                self.pending.push(r);
            }
            return Ok(true);
        }
    }
}

impl Decoder for SymDecoder {
    fn rate(&self) -> u32 {
        self.rate
    }
    fn read(&mut self, out: &mut Vec<f32>, frames: usize) -> Result<usize> {
        while self.pending.len() < frames * 2 {
            if !self.decode_packet()? {
                break;
            }
        }
        let take = (frames * 2).min(self.pending.len());
        out.extend(self.pending.drain(..take));
        Ok(take / 2)
    }
    fn seek(&mut self, frame: u64) -> Result<()> {
        if !self.seekable {
            return Ok(());
        }
        self.pending.clear();
        let seeked = self
            .format
            .seek(SeekMode::Accurate, SeekTo::TimeStamp { ts: frame, track_id: self.track_id })
            .map_err(|e| anyhow!("Seek failed ({e})"))?;
        self.decoder.reset();
        self.skip_until = Some(seeked.required_ts);
        Ok(())
    }
}

fn open_decoder(input: &Input) -> Result<Box<dyn Decoder>> {
    match input {
        Input::Pcm { path, offset, length, channels, bits, rate } => Ok(Box::new(PcmDecoder {
            file: std::fs::File::open(path).map_err(|e| anyhow!("Missing BGM archive: {} ({e})", path.display()))?,
            offset: *offset,
            length: *length,
            channels: (*channels).max(1) as usize,
            bytes: ((*bits as usize) / 8).clamp(1, 4),
            rate: *rate,
            pos: 0,
            buf: Vec::new(),
        })),
        Input::File(path) => {
            let ext = path.extension().map(|e| e.to_string_lossy().to_lowercase());
            let file = std::fs::File::open(path)?;
            Ok(Box::new(SymDecoder::open(Box::new(file), ext.as_deref(), true)?))
        }
        Input::Member(member) => Ok(Box::new(SymDecoder::open(Box::new(MemberReader::new(member.clone())?), Some("ogg"), true)?)),
        Input::Stream { url, user_agent } => {
            let resp = ureq::AgentBuilder::new()
                .timeout_connect(Duration::from_secs(15))
                .timeout_read(Duration::from_secs(20))
                .build()
                .get(url)
                .set("User-Agent", user_agent)
                .call()
                .map_err(|e| anyhow!("{e}"))?;
            let reader = resp.into_reader();
            Ok(Box::new(SymDecoder::open(Box::new(ReadOnlySource::new(reader)), Some("mp3"), false)?))
        }
    }
}


struct Resampler {
    step: f64,
    pos: f64,
    buf: Vec<[f32; 2]>,
}

impl Resampler {
    fn new(in_rate: u32, out_rate: u32) -> Self {
        Resampler { step: in_rate as f64 / out_rate as f64, pos: 1.0, buf: vec![[0.0; 2]] }
    }

    fn reset(&mut self) {
        self.pos = 1.0;
        self.buf.clear();
        self.buf.push([0.0; 2]);
    }

    fn passthrough(&self) -> bool {
        (self.step - 1.0).abs() < 1e-9
    }

    fn process(&mut self, input: &[f32], out: &mut Vec<f32>) {
        if self.passthrough() {
            out.extend_from_slice(input);
            return;
        }
        if self.buf.len() == 1 && self.buf[0] == [0.0; 2] && !input.is_empty() {
            self.buf[0] = [input[0], input[1]];
        }
        self.buf.extend(input.chunks_exact(2).map(|c| [c[0], c[1]]));
        while self.pos + 2.0 < self.buf.len() as f64 {
            let i = self.pos.floor() as usize;
            let t = (self.pos - i as f64) as f32;
            for c in 0..2 {
                let (y0, y1, y2, y3) = (self.buf[i - 1][c], self.buf[i][c], self.buf[i + 1][c], self.buf[i + 2][c]);
                let c0 = y1;
                let c1 = 0.5 * (y2 - y0);
                let c2 = y0 - 2.5 * y1 + 2.0 * y2 - 0.5 * y3;
                let c3 = 0.5 * (y3 - y0) + 1.5 * (y1 - y2);
                out.push(((c3 * t + c2) * t + c1) * t + c0);
            }
            self.pos += self.step;
        }
        let drop = (self.pos.floor() as usize).saturating_sub(1);
        if drop > 0 {
            self.buf.drain(..drop.min(self.buf.len()));
            self.pos -= drop as f64;
        }
    }
}


#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum State {
    Buffering = 0,
    Playing = 1,
    Ended = 2,
    Failed = 3,
}

struct Chunk {
    gen: u64,
    start: f64,
    data: Vec<f32>,
    wrapped: bool,
    end: Option<Option<String>>,
}

struct Shared {
    gen: AtomicU64,
    seek: Mutex<Option<(f64, u64)>>,
    loop_region: Mutex<Option<(f64, f64)>>,
    position_us: AtomicU64,
    state: AtomicU8,
    error: Mutex<Option<String>>,
    wraps: AtomicU64,
    stop: AtomicBool,
}

fn decode_thread(input: Input, out_rate: u32, shared: Arc<Shared>, tx: SyncSender<Chunk>) {
    let fail = |msg: String| {
        let _ = tx.send(Chunk { gen: u64::MAX, start: 0.0, data: Vec::new(), wrapped: false, end: Some(Some(msg)) });
    };
    let mut decoder = match open_decoder(&input) {
        Ok(d) => d,
        Err(e) => return fail(e.to_string()),
    };
    let rate = decoder.rate().max(1);
    let mut resampler = Resampler::new(rate, out_rate);
    let mut gen = shared.gen.load(Ordering::SeqCst);
    let mut frame: u64 = 0;
    let mut raw = Vec::with_capacity(BLOCK_FRAMES * 2);
    let mut wrapped = false;
    loop {
        if shared.stop.load(Ordering::Relaxed) {
            return;
        }
        if let Some((secs, g)) = shared.seek.lock().unwrap().take() {
            let target = (secs.max(0.0) * rate as f64).round() as u64;
            if let Err(e) = decoder.seek(target) {
                return fail(e.to_string());
            }
            frame = target;
            gen = g;
            resampler.reset();
            wrapped = false;
        }
        let region = *shared.loop_region.lock().unwrap();
        let region = region.map(|(s, e)| ((s * rate as f64).round() as u64, (e * rate as f64).round() as u64));
        if let Some((ls, le)) = region {
            if frame >= le {
                if let Err(e) = decoder.seek(ls) {
                    return fail(e.to_string());
                }
                frame = ls;
                wrapped = true;
            }
        }
        let mut want = BLOCK_FRAMES;
        if let Some((_, le)) = region {
            want = want.min((le - frame) as usize).max(1);
        }
        raw.clear();
        let n = match decoder.read(&mut raw, want) {
            Ok(n) => n,
            Err(e) => return fail(e.to_string()),
        };
        if n == 0 {
            if let Some((ls, le)) = region {
                if frame > ls && le > ls {
                    if let Err(e) = decoder.seek(ls) {
                        return fail(e.to_string());
                    }
                    frame = ls;
                    wrapped = true;
                    continue;
                }
            }
            let _ = tx.send(Chunk { gen, start: frame as f64 / rate as f64, data: Vec::new(), wrapped: false, end: Some(None) });
            return;
        }
        let mut data = Vec::with_capacity(raw.len() * out_rate as usize / rate as usize + 8);
        resampler.process(&raw, &mut data);
        let chunk = Chunk { gen, start: frame as f64 / rate as f64, data, wrapped, end: None };
        wrapped = false;
        frame += n as u64;
        if tx.send(chunk).is_err() {
            return;
        }
    }
}

struct EngineSource {
    rx: Receiver<Chunk>,
    shared: Arc<Shared>,
    rate: u32,
    cur: Vec<f32>,
    idx: usize,
    start: f64,
    pair_silence: bool,
    done: bool,
}

impl EngineSource {
    fn pull(&mut self) -> bool {
        loop {
            match self.rx.try_recv() {
                Ok(chunk) => {
                    if let Some(end) = chunk.end {
                        if chunk.gen != u64::MAX && chunk.gen != self.shared.gen.load(Ordering::SeqCst) {
                            continue;
                        }
                        match end {
                            Some(err) => {
                                *self.shared.error.lock().unwrap() = Some(err);
                                self.shared.state.store(State::Failed as u8, Ordering::SeqCst);
                            }
                            None => self.shared.state.store(State::Ended as u8, Ordering::SeqCst),
                        }
                        self.done = true;
                        return false;
                    }
                    if chunk.gen != self.shared.gen.load(Ordering::SeqCst) {
                        continue;
                    }
                    if chunk.data.is_empty() {
                        continue;
                    }
                    if chunk.wrapped {
                        self.shared.wraps.fetch_add(1, Ordering::SeqCst);
                    }
                    self.cur = chunk.data;
                    self.idx = 0;
                    self.start = chunk.start;
                    self.shared.state.store(State::Playing as u8, Ordering::SeqCst);
                    return true;
                }
                Err(TryRecvError::Empty) => return false,
                Err(TryRecvError::Disconnected) => {
                    self.done = true;
                    return false;
                }
            }
        }
    }
}

impl Iterator for EngineSource {
    type Item = f32;
    fn next(&mut self) -> Option<f32> {
        if self.pair_silence {
            self.pair_silence = false;
            return Some(0.0);
        }
        if self.idx >= self.cur.len() {
            if self.done {
                return None;
            }
            if !self.pull() {
                if self.done {
                    return None;
                }
                self.pair_silence = true;
                return Some(0.0);
            }
        }
        let s = self.cur[self.idx];
        self.idx += 1;
        if self.idx % 64 == 0 || self.idx == self.cur.len() {
            let t = self.start + (self.idx / 2) as f64 / self.rate as f64;
            self.shared.position_us.store((t * 1e6) as u64, Ordering::Relaxed);
        }
        Some(s)
    }
}

impl rodio::Source for EngineSource {
    fn current_frame_len(&self) -> Option<usize> {
        None
    }
    fn channels(&self) -> u16 {
        2
    }
    fn sample_rate(&self) -> u32 {
        self.rate
    }
    fn total_duration(&self) -> Option<Duration> {
        None
    }
}

pub struct Playback {
    sink: rodio::Sink,
    shared: Arc<Shared>,
    seen_wraps: u64,
}

impl Playback {
    pub fn pause(&self) {
        self.sink.pause();
    }
    pub fn resume(&self) {
        self.sink.play();
    }
    pub fn is_paused(&self) -> bool {
        self.sink.is_paused()
    }
    pub fn set_volume(&self, v: f32) {
        self.sink.set_volume(v);
    }
    pub fn position(&self) -> f64 {
        self.shared.position_us.load(Ordering::Relaxed) as f64 / 1e6
    }
    pub fn state(&self) -> State {
        match self.shared.state.load(Ordering::SeqCst) {
            1 => State::Playing,
            2 => State::Ended,
            3 => State::Failed,
            _ => State::Buffering,
        }
    }
    pub fn error(&self) -> Option<String> {
        self.shared.error.lock().unwrap().clone()
    }
    pub fn seek(&self, seconds: f64) {
        let mut seek = self.shared.seek.lock().unwrap();
        let gen = self.shared.gen.fetch_add(1, Ordering::SeqCst) + 1;
        *seek = Some((seconds, gen));
        self.shared.position_us.store((seconds.max(0.0) * 1e6) as u64, Ordering::Relaxed);
    }
    pub fn set_loop(&self, region: Option<(f64, f64)>) {
        *self.shared.loop_region.lock().unwrap() = region;
    }
    pub fn take_wrapped(&mut self) -> bool {
        let w = self.shared.wraps.load(Ordering::SeqCst);
        let changed = w != self.seen_wraps;
        self.seen_wraps = w;
        changed
    }
}

impl Drop for Playback {
    fn drop(&mut self) {
        self.shared.stop.store(true, Ordering::Relaxed);
        self.sink.stop();
    }
}

pub struct Engine {
    _keep_alive: std::sync::mpsc::Sender<()>,
    handle: rodio::OutputStreamHandle,
    rate: u32,
}

impl Engine {
    pub fn new() -> Result<Engine> {
        let (ready_tx, ready_rx) = std::sync::mpsc::sync_channel(1);
        let (keep_tx, keep_rx) = std::sync::mpsc::channel::<()>();
        std::thread::Builder::new().name("audio-output".into()).spawn(move || {
            use rodio::cpal::traits::{DeviceTrait, HostTrait};
            match rodio::OutputStream::try_default() {
                Ok((stream, handle)) => {
                    let rate = rodio::cpal::default_host()
                        .default_output_device()
                        .and_then(|d| d.default_output_config().ok())
                        .map(|c| c.sample_rate().0)
                        .unwrap_or(48000);
                    if ready_tx.send(Ok((handle, rate))).is_ok() {
                        let _ = keep_rx.recv();
                    }
                    drop(stream);
                }
                Err(e) => {
                    let _ = ready_tx.send(Err(anyhow!("No audio output device ({e})")));
                }
            }
        })?;
        let (handle, rate) = ready_rx.recv().map_err(|_| anyhow!("The audio output stopped unexpectedly"))??;
        Ok(Engine { _keep_alive: keep_tx, handle, rate })
    }

    pub fn play(&self, input: Input, start_at: f64, loop_region: Option<(f64, f64)>, volume: f32, paused: bool) -> Result<Playback> {
        let sink = rodio::Sink::try_new(&self.handle).map_err(|e| anyhow!("{e}"))?;
        sink.set_volume(volume);
        if paused {
            sink.pause();
        }
        let shared = Arc::new(Shared {
            gen: AtomicU64::new(0),
            seek: Mutex::new(None),
            loop_region: Mutex::new(loop_region),
            position_us: AtomicU64::new(0),
            state: AtomicU8::new(State::Buffering as u8),
            error: Mutex::new(None),
            wraps: AtomicU64::new(0),
            stop: AtomicBool::new(false),
        });
        let (tx, rx) = sync_channel::<Chunk>(12);
        let rate = self.rate;
        {
            let shared = shared.clone();
            std::thread::Builder::new().name("audio-decode".into()).spawn(move || {
                let tx2 = tx.clone();
                let run = std::panic::AssertUnwindSafe(move || decode_thread(input, rate, shared, tx));
                if std::panic::catch_unwind(run).is_err() {
                    let _ = tx2.send(Chunk {
                        gen: u64::MAX,
                        start: 0.0,
                        data: Vec::new(),
                        wrapped: false,
                        end: Some(Some("The audio decoder failed on this file.".into())),
                    });
                }
            })?;
        }
        let playback = Playback { sink, shared: shared.clone(), seen_wraps: 0 };
        if start_at > 0.0 {
            playback.seek(start_at);
        }
        playback.sink.append(EngineSource {
            rx,
            shared,
            rate,
            cur: Vec::new(),
            idx: 0,
            start: start_at,
            pair_silence: false,
            done: false,
        });
        Ok(playback)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resampler_length() {
        let mut r = Resampler::new(44100, 48000);
        let input = vec![0.5f32; 44100 * 2];
        let mut out = Vec::new();
        r.process(&input, &mut out);
        let frames = out.len() / 2;
        assert!((47990..=48000).contains(&frames), "{frames}");
        assert!(out.iter().all(|&s| (s - 0.5).abs() < 1e-4));
    }
}

pub fn probe_decode(input: &Input, start: f64, seconds: f64, seek_to: Option<f64>) -> Result<(u64, f32)> {
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| probe_inner(input, start, seconds, seek_to)))
        .unwrap_or_else(|_| Err(anyhow!("decoder panicked")))
}

fn probe_inner(input: &Input, start: f64, seconds: f64, seek_to: Option<f64>) -> Result<(u64, f32)> {
    let mut d = open_decoder(input)?;
    let rate = d.rate() as f64;
    if start > 0.0 {
        d.seek((start * rate) as u64)?;
    }
    let mut total = 0u64;
    let mut peak = 0f32;
    let mut buf = Vec::new();
    let mut run = |d: &mut Box<dyn Decoder>, secs: f64, total: &mut u64, peak: &mut f32| -> Result<()> {
        let want = (secs * rate) as u64;
        let mut got = 0;
        while got < want {
            buf.clear();
            let n = d.read(&mut buf, BLOCK_FRAMES)?;
            if n == 0 {
                break;
            }
            got += n as u64;
            *peak = buf.iter().fold(*peak, |m, s| m.max(s.abs()));
        }
        *total += got;
        Ok(())
    };
    run(&mut d, seconds, &mut total, &mut peak)?;
    if let Some(t) = seek_to {
        d.seek((t * rate) as u64)?;
        run(&mut d, 1.0, &mut total, &mut peak)?;
    }
    Ok((total, peak))
}
