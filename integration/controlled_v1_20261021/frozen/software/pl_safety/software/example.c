#include "interlock.h"

/* Called by the single serial/Web execution backend after its critical
 * control-cycle health checks PASS. Schedule approximately every 500000us
 * using a monotonic clock; failures request STOP and retain cancellation state.
 * Never invoke this from an unconditional timer or independent feeder thread.
 * Browser connection state is not the decision to feed or stop feeding. */
int execution_backend_report_healthy(const struct interlock_io *io,
                                     struct interlock_owner *owner,
                                     int critical_control_cycle_healthy)
{
    if (!critical_control_cycle_healthy) return -(int)SI_ERR_STATE;
    return interlock_feed_after_health_check(io, owner);
}
