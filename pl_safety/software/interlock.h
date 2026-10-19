#ifndef PL_SAFETY_INTERLOCK_H
#define PL_SAFETY_INTERLOCK_H
#include <stdint.h>
#include "../generated/interlock_defs.h"

/* Callbacks perform ordered little-endian D32 MMIO and propagate bus errors.
 * One execution-backend owner holds the software lock for each complete call.
 * ctx is bound to the EXISTING safety window; this is not a Linux driver. */
struct interlock_io {
    void *ctx;
    int (*read)(void *ctx, uint32_t offset, uint32_t *value);
    int (*write)(void *ctx, uint32_t offset, uint32_t value);
};
struct interlock_owner { uint64_t id, sequence; };
int interlock_identify(const struct interlock_io *io);
int interlock_configure(const struct interlock_io *io, uint32_t txn,
                        uint32_t axes, uint32_t feedback_us, uint32_t watchdog_us);
int interlock_open(const struct interlock_io *io, struct interlock_owner *owner);
int interlock_feed_after_health_check(const struct interlock_io *io,
                                     struct interlock_owner *owner);
int interlock_close(const struct interlock_io *io, const struct interlock_owner *owner);
int interlock_snapshot(const struct interlock_io *io, uint32_t request,
                       uint32_t words[SI_SNAPSHOT_WORDS]);
#endif
