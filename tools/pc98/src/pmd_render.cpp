#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include "opna_audio.h"
#include "pmd_driver.h"

static constexpr unsigned RATE = 44100;
static std::vector<uint8_t> read_file(const std::string &path) {
    std::ifstream f(path, std::ios::binary);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(f), {});
}
static void put16(FILE *f, unsigned v) { fputc(v & 255, f); fputc((v >> 8) & 255, f); }
static void put32(FILE *f, unsigned v) { put16(f, v); put16(f, v >> 16); }

struct Player {
    Pc98Synth synth;
    MukyuPmd *driver = nullptr;
    std::vector<uint8_t> data;
    ~Player() { mukyu_pmd_free(driver); }
    bool load(const std::vector<uint8_t> &source, const std::string &pcm) {
        data = source;
        driver = mukyu_pmd_new(data.data(), data.size(), &synth,
            [](void *s, unsigned a) { return static_cast<Pc98Synth *>(s)->read(a); },
            [](void *s, unsigned a, unsigned v) { static_cast<Pc98Synth *>(s)->write(a, v); },
            [](void *s) { return uint8_t(static_cast<Pc98Synth *>(s)->status); });
        if (!driver) return false;
        synth.interrupt = [&]() { mukyu_pmd_interrupt(driver); };
        const char *name = mukyu_pmd_pcm_name(driver);
        if (name && *name) {
            auto samples = read_file(pcm + "/" + name);
            if (!samples.empty()) mukyu_pmd_pcm_load(driver, samples.data(), samples.size());
        }
        return true;
    }
};

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: pmd_render --info|--render SONG [OUT] [--rhythm DIR] [--pcm DIR] [--tail MS]\n"); return 64; }
    std::string mode = argv[1], song = argv[2], out, rhythm = ".";
    size_t slash = song.find_last_of("/\\");
    std::string pcm = slash == std::string::npos ? "." : song.substr(0, slash);
    unsigned tail = 1500;
    int i = 3;
    if (mode == "--render") { if (argc < 4) return 64; out = argv[3]; i = 4; }
    else if (mode != "--info") return 64;
    for (; i + 1 < argc; i += 2) {
        std::string key = argv[i];
        if (key == "--rhythm") rhythm = argv[i + 1];
        else if (key == "--pcm") pcm = argv[i + 1];
        else if (key == "--tail") tail = std::max(0, std::min(60000, atoi(argv[i + 1])));
        else return 64;
    }
    if (i != argc) return 64;
    auto data = read_file(song);
    auto probe = std::make_unique<Player>();
    if (!probe->load(data, pcm)) { fprintf(stderr, "cannot read a valid PMD song: %s\n", song.c_str()); return 2; }
    uint64_t first = 0, second = 0;
    unsigned previous_loop = 0;
    bool ended = false;
    while (probe->synth.elapsed < Pc98Synth::clock * 600) {
        probe->synth.advance(probe->synth.next_event());
        if (!mukyu_pmd_playing(probe->driver)) { first = probe->synth.elapsed; ended = true; break; }
        if (mukyu_pmd_loop(probe->driver) != previous_loop) {
            if (!first) first = probe->synth.elapsed;
            else { second = probe->synth.elapsed; break; }
            previous_loop = mukyu_pmd_loop(probe->driver);
        }
    }
    if (!ended && !second) { fprintf(stderr, "no loop or ending found within ten minutes\n"); return 3; }
    uint64_t loop = second > first ? second - first : 0;
    uint64_t start = loop <= first ? first - loop : 0;
    auto milliseconds = [](uint64_t clocks) { return (clocks * 1000 + Pc98Synth::clock / 2) / Pc98Synth::clock; };
    if (mode == "--info") {
        const char *title = mukyu_pmd_comment(probe->driver, 0);
        const char *composer = mukyu_pmd_comment(probe->driver, 1);
        probe->synth.load_rhythm(rhythm);
        printf("TITLE=%s\nCOMPOSER=%s\nLENGTH_MS=%llu\nLOOP_MS=%llu\nLOOP_START_MS=%llu\nRHYTHM=%u\n", title ? title : "", composer ? composer : "",
               (unsigned long long)milliseconds(first), (unsigned long long)milliseconds(loop), (unsigned long long)milliseconds(start), probe->synth.rhythm_count);
        return 0;
    }
    probe.reset();
    auto player = std::make_unique<Player>();
    if (!player->load(data, pcm)) return 2;
    player->synth.load_rhythm(rhythm);
    uint64_t frames = std::max<uint64_t>(RATE / 2, (first * RATE) / Pc98Synth::clock + (ended ? uint64_t(tail) * RATE / 1000 : 0));
    FILE *f = fopen(out.c_str(), "wb");
    if (!f) { fprintf(stderr, "cannot write %s\n", out.c_str()); return 4; }
    fwrite("RIFF", 1, 4, f); put32(f, 36 + frames * 4);
    fwrite("WAVEfmt ", 1, 8, f); put32(f, 16); put16(f, 1); put16(f, 2);
    put32(f, RATE); put32(f, RATE * 4); put16(f, 4); put16(f, 16);
    fwrite("data", 1, 4, f); put32(f, frames * 4);
    int32_t mixed[2048]; int16_t output[2048];
    for (uint64_t done = 0; done < frames;) {
        unsigned n = std::min<uint64_t>(1024, frames - done);
        player->synth.mix(mixed, n, RATE, true);
        for (unsigned j = 0; j < n * 2; ++j) output[j] = std::max(-32768, std::min(32767, mixed[j]));
        mukyu_pmd_mix(player->driver, output, n);
        if (fwrite(output, 4, n, f) != n) { fclose(f); return 5; }
        done += n;
    }
    return fclose(f) ? 5 : 0;
}
