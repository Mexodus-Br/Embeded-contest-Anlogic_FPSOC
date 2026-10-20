#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../software/interlock.h"
#include "../generated/safety_defs.h"

struct model {
    uint32_t regs[1024], dirty, writes, fail_write, uncertain_commit, race_snapshot;
    uint64_t owner, sequence;
};
static int read_reg(void *ctx, uint32_t offset, uint32_t *value)
{
    struct model *m = ctx;
    if (offset >= 4096 || offset % 4) return -1;
    if (offset == SI_SNAPSHOT_BASE + 16 && m->race_snapshot)
        ++m->regs[SI_REG_SNAP_ID / 4];
    *value = m->regs[offset / 4];
    return 0;
}
static uint64_t pair(struct model *m, uint32_t lo, uint32_t hi)
{ return ((uint64_t)m->regs[hi / 4] << 32) | m->regs[lo / 4]; }
static int write_reg(void *ctx, uint32_t offset, uint32_t value)
{
    struct model *m = ctx;
    ++m->writes;
    if (m->writes == m->fail_write) return -99;
    if (offset >= 4096 || offset % 4) return -1;
    m->regs[offset / 4] = value;
    if (offset >= SI_REG_HEARTBEAT_OWNER_LO && offset <= SI_REG_HEARTBEAT_SEQ_HI)
        m->dirty |= 1u << ((offset - SI_REG_HEARTBEAT_OWNER_LO) / 4);
    if (offset == SI_REG_OWNER_OPEN) {
        m->owner++; m->sequence = 0; m->dirty = 0;
        m->regs[SI_REG_OWNER_LO / 4] = (uint32_t)m->owner;
        m->regs[SI_REG_OWNER_HI / 4] = (uint32_t)(m->owner >> 32);
    }
    if (offset == SI_REG_HEARTBEAT_COMMIT) {
        uint64_t id = pair(m, SI_REG_HEARTBEAT_OWNER_LO, SI_REG_HEARTBEAT_OWNER_HI);
        uint64_t seq = pair(m, SI_REG_HEARTBEAT_SEQ_LO, SI_REG_HEARTBEAT_SEQ_HI);
        if (m->dirty != 15 || id != m->owner || seq <= m->sequence) return -4;
        m->sequence = seq; m->dirty = 0;
        if (m->uncertain_commit) { m->uncertain_commit = 0; return -98; }
    }
    if (offset == SI_REG_CONFIG_COMMIT)
        m->regs[SI_REG_CONFIG_APPLIED / 4] = m->regs[SI_REG_CONFIG_TXN / 4];
    if (offset == SI_REG_SNAP_REQ) m->regs[SI_REG_SNAP_ID / 4] = value;
    return 0;
}
int main(void)
{
    struct model m;
    struct interlock_owner owner;
    struct interlock_io io = {&m, read_reg, write_reg};
    uint32_t words[SI_SNAPSHOT_WORDS], before;
    memset(&m, 0, sizeof(m));
    m.regs[SAF_REGISTERS_PROFILE / 4] = SI_PROFILE;
    m.regs[SAF_REGISTERS_VERSION / 4] = SI_VERSION;
    assert(interlock_identify(&io) == 0);
    m.regs[SAF_REGISTERS_PROFILE / 4] = SAF_PROFILE;
    assert(interlock_identify(&io) == -(int)SI_ERR_IDENTITY);
    before = m.writes;
    assert(interlock_configure(&io, 1, 7, 999999, 2000000) == -(int)SI_ERR_VALUE);
    assert(before == m.writes);
    assert(interlock_configure(&io, 1, 7, 1000000, 3000000) == 0);
    m.owner = UINT64_C(0x1234567800000000);
    assert(interlock_open(&io, &owner) == 0 && owner.id == m.owner && owner.sequence == 0);
    assert(interlock_feed_after_health_check(&io, &owner) == 0 && m.sequence == 1);
    m.fail_write = m.writes + 3; /* Interrupted before all four shadow words. */
    assert(interlock_feed_after_health_check(&io, &owner) == -99 && m.sequence == 1);
    m.fail_write = 0;
    assert(interlock_feed_after_health_check(&io, &owner) == 0 && m.sequence == 3);
    m.uncertain_commit = 1; /* Hardware accepted but response was lost. */
    assert(interlock_feed_after_health_check(&io, &owner) == -98 && m.sequence == 4);
    assert(interlock_feed_after_health_check(&io, &owner) == 0 && m.sequence == 5);
    m.owner++; /* A service restart must not continue feeding an old owner. */
    assert(interlock_feed_after_health_check(&io, &owner) == -4);
    owner.sequence = UINT64_MAX; before = m.writes;
    assert(interlock_feed_after_health_check(&io, &owner) == -(int)SI_ERR_IDENTITY && before == m.writes);
    assert(interlock_snapshot(&io, 1, words) == 0);
    m.race_snapshot = 1;
    assert(interlock_snapshot(&io, 2, words) == -(int)SI_ERR_IDENTITY);
    puts("PASS interlock software partial/uncertain writes, identities, sequence exhaustion and snapshot race");
    return 0;
}
