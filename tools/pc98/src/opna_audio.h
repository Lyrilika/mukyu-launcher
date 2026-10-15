#ifndef MUKYU_OPNA_AUDIO_H
#define MUKYU_OPNA_AUDIO_H
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <string>
#include <vector>
extern "C" {
#include "libopna/opna.h"
}

class Pc98Synth {
public:
    static constexpr uint64_t clock = 7987200;
    struct opna chip{};
    std::function<void()> interrupt;
    uint64_t elapsed = 0;
    unsigned status = 0;
    unsigned rhythm_count = 0;
    uint8_t registers[512]{};

    Pc98Synth() { reset(); }

    void reset() {
        chip = {};
        opna_reset(&chip);
#if defined(__x86_64__) || defined(_M_X64)
        opna_ssg_sinc_calc_func = opna_ssg_sinc_calc_sse2;
#endif
        opna_adpcm_set_ram_256k(&chip.adpcm, ram.data());
        elapsed = status = 0;
        std::fill(std::begin(registers), std::end(registers), 0);
        remaining = {-1, -1};
        fraction = sample_fraction = 0;
        previous[0] = previous[1] = current[0] = current[1] = 0;
    }

    void write(unsigned address, unsigned value) {
        if (address >= 512) return;
        uint8_t old = registers[address];
        registers[address] = value;
        opna_writereg(&chip, address, value);
        if (address == 0x27) {
            if (value & 0x10) status &= ~1u;
            if (value & 0x20) status &= ~2u;
            for (unsigned i = 0; i < 2; ++i) {
                if (!(value & (1u << i))) remaining[i] = -1;
                else if (!(old & (1u << i))) remaining[i] = period(i);
            }
        }
    }

    unsigned read(unsigned address) const {
        return address < 16 ? opna_readreg(&chip, address) :
               address < 512 ? registers[address] : 255;
    }

    uint64_t next_event() const {
        uint64_t result = clock;
        for (auto value : remaining) if (value >= 0) result = std::min(result, static_cast<uint64_t>(value));
        return result;
    }

    void advance(uint64_t clocks) {
        while (clocks) {
            uint64_t step = std::min(clocks, next_event());
            for (auto &value : remaining) if (value >= 0) value -= step;
            clocks -= step;
            elapsed += step;
            unsigned previous_status = status;
            for (unsigned i = 0; i < 2; ++i) {
                if (remaining[i] == 0) {
                    remaining[i] = period(i);
                    if (registers[0x27] & (4u << i)) status |= 1u << i;
                }
            }
            if (status != previous_status && interrupt) interrupt();
        }
    }

    void native(int16_t *output, unsigned count, bool run_timers) {
        while (count) {
            unsigned n = count;
            if (run_timers) n = std::min<uint64_t>(n, std::max<uint64_t>(1, (next_event() + 143) / 144));
            std::fill(output, output + n * 2, 0);
            opna_mix(&chip, output, n);
            if (run_timers) advance(n * 144);
            output += n * 2;
            count -= n;
        }
    }

    void mix(int32_t *output, unsigned count, unsigned rate, bool run_timers = false) {
        uint64_t denominator = uint64_t(rate) * 144;
        size_t needed = (sample_fraction + uint64_t(count) * clock) / denominator;
        buffer.resize(needed * 2);
        if (needed) native(buffer.data(), needed, run_timers);
        size_t cursor = 0;
        for (unsigned i = 0; i < count; ++i) {
            sample_fraction += clock;
            while (sample_fraction >= denominator) {
                previous[0] = current[0]; previous[1] = current[1];
                current[0] = buffer[cursor++]; current[1] = buffer[cursor++];
                sample_fraction -= denominator;
            }
            double part = double(sample_fraction) / denominator;
            for (unsigned c = 0; c < 2; ++c)
                output[i * 2 + c] = int32_t(previous[c] + (current[c] - previous[c]) * part);
        }
    }

    void load_rhythm(const std::string &directory) {
        static const char *names[] = {"BD", "SD", "TOP", "HH", "TOM", "RIM"};
        rhythm_count = 0;
        for (unsigned d = 0; d < 6; ++d) {
            std::string path = directory + "/2608_" + names[d] + ".WAV";
            FILE *f = fopen(path.c_str(), "rb");
            if (!f) continue;
            std::vector<uint8_t> bytes;
            uint8_t block[4096]; size_t got;
            while ((got = fread(block, 1, sizeof(block), f))) bytes.insert(bytes.end(), block, block + got);
            fclose(f);
            if (bytes.size() < 12 || memcmp(bytes.data(), "RIFF", 4) || memcmp(bytes.data() + 8, "WAVE", 4)) continue;
            unsigned rate = 0, channels = 0, bits = 0, format = 0;
            const uint8_t *data = nullptr; size_t length = 0;
            auto read16 = [](const uint8_t *p) { return unsigned(p[0]) | unsigned(p[1]) << 8; };
            auto read32 = [](const uint8_t *p) { return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24; };
            for (size_t off = 12; off + 8 <= bytes.size();) {
                size_t size = read32(bytes.data() + off + 4);
                if (size > bytes.size() - off - 8) break;
                const uint8_t *p = bytes.data() + off + 8;
                if (!memcmp(bytes.data() + off, "fmt ", 4) && size >= 16) {
                    format = read16(p); channels = read16(p + 2); rate = read32(p + 4); bits = read16(p + 14);
                }
                if (!memcmp(bytes.data() + off, "data", 4)) { data = p; length = size; }
                off += 8 + size + (size & 1);
            }
            if (!data || format != 1 || !rate || !channels || channels > 2 || bits != 16) continue;
            size_t frames = length / (2 * channels);
            if (!frames) continue;
            auto &samples = drums[d];
            samples.resize(uint64_t(frames) * clock / (144 * uint64_t(rate)));
            for (size_t i = 0; i < samples.size(); ++i) {
                double position = double(i) * rate * 144 / clock;
                size_t a = std::min(frames - 1, size_t(position));
                size_t b = std::min(frames - 1, a + 1);
                auto at = [&](size_t index) {
                    int sum = 0;
                    for (unsigned c = 0; c < channels; ++c) sum += int16_t(read16(data + (index * channels + c) * 2));
                    return sum / int(channels);
                };
                samples[i] = int16_t(at(a) + (at(b) - at(a)) * (position - a));
            }
            chip.drum.drums[d].data = samples.data();
            chip.drum.drums[d].len = samples.size();
            ++rhythm_count;
        }
    }

    void Init(unsigned, unsigned rate, bool, const char *rhythm) { reset(); output_rate = rate; load_rhythm(rhythm); }
    void SetReg(unsigned address, unsigned value) { write(address, value); }
    unsigned GetReg(unsigned address) const { return read(address); }
    unsigned ReadStatus() const { return status; }
    void Count(unsigned microseconds) {
        fraction += uint64_t(microseconds) * clock;
        advance(fraction / 1000000);
        fraction %= 1000000;
    }
    void Mix(int32_t *output, unsigned count) { mix(output, count, output_rate); }

private:
    std::vector<int16_t> buffer;
    std::array<uint8_t, 262144> ram{};
    std::array<int64_t, 2> remaining{};
    std::array<std::vector<int16_t>, 6> drums;
    uint64_t fraction = 0, sample_fraction = 0;
    unsigned output_rate = 44100;
    int16_t previous[2]{}, current[2]{};
    uint64_t period(unsigned timer) const {
        return timer ? 2304 * (256 - registers[0x26]) :
               144 * (1024 - ((unsigned(registers[0x24]) << 2) | (registers[0x25] & 3)));
    }
};
#endif
