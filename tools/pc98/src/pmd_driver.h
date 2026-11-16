#ifndef MUKYU_PMD_DRIVER_H
#define MUKYU_PMD_DRIVER_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct MukyuPmd;
struct MukyuPmd *mukyu_pmd_new(uint8_t *data, size_t size, void *context,
    unsigned (*read_reg)(void *, unsigned), void (*write_reg)(void *, unsigned, unsigned),
    uint8_t (*read_status)(void *));
void mukyu_pmd_free(struct MukyuPmd *p);
void mukyu_pmd_interrupt(struct MukyuPmd *p);
int mukyu_pmd_playing(struct MukyuPmd *p);
unsigned mukyu_pmd_loop(struct MukyuPmd *p);
const char *mukyu_pmd_comment(struct MukyuPmd *p, int line);
const char *mukyu_pmd_pcm_name(struct MukyuPmd *p);
void mukyu_pmd_pcm_load(struct MukyuPmd *p, uint8_t *data, size_t size);
void mukyu_pmd_mix(struct MukyuPmd *p, int16_t *output, unsigned frames);
#ifdef __cplusplus
}
#endif
#endif
