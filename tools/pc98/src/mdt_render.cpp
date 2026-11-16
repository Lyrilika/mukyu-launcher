#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
extern "C" {
#include "x86emu.h"
}
#include "opna_audio.h"

static const int RATE = 44100;
static const uint32_t CLOCK = 7987200;
static const double GAIN = 0.7;

struct Machine {
    x86emu_t *emu;
    Pc98Synth opna;
    uint8_t addr1 = 0, addr2 = 0;
    uint8_t pic_mask_m = 0xff, pic_mask_s = 0xff;
    bool stop_flag = false, armed = false, left = false;
    bool trace = false;
    x86emu_memio_handler_t orig_memio;
    std::vector<int16_t> pcm;
    double us_acc = 0;
    long frames = 0;
    long pos = 0;
    bool mix = true;
    std::map<uint32_t, long> first_visit;
    struct LoopEv { unsigned si; long start, end; };
    std::vector<LoopEv> loops;
    std::set<unsigned> ended;
    std::set<unsigned> seen_ch;
} M;

#define IDLE_SEG 0xF000
#define IDLE_OFF 0x0010

static int unhandled21 = 0;

static unsigned memio(x86emu_t *emu, u32 addr, u32 *val, unsigned type) {
    unsigned kind = type & ~0xffu & 0xff00;
    unsigned bits = type & 0xff;
    if (kind == X86EMU_MEMIO_I || kind == X86EMU_MEMIO_O) {
        bool out = kind == X86EMU_MEMIO_O;
        uint32_t port = addr & 0xffff;
        if (out) {
            uint8_t v = *val & 0xff;
            if (M.trace && port != 0x5f) fprintf(stderr, "OUT %04x <- %02x\n", port, v);
            switch (port) {
            case 0x188: M.addr1 = v; break;
            case 0x18a: M.opna.SetReg(M.addr1, v); if (M.trace) fprintf(stderr, "W1 %02x=%02x\n", M.addr1, v); break;
            case 0x18c: M.addr2 = v; break;
            case 0x18e: M.opna.SetReg(0x100 | M.addr2, v); if (M.trace) fprintf(stderr, "W2 %02x=%02x\n", M.addr2, v); break;
            case 0x02: M.pic_mask_m = v; break;
            case 0x0a: M.pic_mask_s = v; break;
            default: break;
            }
        } else {
            uint32_t v = 0xff;
            if (M.trace && (port & 0xf000) == 0 ) {}
            switch (port) {
            case 0x188: v = M.opna.ReadStatus() & 0x03; break;
            case 0x18a:
                if (M.addr1 == 0x0e) v = 0x00;
                else if (M.addr1 == 0xff) v = 0x01;
                else v = M.opna.GetReg(M.addr1);
                break;
            case 0x18c: v = 0x00; break;
            case 0x18e: v = 0x00; break;
            case 0x588: case 0x58a: case 0x58c: case 0x58e: v = 0xff; break;
            case 0x02: v = M.pic_mask_m; break;
            case 0x0a: v = M.pic_mask_s; break;
            case 0x00: case 0x08: v = 0; break;
            default: v = 0xff; break;
            }
            if (M.trace) fprintf(stderr, "IN %04x -> %02x\n", port, v);
            *val = bits == X86EMU_MEMIO_16 ? (v | 0xff00) : v;
        }
        return 0;
    }
    return M.orig_memio(emu, addr, val, type);
}

static int code_check(x86emu_t *emu) {
    if (M.stop_flag) return 1;
    if (emu->x86.R_CS == 0x1000) {
        unsigned ip = emu->x86.R_IP;
        if (ip == 0xb1f) {
            unsigned si = emu->x86.R_SI, bx = emu->x86.R_BX;
            M.seen_ch.insert(si);
            M.first_visit.emplace((si << 16) | bx, M.pos);
        } else if (ip == 0x1513) {
            unsigned si = emu->x86.R_SI, bx = emu->x86.R_BX;
            unsigned target = (bx + 1 + x86emu_read_word(emu, emu->x86.R_DS_BASE + bx)) & 0xffff;
            auto it = M.first_visit.find((si << 16) | target);
            bool dup = false; for (auto &l : M.loops) if (l.si == si) dup = true;
            if (!dup) M.loops.push_back({si, it == M.first_visit.end() ? 0 : it->second, M.pos});
        } else if (ip == 0x1828) {
            M.ended.insert(emu->x86.R_SI);
        }
    }
    bool at_idle = emu->x86.R_CS == IDLE_SEG && emu->x86.R_IP == IDLE_OFF;
    if (!M.armed) return 0;
    if (!at_idle) M.left = true;
    else if (M.left) return 1;
    return 0;
}

