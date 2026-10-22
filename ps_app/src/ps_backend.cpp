#include "ps_backend.hpp"
#include <algorithm>

namespace ps {
class SimulationBackend final:public ExecutionBackend,public SimulationControl {
    std::shared_ptr<const PlannedTask> plan_;
    uint64_t started_=0,iteration_=0,index_=0,stop_at_=0;
    bool running_=false,stop_failure_=false;
public:
    void submit(std::shared_ptr<const PlannedTask> plan,uint64_t now)override {
        plan_=std::move(plan);started_=now;iteration_=index_=stop_at_=0;running_=true;
    }
    void manual_target(const ManualSegment &)override {plan_.reset();running_=false;}
    void request_stop(uint64_t now)override {running_=false;stop_at_=now+10000;}
    void inject_stop_failure(bool fail)override {stop_failure_=fail;}
    BackendUpdate poll(uint64_t now)override {
        BackendUpdate r;r.iteration=iteration_;
        if(stop_at_&&now>=stop_at_){stop_at_=0;r.stopped=true;r.pulse_safe=!stop_failure_;}
        if(!running_)return r;
        const auto &p=iteration_?plan_->cycle:plan_->first;const auto &samples=p.at("samples");
        size_t lo=index_,hi=samples.size();
        while(lo<hi){size_t mid=lo+(hi-lo)/2;if(u64(samples[mid].at("time_us"),"time_us")<=now-started_)lo=mid+1;else hi=mid;}
        if(lo>index_){index_=lo;const auto &s=samples[lo-1];r.pose={{"xyz_mm",s.at("xyz_mm")},{"steps",s.at("steps")},{"joint_deg",s.at("joint_deg")}};r.parameter=plan_->parameter;}
        if(index_==samples.size()){
            r.iteration=++iteration_;const auto &repeat=plan_->task.at("repeat");
            if(repeat.at("mode")=="until_stopped"||iteration_<u64(repeat.at("count"),"count")){index_=0;started_+=u64(p.at("duration_us"),"duration_us");}
            else{running_=false;r.completed=true;}
        }
        return r;
    }
    Json status()const override {
        Json r={{"kind","simulation"},{"pulse_model","not_cycle_accurate"},{"accepted_sequence",nullptr},{"completed_sequence",nullptr}};
        if(plan_){const auto &samples=(iteration_&&!plan_->cycle.is_null()?plan_->cycle:plan_->first).at("samples");
            r["accepted_sequence"]=std::to_string(std::min<size_t>(samples.size(),index_+73)-1);if(index_)r["completed_sequence"]=std::to_string(index_-1);}
        return r;
    }
};
std::unique_ptr<ExecutionBackend> simulation_backend(){return std::make_unique<SimulationBackend>();}
}
