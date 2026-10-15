
import struct
from pathlib import Path


def ogg_info(read, size):

    header = read(0, min(size, 4096))
    if header[:5] != b'OggS\0' or len(header) < 28:
        raise ValueError('Invalid Ogg header')
    serial = header[14:18]
    start = 27 + header[26]
    if header[start:start + 7] != b'\x01vorbis' or len(header) < start + 30:
        raise ValueError('Expected Vorbis identification packet')
    channels = header[start + 11]
    rate = struct.unpack_from('<I', header, start + 12)[0]
    if not rate or not channels:
        raise ValueError('Invalid Vorbis audio format')

    tail = read(max(0, size - 131072), min(size, 131072))
    pos = len(tail)
    while True:
        pos = tail.rfind(b'OggS\0', 0, pos)
        if pos < 0:
            raise ValueError('Missing final Ogg page')
        if pos + 27 > len(tail) or tail[pos + 14:pos + 18] != serial or not tail[pos + 5] & 4:
            continue
        segments = tail[pos + 26]
        end_header = pos + 27 + segments
        if end_header > len(tail):
            continue
        end = end_header + sum(tail[pos + 27:end_header])
        if end != len(tail):
            continue
        samples = struct.unpack_from('<q', tail, pos + 6)[0]
        if samples <= 0:
            raise ValueError('Invalid Ogg sample count')
        return samples / rate, rate, channels


def ogg_file_info(path):
    with open(path, 'rb') as f:
        def read(start, length):
            f.seek(start)
            return f.read(length)
        return ogg_info(read, Path(path).stat().st_size)


def riff_loop(read, size, rate):

    if read(0, 4) != b'RIFF':
        return 0.0, 0.0
    cues, lengths = {}, {}
    pos = 12
    while pos + 8 <= size:
        header = read(pos, 8)
        if len(header) != 8:
            break
        tag, length = struct.unpack('<4sI', header)
        if pos + 8 + length > size:
            break
        if tag == b'cue ' and length >= 4 and length <= 65536:
            chunk = read(pos + 8, length)
            for i in range(min(struct.unpack_from('<I', chunk)[0], (length - 4) // 24)):
                ident, _, _, _, _, sample = struct.unpack_from('<II4sIII', chunk, 4 + i * 24)
                cues[ident] = sample
        elif tag == b'LIST' and length <= 65536:
            chunk = read(pos + 8, length)
            if chunk[:4] == b'adtl':
                p = 4
                while p + 8 <= len(chunk):
                    kind, n = struct.unpack_from('<4sI', chunk, p)
                    if p + 8 + n > len(chunk):
                        break
                    if kind == b'ltxt' and n >= 8:
                        ident, samples = struct.unpack_from('<II', chunk, p + 8)
                        lengths[ident] = samples
                    p += 8 + n + n % 2
        pos += 8 + length + length % 2
    for ident, start in cues.items():
        if lengths.get(ident, 0) > 0:
            return start / rate, (start + lengths[ident]) / rate
    return 0.0, 0.0


def file_loop(path, rate):
    with open(path, 'rb') as f:
        def read(start, length):
            f.seek(start)
            return f.read(length)
        return riff_loop(read, Path(path).stat().st_size, rate)
