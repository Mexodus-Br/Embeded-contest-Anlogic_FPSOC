#pragma once
#include "ps_core.hpp"
#include <memory>
#include <array>

namespace ps {
struct ExecutionBinding {
    std::string boot_id,command_id,parameter_revision,start_position_id;
    uint64_t cancel_epoch=0;uint32_t generation=0;
    std::array<int64_t,3> start_steps{};
};
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
    bool completed=false,stopped=false,pulse_safe=false,accepted=false,failed=false;
};
// Called only by the service owner thread, except submit under its same mutex.
// A future hardware adapter must implement actual completion and pulse-safe STOP.
class ExecutionBackend {
public:
    virtual ~ExecutionBackend()=default;
    virtual void submit(std::shared_ptr<const PlannedTask> plan,uint64_t now,const ExecutionBinding &binding={})=0;
    virtual void manual_target(const ManualSegment &segment)=0;
    virtual void request_stop(uint64_t now)=0;
    virtual BackendUpdate poll(uint64_t now)=0;
    virtual Json status()const=0;
    virtual bool simulation()const{return true;}
    virtual Json telemetry()const{return nullptr;}
    virtual Json history()const{return nullptr;}
    virtual void action(const std::string&){throw Error("BACKEND_UNAVAILABLE","Hardware action requires hardware backend");}
};
class SimulationControl {
public:
    virtual ~SimulationControl()=default;
    virtual void inject_stop_failure(bool fail)=0;
};
std::unique_ptr<ExecutionBackend> simulation_backend();
}
