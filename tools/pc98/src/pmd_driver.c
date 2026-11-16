#include <stdlib.h>
#include "pmd_driver.h"
#include "fmdriver/fmdriver.h"
#include "fmdriver/fmdriver_pmd.h"
struct MukyuPmd {
    struct driver_pmd driver;
    struct fmdriver_work work;
    struct ppz8 ppz;
    void *context;
    unsigned (*read_reg)(void *, unsigned);
    void (*write_reg)(void *, unsigned, unsigned);
    uint8_t (*read_status)(void *);
};
static unsigned read_reg(struct fmdriver_work *w, unsigned a) {
    struct MukyuPmd *p = w->opna;
    return p->read_reg(p->context, a);
}
static void write_reg(struct fmdriver_work *w, unsigned a, unsigned v) {
    struct MukyuPmd *p = w->opna;
    p->write_reg(p->context, a, v);
}
static uint8_t read_status(struct fmdriver_work *w, bool high) {
    (void)high;
    struct MukyuPmd *p = w->opna;
    return p->read_status(p->context);
}
struct MukyuPmd *mukyu_pmd_new(uint8_t *data, size_t size, void *context,
    unsigned (*read_callback)(void *, unsigned), void (*write_callback)(void *, unsigned, unsigned),
    uint8_t (*status_callback)(void *)) {
    if (!size || size > 65535) return NULL;
    struct MukyuPmd *p = calloc(1, sizeof(*p));
    if (!p) return NULL;
    if (!pmd_load(&p->driver, data, size)) { free(p); return NULL; }
    p->context = context; p->read_reg = read_callback; p->write_reg = write_callback; p->read_status = status_callback;
    p->work.opna = p; p->work.opna_readreg = read_reg; p->work.opna_writereg = write_reg; p->work.opna_status = read_status;
    ppz8_init(&p->ppz, 44100, 0xa000);
    p->work.ppz8 = &p->ppz; p->work.ppz8_functbl = &ppz8_functbl;
    pmd_init(&p->work, &p->driver);
    return p;
}
void mukyu_pmd_free(struct MukyuPmd *p) { free(p); }
void mukyu_pmd_interrupt(struct MukyuPmd *p) { p->work.driver_opna_interrupt(&p->work); }
int mukyu_pmd_playing(struct MukyuPmd *p) { return p->work.playing; }
unsigned mukyu_pmd_loop(struct MukyuPmd *p) { return p->work.loop_cnt; }
const char *mukyu_pmd_comment(struct MukyuPmd *p, int line) { return p->work.get_comment ? p->work.get_comment(&p->work, line) : ""; }
const char *mukyu_pmd_pcm_name(struct MukyuPmd *p) { return p->driver.ppcfile; }
void mukyu_pmd_pcm_load(struct MukyuPmd *p, uint8_t *data, size_t size) { pmd_ppc_load(&p->work, data, size); }
void mukyu_pmd_mix(struct MukyuPmd *p, int16_t *output, unsigned frames) { ppz8_mix(&p->ppz, output, frames); }
