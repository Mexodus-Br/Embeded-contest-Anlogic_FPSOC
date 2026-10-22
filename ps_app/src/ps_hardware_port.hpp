#pragma once
#include "ps_core.hpp"
#include <memory>

namespace ps {
// Integration proposal only: no device access and no hardware factory is installed.
struct OwnerIdentity {
    std::string boot_id, command_id, submission_id, parameter_revision;
    std::string start_position_id;
    uint64_t cancel_epoch=0;
};
enum class Admission {rejected, queued, capacity_exhausted, qualification_missing};
struct OwnerPlan {
    OwnerIdentity identity;
    // Immutable bounded MOT2-compatible samples; production limits remain unapproved.
    Json samples;
};
struct OwnerSnapshot {
    OwnerIdentity identity;
    uint64_t observed_monotonic_us=0, observed_stop_epoch=0;
    bool qualified=false, accepted=false, completed=false;
    bool stopped=false, pulse_safe=false, result_unknown=true;
    Json command_position=nullptr, xyz_estimate=nullptr, driver_feedback=nullptr;
    // Each value must carry its own validity/source/time/generation/revision.
    Json telemetry=nullptr;
};
class HardwareOwnerPort {
public:
    virtual ~HardwareOwnerPort()=default;
    virtual Admission try_submit(std::shared_ptr<const OwnerPlan>)=0;
    // Must be nonblocking and independent of ordinary submission/IO locks.
    virtual void request_stop(uint64_t cancel_epoch)=0;
    // Cached read-only copy; never reads or consumes GP/DMA on the caller's thread.
    virtual std::shared_ptr<const OwnerSnapshot> snapshot()const=0;
};
}