static void set_ivt(unsigned n, unsigned seg, unsigned off) {
    x86emu_write_word(M.emu, n * 4, off);
    x86emu_write_word(M.emu, n * 4 + 2, seg);
}

static int intr21(x86emu_t *emu, u8 num, unsigned type) {
    auto &x = emu->x86;
    if (num == 0x20) { M.stop_flag = true; return 1; }
    if (num != 0x21) return 0;
    unsigned ah = x.R_AH;
    switch (ah) {
    case 0x09: {
        unsigned a = x.R_DS_BASE + x.R_DX; std::string s;
        for (int i = 0; i < 400; i++) { int c = x86emu_read_byte(emu, a + i); if (c == '$') break; s += (char)c; }
        if (M.trace) fprintf(stderr, "[DOS print] %s\n", s.c_str());
        return 1; }
    case 0x25: set_ivt(x.R_AL, x.R_DS, x.R_DX); return 1;
    case 0x35: x.R_BX = x86emu_read_word(emu, x.R_AL * 4); x86emu_set_seg_register(emu, x.R_ES_SEL, x86emu_read_word(emu, x.R_AL * 4 + 2)); return 1;
    case 0x31: case 0x4c: M.stop_flag = true; return 1;
    case 0x30: x.R_AX = 0x0006; return 1;
    default:
        if (M.trace) fprintf(stderr, "[INT21 AH=%02x unhandled]\n", ah);
        unhandled21++;
        return 1;
    }
}

static void run_until_idle(unsigned long max_instr = 20000000UL) {
    M.armed = true; M.stop_flag = false; M.left = false;
    M.emu->max_instr = M.emu->x86.R_TSC + max_instr;
    x86emu_run(M.emu, X86EMU_RUN_MAX_INSTR);
    M.armed = false;
}

static void begin_call_at_idle() {
    auto &x = M.emu->x86;
    x86emu_set_seg_register(M.emu, x.R_CS_SEL, IDLE_SEG);
    x.R_EIP = IDLE_OFF;
    x86emu_set_seg_register(M.emu, x.R_SS_SEL, 0x2000);
    x.R_SP = 0xfff0;
    x.R_FLG |= 0x200;
}

static void soft_int(unsigned n) {
    begin_call_at_idle();
    x86emu_intr_raise(M.emu, n, INTR_TYPE_SOFT, 0);
    run_until_idle();
}

static void write_wav(const char *path, const std::vector<int16_t> &pcm) {
    FILE *f = fopen(path, "wb"); if (!f) { perror(path); exit(5); }
    auto p16 = [&](unsigned v) { fputc(v & 255, f); fputc((v >> 8) & 255, f); };
    auto p32 = [&](unsigned v) { p16(v & 0xffff); p16(v >> 16); };
    unsigned bytes = pcm.size() * 2;
    fwrite("RIFF", 1, 4, f); p32(36 + bytes); fwrite("WAVEfmt ", 1, 8, f); p32(16);
    p16(1); p16(2); p32(RATE); p32(RATE * 4); p16(4); p16(16);
    fwrite("data", 1, 4, f); p32(bytes); fwrite(pcm.data(), 2, pcm.size(), f); fclose(f);
}

#ifdef _WIN32
#define PATH_SEPS "/\\"
static bool is_sep(char c) { return c == '/' || c == '\\'; }
#else
#define PATH_SEPS "/"
static bool is_sep(char c) { return c == '/'; }
#endif

static std::string with_slash(std::string d) { if (d.empty()) return "./"; if (!is_sep(d.back())) d += '/'; return d; }

static std::vector<uint8_t> slurp(const char *p) {
    std::vector<uint8_t> v; FILE *f = fopen(p, "rb"); if (!f) return v;
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET); v.resize(n); if (fread(v.data(), 1, n, f) != (size_t)n) v.clear(); fclose(f); return v;
}

