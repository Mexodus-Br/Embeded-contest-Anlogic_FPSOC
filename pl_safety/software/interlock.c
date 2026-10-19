#include "interlock.h"
#include "../generated/safety_defs.h"

static int valid_io(const struct interlock_io *io)
{ return io && io->read && io->write; }
static int put(const struct interlock_io *io, uint32_t off, uint32_t value)
{ return io->write(io->ctx, off, value); }
static int get(const struct interlock_io *io, uint32_t off, uint32_t *value)
{ return io->read(io->ctx, off, value); }
static int put64(const struct interlock_io *io, uint32_t lo, uint32_t hi, uint64_t value)
{
    int error = put(io, lo, (uint32_t)value);
    return error ? error : put(io, hi, (uint32_t)(value >> 32));
}
int interlock_identify(const struct interlock_io *io)
{
    uint32_t profile, version;
    int error;
    if (!valid_io(io)) return -(int)SI_ERR_VALUE;
    error = get(io, SAF_REGISTERS_PROFILE, &profile);
    if (error) return error;
    error = get(io, SAF_REGISTERS_VERSION, &version);
    if (error) return error;
    return profile == SI_PROFILE && version == SI_VERSION ? 0 : -(int)SI_ERR_IDENTITY;
}
int interlock_configure(const struct interlock_io *io, uint32_t txn,
                        uint32_t axes, uint32_t feedback_us, uint32_t watchdog_us)
{
    uint32_t applied;
    int error;
    if (!valid_io(io) || !txn || !axes || axes > 7 ||
        feedback_us < SI_TIMEOUT_MIN_US || feedback_us > SI_TIMEOUT_MAX_US ||
        watchdog_us < SI_TIMEOUT_MIN_US || watchdog_us > SI_TIMEOUT_MAX_US)
        return -(int)SI_ERR_VALUE;
    error = put(io, SI_REG_SHADOW_AXES, axes);
    if (!error) error = put(io, SI_REG_SHADOW_FEEDBACK_US, feedback_us);
    if (!error) error = put(io, SI_REG_SHADOW_WATCHDOG_US, watchdog_us);
    if (!error) error = put(io, SI_REG_CONFIG_TXN, txn);
    if (!error) error = put(io, SI_REG_CONFIG_COMMIT, 1);
    if (!error) error = get(io, SI_REG_CONFIG_APPLIED, &applied);
    if (error) return error;
    return applied == txn ? 0 : -(int)SI_ERR_STATE;
}
int interlock_open(const struct interlock_io *io, struct interlock_owner *owner)
{
    uint32_t lo, hi;
    int error;
    if (!valid_io(io) || !owner) return -(int)SI_ERR_VALUE;
    error = put(io, SI_REG_OWNER_OPEN, 1);
    if (!error) error = get(io, SI_REG_OWNER_LO, &lo);
    if (!error) error = get(io, SI_REG_OWNER_HI, &hi);
    if (error) return error;
    owner->id = ((uint64_t)hi << 32) | lo;
    owner->sequence = 0;
    return owner->id ? 0 : -(int)SI_ERR_IDENTITY;
}
int interlock_feed_after_health_check(const struct interlock_io *io,
                                     struct interlock_owner *owner)
{
    uint64_t next;
    int error;
    if (!valid_io(io) || !owner || !owner->id || owner->sequence == UINT64_MAX)
        return -(int)SI_ERR_IDENTITY;
    next = ++owner->sequence; /* Never reuse a sequence after an uncertain write. */
    error = put64(io, SI_REG_HEARTBEAT_OWNER_LO, SI_REG_HEARTBEAT_OWNER_HI, owner->id);
    if (!error) error = put64(io, SI_REG_HEARTBEAT_SEQ_LO, SI_REG_HEARTBEAT_SEQ_HI, next);
    return error ? error : put(io, SI_REG_HEARTBEAT_COMMIT, 1);
}
int interlock_close(const struct interlock_io *io, const struct interlock_owner *owner)
{
    int error;
    if (!valid_io(io) || !owner || !owner->id) return -(int)SI_ERR_IDENTITY;
    error = put64(io, SI_REG_HEARTBEAT_OWNER_LO, SI_REG_HEARTBEAT_OWNER_HI, owner->id);
    return error ? error : put(io, SI_REG_OWNER_CLOSE, 1);
}
int interlock_snapshot(const struct interlock_io *io, uint32_t request,
                       uint32_t words[SI_SNAPSHOT_WORDS])
{
    uint32_t id, index;
    int error;
    if (!valid_io(io) || !request || !words) return -(int)SI_ERR_VALUE;
    error = put(io, SI_REG_SNAP_REQ, request);
    if (error) return error;
    error = get(io, SI_REG_SNAP_ID, &id);
    if (error) return error;
    if (id != request) return -(int)SI_ERR_IDENTITY;
    for (index = 0; index < SI_SNAPSHOT_WORDS; ++index) {
        error = get(io, SI_SNAPSHOT_BASE + 4 * index, &words[index]);
        if (error) return error;
    }
    error = get(io, SI_REG_SNAP_ID, &id);
    if (error) return error;
    return id == request ? 0 : -(int)SI_ERR_IDENTITY;
}
