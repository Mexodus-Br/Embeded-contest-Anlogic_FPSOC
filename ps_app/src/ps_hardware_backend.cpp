#include "ps_hardware_port.hpp"
#include "ps_runtime.hpp"
#include <chrono>
#include <algorithm>
#include "../../bsp/motion/generated/interface_defs.h"
namespace ps {
HardwareBackend::HardwareBackend(std::shared_ptr<BoardDevice> d,std::string boot):device_(std::move(d)),boot_(std::move(boot)) {worker_=std::thread([this]{run();});}
HardwareBackend::~HardwareBackend(){quit_=true;try{device_->stop();}catch(...){}worker_.join();}
void HardwareBackend::submit(std::shared_ptr<const PlannedTask> p,uint64_t now,const ExecutionBinding &binding){
    std::lock_guard<std::mutex> l(mutex_);
    require(!board_.calibration_only,"CALIBRATION_ONLY","Only bounded HOME calibration is enabled; ordinary motion remains disabled");
    require(cancel_<UINT64_MAX/2-1&&!pending_&&phase_=="idle"&&board_.ready&&board_.qualified&&owner_&&board_.owner==owner_&&!board_.fault&&!board_.quarantine,"QUALIFICATION_MISSING","Explicit owner, recovery and complete HOME required");
    require(p&&p->first.at("samples").size()>0&&p->first.at("samples").size()<=200000,"RESOURCE_LIMIT","Bounded plan required");
    require(binding.boot_id==boot_&&logical_id(binding.command_id)&&binding.parameter_revision==p->parameter&&binding.start_position_id==position_id_&&binding.cancel_epoch==cancel_&&binding.generation==board_.generation&&binding.start_steps==board_.position&&board_.position_valid,"STALE_INPUT","Boot/command/parameter/start position/generation/cancel binding mismatch");
    require(!publication_.is_null()&&(u64(publication_.at("observed_monotonic_us"),"observation")>=now||now-u64(publication_.at("observed_monotonic_us"),"observation")<100000),"STALE_INPUT","Start snapshot stale");
    require(used_commands_.size()<1024&&!used_commands_.count(binding.command_id),"ID_CONFLICT","Command ledger full or ID already submitted");
    used_commands_.insert(binding.command_id);pending_binding_=binding;command_id_=binding.command_id;parameter_revision_=binding.parameter_revision;
    pending_=std::move(p);phase_="queued";
}
void HardwareBackend::manual_target(const ManualSegment&){throw Error("POSITION_UNKNOWN","Hardware jog requires approved XYZ estimator and streaming policy");}
void HardwareBackend::request_stop(uint64_t){
    auto before_epoch=cancel_.load();constexpr uint64_t limit=UINT64_MAX/2-1;
    while(before_epoch<limit&&!cancel_.compare_exchange_weak(before_epoch,before_epoch+1)){}
    auto epoch=before_epoch<limit?before_epoch+1:limit; // saturation permanently retires admission
    // Invalidate before I/O; result cannot precede the writes.
    bool ok=true;std::string error;
    try{device_->stop();}catch(const std::exception&e){ok=false;error=e.what();}
    auto result=epoch*2+(ok?1:0),before=stop_write_result_.load();
    while(before<result&&!stop_write_result_.compare_exchange_weak(before,result)){}
    if(!ok){std::lock_guard<std::mutex> l(mutex_);error_=error;phase_="fault";}
}
BackendUpdate HardwareBackend::poll(uint64_t now){
    // This lease is produced only when the shared command service control loop progresses.
    lease_=now;std::lock_guard<std::mutex> l(mutex_);BackendUpdate r;
    r.completed=completion_&&observed_cancel_==cancel_;completion_=false;r.iteration=iteration_;
    r.stopped=stop_result_&&observed_cancel_==cancel_;r.pulse_safe=stop_ok_;stop_result_=false;
    r.accepted=phase_=="running";r.failed=phase_=="fault"||phase_=="rejected";
    return r; // No target-derived XYZ or pose publication.
}
void HardwareBackend::action(const std::string &name){
    static const std::map<std::string,SafetyAction> names={{"open",SafetyAction::open},{"close",SafetyAction::close},{"clear",SafetyAction::clear},{"home",SafetyAction::home},{"recover",SafetyAction::recover},{"configure",SafetyAction::configure},{"feedback_on",SafetyAction::feedback_on},{"feedback_off",SafetyAction::feedback_off},{"disable",SafetyAction::disable}};
    require(names.count(name),"FORMAT","Unknown hardware action");std::lock_guard<std::mutex> l(mutex_);
    require(name!="home"||board_.home_capable,"PRODUCTION_HOME_UNAPPROVED","Exact approved HOME calibration config identity and valid snapshot required");
    require(actions_.empty()&&!pending_&&phase_!="running"&&phase_!="queued"&&phase_!="homing"&&phase_!="stopping","BUSY","Control operation pending");actions_.push_back({names.at(name),owner_,cancel_.load(),monotonic_us()+100000});
}
Json HardwareBackend::status()const{std::lock_guard<std::mutex> l(mutex_);return {{"kind","hardware"},{"boot_id",boot_},{"position_id",position_id_},{"command_id",command_id_},{"parameter_revision",parameter_revision_},{"generation",std::to_string(board_.generation)},{"phase",phase_},{"error",error_},{"owner_id",std::to_string(owner_)},{"cancel_epoch",std::to_string(cancel_.load())},{"observed_stop_epoch",std::to_string(observed_cancel_)},{"accepted_sequence",board_.accepted_valid?Json(std::to_string(board_.accepted)):Json()},{"completed_sequence",board_.done_valid?Json(std::to_string(board_.done)):Json()},{"quarantine",board_.quarantine},{"dma_owned",board_.dma_owned},{"home_capable",board_.home_capable},{"calibration_only",board_.calibration_only}};}
Json HardwareBackend::telemetry()const{std::lock_guard<std::mutex> l(mutex_);return publication_;}
void HardwareBackend::run(){
    ExecutionBinding binding;std::shared_ptr<const PlannedTask> active;size_t offset=0;uint64_t session=0,id=0,seq=0,last_feed=0,epoch=0,deadline=0,iteration=0,stop_deadline=0,home_before=0,home_deadline=0;uint32_t generation=0,ends=0;bool started=false,stop_pending=false,lost=false,homing=false;
    while(!quit_){auto now=monotonic_us();try{
        auto write_before_snapshot=stop_write_result_.load();
        auto b=device_->read();
        auto current=cancel_.load();
        if(current!=epoch){epoch=current;active.reset();homing=false;offset=0;started=false;stop_pending=true;stop_deadline=now+2000000;std::lock_guard<std::mutex> l(mutex_);pending_.reset();actions_.clear();completion_=false;stop_result_=false;stop_ok_=false;phase_="stopping";observed_cancel_=epoch;}
        if(id&&(!b.owner_active||b.owner!=id)){
            id=0;active.reset();lost=true;device_->stop();std::lock_guard<std::mutex> l(mutex_);pending_.reset();phase_="fault";error_="owner_lost";
        }
        auto stop_write=stop_write_result_.load();
        if(stop_pending&&stop_write==epoch*2+1&&write_before_snapshot==stop_write&&cancel_==epoch&&b.stopped&&b.pulse_safe){stop_pending=false;std::lock_guard<std::mutex> l(mutex_);stop_result_=true;stop_ok_=true;phase_="stopped";}
        if(stop_pending&&(stop_write==epoch*2||now>=stop_deadline)){stop_pending=false;std::lock_guard<std::mutex> l(mutex_);stop_result_=true;stop_ok_=false;phase_="fault";error_="stop_failed_or_timeout";lost=true;}
        if(homing&&(b.fault||!b.home_capable||now>=home_deadline))throw Error("HOME_FAILED","HOME fault, config identity change or execution deadline");
        if(active&&session&&(b.fault||b.quarantine||b.generation!=generation||b.session!=session||now>=deadline))throw Error("HARDWARE_FAILURE","Fault, generation/session mismatch or execution timeout");
        auto lease=lease_.load();bool healthy=lease&&(lease>=now||now-lease<250000)&&!b.quarantine&&!lost;
        if((active||homing)&&!healthy)throw Error("CONTROL_STALE","Critical command loop stopped progressing");
        if(id&&healthy&&(!last_feed||now-last_feed>=500000)){require(seq!=UINT64_MAX,"EXHAUSTED","Heartbeat sequence exhausted");device_->feed(id,++seq);last_feed=now;}
        SafetyAction a=SafetyAction::open;bool action=false;PendingAction request{};
        {std::lock_guard<std::mutex> l(mutex_);if(!actions_.empty()){request=actions_.front();a=request.action;actions_.clear();action=true;}}
        if(action){
            require(request.cancel==cancel_.load()&&!stop_pending&&monotonic_us()<request.expires,"STALE_ACTION","Cancelled or expired hardware action");
            if(a==SafetyAction::home)require(request.owner==id,"STALE_ACTION","HOME owner changed after admission");
            auto action_lease=lease_.load(),action_now=monotonic_us();
            require(action_lease&&(action_lease>=action_now||action_now-action_lease<250000),"CONTROL_STALE","Expired control action");
            if(a==SafetyAction::open){require(!b.owner_active,"OWNER_BUSY","Never adopt an old owner");id=device_->safety(a,0);seq=last_feed=0;lost=false;}
            else {if(a==SafetyAction::home){require(b.home_capable&&b.qualified&&id&&b.owner==id&&!b.fault&&!b.dma_owned,"QUALIFICATION_MISSING","Approved fresh HOME identity, healthy owner and feedback required");home_before=b.home_start_us;} device_->safety(a,id);if(a==SafetyAction::home){homing=true;home_deadline=now+20000000;}}
            if(a==SafetyAction::close)id=0;
            std::lock_guard<std::mutex> l(mutex_);phase_=lost?"fault":(a==SafetyAction::home?"homing":"idle");if(!lost)error_.clear();
            continue; // Observe the post-command snapshot before any qualification decision.
        }
        {std::lock_guard<std::mutex> l(mutex_);if(!active&&pending_){active=std::move(pending_);binding=pending_binding_;pending_.reset();iteration=0;offset=0;started=false;session=0;}}
        if(active&&epoch==cancel_){
            const auto &plan=iteration?active->cycle:active->first;const auto &samples=plan.at("samples");
            if(!session){
                if(!iteration)require(binding.cancel_epoch==epoch&&binding.generation==b.generation&&binding.start_steps==b.position&&b.position_valid,"STALE_INPUT","Starting hardware position changed after queue admission");
                require(b.qualified&&b.ready&&id&&b.owner==id&&!b.fault,"QUALIFICATION_MISSING","Hardware qualification lost before submission");
                device_->motion(PLI_CMD_ENABLE);if(epoch!=cancel_)continue;
                session=device_->motion(PLI_CMD_OPEN_SESSION);generation=b.generation;ends=b.end_count;require(ends!=UINT32_MAX,"EXHAUSTED","END counter exhausted");deadline=now+u64(plan.at("duration_us"),"duration_us")+2000000;}
            // Small bounded packets fit pre-start credits and cap blocking IO to 100ms.
            if(offset<samples.size()&&b.buffered<=32){
                size_t count=std::min<size_t>(32,samples.size()-offset);std::vector<uint8_t> bytes;bytes.reserve(count*72);
                for(size_t i=0;i<count;i++){const auto &s=samples[offset+i];auto steps=s.at("steps");if(steps.size()==3)steps.push_back("0");
                    auto encoded=motion_encode({{"op","motion_encode"},{"session_id",std::to_string(session)},{"sequence",offset+i},{"duration_us",s.at("duration_us")},{"steps",steps},{"end",offset+i+1==samples.size()}}).at("hex_le").get<std::string>();
                    for(size_t n=0;n<encoded.size();n+=2)bytes.push_back(uint8_t(std::stoul(encoded.substr(n,2),nullptr,16)));}
                if(epoch!=cancel_)continue;
                device_->packet(bytes);
                if(epoch!=cancel_)continue;
                offset+=count;
                if(!started&&epoch==cancel_){device_->motion(PLI_CMD_START);started=true;}
            }
            if(epoch==cancel_&&b.accepted_valid&&b.session==session){std::lock_guard<std::mutex> l(mutex_);phase_="running";}
            if(offset==samples.size()&&b.accepted_valid&&b.done_valid&&b.accepted==samples.size()-1&&b.done==samples.size()-1&&b.end_count==ends+1&&!b.buffered){
                ++iteration;{std::lock_guard<std::mutex> l(mutex_);iteration_=iteration;}auto repeat=active->task.at("repeat");bool again=repeat.at("mode")=="until_stopped"||iteration<u64(repeat.at("count"),"count");
                if(again){session=0;offset=0;started=false;}else{active.reset();session=0;std::lock_guard<std::mutex> l(mutex_);if(epoch==cancel_){completion_=true;iteration_=iteration;phase_="idle";}}
            }
        }
        Json positions=Json::array(),pulses=Json::array();for(auto v:b.position)positions.push_back(std::to_string(v));for(auto v:b.pulses)pulses.push_back(std::to_string(v));
        {std::lock_guard<std::mutex> l(mutex_);if(b.position!=board_.position||b.pulses!=board_.pulses||b.position_valid!=board_.position_valid||b.generation!=board_.generation||position_id_.empty())position_id_=boot_+"_"+std::to_string(++position_revision_);
            board_=b;owner_=id;
            if(homing&&b.ready&&b.position_valid&&b.home_start_us!=home_before&&b.home_done_us>=b.home_start_us){require(b.position==std::array<int64_t,3>{0,0,0},"HOME_REFERENCE","HOME completed with unexpected calibration counts");homing=false;phase_="idle";}
            publication_={{"simulation",false},{"source","bsp_snapshot"},{"observed_monotonic_us",std::to_string(now)},{"source_time_us",std::to_string(b.pl_time_us)},{"transport_generation",std::to_string(b.generation)},{"command_position",{{"source","pl_step_counter"},{"position_id",position_id_},{"valid",b.position_valid&&!b.fault},{"steps",positions},{"pulses",pulses}}},{"xyz_estimate",nullptr},{"driver_feedback",b.driver_feedback},{ "calibration",{{"mode","home_counts_only"},{"counts_referenced",b.home_capable&&b.ready&&b.position_valid&&!b.fault},{"contact_reference_steps",{"-150","-150","-150"}},{"pull_complete_steps",{"0","0","0"}},{"xyz_valid",false},{"joint_angles_calibrated",false},{"machine_display_zero","formal_pull_complete_pose_pending_model_mapping"}}},{"raw",b.raw}};}
    }catch(const std::exception &e){active.reset();homing=false;session=0;try{device_->stop();}catch(...){}std::lock_guard<std::mutex> l(mutex_);pending_.reset();phase_="fault";error_=e.what();completion_=false;lost=true;}
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
}
}