static int irq_vector = 0x0b;
static int irq_count = 0;
static bool dump_state = false;
static bool no_finish = false;
static bool finished() {
    if (no_finish) return false;
    if (M.seen_ch.empty()) return false;
    std::set<unsigned> done = M.ended; for (auto &l : M.loops) done.insert(l.si);
    return done.size() >= M.seen_ch.size();
}
static void advance(long frames) {
    const int CH = 64;
    long done = 0;
    std::vector<int32_t> buf(CH * 2);
    while (done < frames) {
        int n = (int)std::min<long>(CH, frames - done);
        M.us_acc += n * 1e6 / RATE;
        int us = (int)M.us_acc; M.us_acc -= us;
        M.opna.Count(us);
        if ((M.opna.ReadStatus() & 3) && (M.opna.GetReg(0x29) & 3 || true)) {

            begin_call_at_idle();
            x86emu_intr_raise(M.emu, irq_vector, INTR_TYPE_SOFT, 0);
            run_until_idle(2000000);
            irq_count++;
            if (dump_state && irq_count % 20 == 0) { printf("t=%.3f", M.pcm.size()/2.0/RATE); for (int c = 0; c < 2; c++) { printf(" |"); for (int o = 0; o < 64; o += 2) printf(" %04x", x86emu_read_word(M.emu, 0x10000 + 0x260 + c*0x40 + o)); } printf("\n"); }
        }
        M.pos += n;
        if (!M.mix) { done += n; if (finished()) break; continue; }
        memset(buf.data(), 0, buf.size() * sizeof(int32_t));
        M.opna.Mix(buf.data(), n);
        for (int i = 0; i < n * 2; i++) {
            int v = (int)(buf[i] * GAIN);
            if (v > 32767) v = 32767; if (v < -32768) v = -32768;
            M.pcm.push_back((int16_t)v);
        }
        done += n;
        if (finished()) break;
    }
}

