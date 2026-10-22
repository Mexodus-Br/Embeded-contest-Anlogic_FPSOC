#pragma once
#include "ps_core.hpp"
#include <memory>

namespace ps {
struct PlannedTask {std::string parameter;Json task,first,cycle;};
struct ManualSegment {
    Json pose;
    std::string submission_id;
    uint64_t duration_us;
};
struct BackendUpdate {
    Json pose=nullptr;
    std::string parameter;
    uint64_t iteration=0;
    bool completed=false,stopped=false,pulse_safe=false;
};
// Called only by the service owner thread, except submit under its same mutex.
// A future hardware adapter must implement actual completion and pulse-safe STOP.
class ExecutionBackend {
public:
    virtual ~ExecutionBackend()=default;
    virtual void submit(std::shared_ptr<const PlannedTask> plan,uint64_t now)=0;
    virtual void manual_target(const ManualSegment &segment)=0;
    virtual void request_stop(uint64_t now)=0;
    virtual BackendUpdate poll(uint64_t now)=0;
    virtual Json status()const=0;
};
class SimulationControl {
public:
    virtual ~SimulationControl()=default;
    virtual void inject_stop_failure(bool fail)=0;
};
std::unique_ptr<ExecutionBackend> simulation_backend();
}