int main(int argc, char **argv) {
    std::string mode, song, out, driver, rhythm = "./";
    double secs = 400;
    if (argc < 3) { fprintf(stderr, "usage: mdt_render --info SONG --driver MDRV98.COM [--secs N]\n       mdt_render --render SONG OUT --driver MDRV98.COM [--rhythm DIR] [--secs N] [--trace]\n"); return 64; }
    mode = argv[1]; song = argv[2];
    int first_opt = 3;
    if (mode == "--render") { if (argc < 4) return 64; out = argv[3]; first_opt = 4; }
    else if (mode != "--info") return 64;
    for (int i = first_opt; i < argc; i++) {
        std::string k = argv[i];
        if (k == "--driver" && i + 1 < argc) driver = argv[++i];
        else if (k == "--rhythm" && i + 1 < argc) rhythm = with_slash(argv[++i]);
        else if (k == "--secs" && i + 1 < argc) secs = atof(argv[++i]);
        else if (k == "--trace") M.trace = true;
        else if (k == "--dump") dump_state = true;
    }
    auto com = slurp(driver.c_str()); auto mdt = slurp(song.c_str());
    if (com.empty()) { fprintf(stderr, "cannot read driver\n"); return 2; }
    if (mdt.empty()) { fprintf(stderr, "cannot read song\n"); return 2; }

    M.emu = x86emu_new(X86EMU_PERM_RWX | X86EMU_PERM_VALID, X86EMU_PERM_RW);
    M.orig_memio = x86emu_set_memio_handler(M.emu, memio);
    x86emu_set_intr_handler(M.emu, intr21);
    x86emu_set_code_handler(M.emu, code_check);
    M.opna.Init(CLOCK, RATE, true, rhythm.c_str());

    x86emu_write_byte(M.emu, 0xF0000, 0xCF);
    x86emu_write_byte(M.emu, 0xF0000 + IDLE_OFF, 0xEB); x86emu_write_byte(M.emu, 0xF0000 + IDLE_OFF + 1, 0xFE);
    for (int i = 0; i < 256; i++) set_ivt(i, 0xF000, 0);

    const unsigned seg = 0x1000;
    for (size_t i = 0; i < com.size(); i++) x86emu_write_byte(M.emu, seg * 16 + 0x100 + i, com[i]);
    x86emu_write_byte(M.emu, seg * 16 + 0, 0xCD); x86emu_write_byte(M.emu, seg * 16 + 1, 0x20);
    x86emu_write_word(M.emu, seg * 16 + 0x2c, 0x0800);
    const char *cmd = " -W0 -M40\r";
    x86emu_write_byte(M.emu, seg * 16 + 0x80, strlen(cmd) - 1);
    for (size_t i = 0; i < strlen(cmd); i++) x86emu_write_byte(M.emu, seg * 16 + 0x81 + i, cmd[i]);
    auto &x = M.emu->x86;
    x86emu_set_seg_register(M.emu, x.R_CS_SEL, seg); x86emu_set_seg_register(M.emu, x.R_DS_SEL, seg);
    x86emu_set_seg_register(M.emu, x.R_ES_SEL, seg); x86emu_set_seg_register(M.emu, x.R_SS_SEL, seg);
    x.R_EIP = 0x100; x.R_SP = 0xfffe; x.R_FLG |= 0x200;
    x86emu_write_word(M.emu, seg * 16 + 0xfffe, 0);
    M.armed = false; M.stop_flag = false;
    M.emu->max_instr = 50000000;
    x86emu_run(M.emu, X86EMU_RUN_MAX_INSTR);
    if (!M.stop_flag) { fprintf(stderr, "driver install did not finish\n"); x86emu_dump(M.emu, X86EMU_DUMP_REGS); return 3; }
    unsigned f2seg = x86emu_read_word(M.emu, 0xF2 * 4 + 2), f2off = x86emu_read_word(M.emu, 0xF2 * 4);
    if (M.trace) fprintf(stderr, "INT F2h -> %04x:%04x\n", f2seg, f2off);

    irq_vector = -1;
    for (int i = 0; i < 256; i++) {
        if (i == 0xF2 || i == 0xF3) continue;
        unsigned s = x86emu_read_word(M.emu, i * 4 + 2);
        if (s == seg) { irq_vector = i; break; }
    }
    if (M.trace) fprintf(stderr, "IRQ vector 0x%02x\n", irq_vector);
    if (irq_vector < 0) { fprintf(stderr, "driver hooked no IRQ\n"); return 3; }

    x.R_AX = 0x0900; soft_int(0xF2);
    if (M.trace) fprintf(stderr, "board check AX=%04x\n", x.R_AX);

    const unsigned sseg = 0x3000;
    for (size_t i = 0; i < mdt.size(); i++) x86emu_write_byte(M.emu, sseg * 16 + i, mdt[i]);
    begin_call_at_idle();
    x86emu_set_seg_register(M.emu, x.R_DS_SEL, sseg); x.R_SI = 0; x.R_AX = 0x0600;
    x86emu_intr_raise(M.emu, 0xF2, INTR_TYPE_SOFT, 0); run_until_idle();
    if (M.trace) fprintf(stderr, "MSET AX=%04x\n", x.R_AX);
    x86emu_set_seg_register(M.emu, x.R_DS_SEL, seg);
    begin_call_at_idle(); x.R_AX = 0x0000; x86emu_intr_raise(M.emu, 0xF2, INTR_TYPE_SOFT, 0); run_until_idle();

    bool info = (mode == "--info");
    M.mix = !info;
    advance((long)(secs * RATE));
    long loop_start = 0, loop_end = 0;
    if (!M.loops.empty()) {

        long smax = 0, pmax = 0;
        for (auto &l : M.loops) { smax = std::max(smax, l.start); pmax = std::max(pmax, l.end - l.start); }
        long L = pmax; const long tol = RATE / 25;
        for (int k = 1; k <= 16; k++) {
            long cand = pmax * k; bool ok = true;
            for (auto &l : M.loops) {
                long p = l.end - l.start; long n = (cand + p / 2) / p; if (n < 1) n = 1;
                if (labs(cand - n * p) > tol * std::max(1L, n / 2)) { ok = false; break; }
            }
            if (ok) { L = cand; break; }
        }
        loop_start = smax; loop_end = smax + L;
        if (loop_end < M.pos) loop_end = M.pos;
        if (M.trace) fprintf(stderr, "period max %.3f -> L %.3f, loop %.3f..%.3f\n", pmax / (double)RATE, L / (double)RATE, loop_start / (double)RATE, loop_end / (double)RATE);
        if (loop_end > M.pos) { no_finish = true; advance(loop_end - M.pos); }
    }
    bool looped = !M.loops.empty();
    long total = looped ? loop_end : M.pos;
    if (info) {
        printf("LOOPED=%d\nLENGTH_MS=%ld\nLOOP_START_MS=%ld\nLOOP_END_MS=%ld\nCHANNELS=%zu\n", looped ? 1 : 0,
               total * 1000 / RATE, looped ? loop_start * 1000 / RATE : 0, looped ? loop_end * 1000 / RATE : 0, M.seen_ch.size());
        return 0;
    }
    if (!looped) {
        no_finish = true;
        advance(RATE * 3 / 2);
        total = M.pos;
    }
    if ((long)M.pcm.size() / 2 > total) M.pcm.resize(total * 2);
    if (M.trace) fprintf(stderr, "irq count %d, frames %zu, unhandled21 %d\n", irq_count, M.pcm.size() / 2, unhandled21);
    write_wav(out.c_str(), M.pcm);
    return 0;
}
