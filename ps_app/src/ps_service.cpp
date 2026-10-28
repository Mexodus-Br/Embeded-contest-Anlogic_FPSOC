#include "ps_runtime.hpp"
#include "ps_backend.hpp"
#include "ps_hardware_port.hpp"
#include "ps_calibration.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <memory>
#include <sstream>
#include <set>

namespace ps {
static void fields(const Json &j,std::initializer_list<const char*> names){require(j.is_object(),"FORMAT","Expected object");for(auto i=j.begin();i!=j.end();++i){bool ok=false;for(auto n:names)ok|=i.key()==n;require(ok,"FORMAT","Unknown field",i.key());}}
static Json task_checked(const Json &t){
    fields(t,{"schema_version","id","points","repeat","parameter_version","work_revision"});require(t.value("schema_version",1)==1,"VERSION","Unsupported task version");
    if(t.contains("parameter_version"))require(t.at("parameter_version").is_string()&&logical_id(t.at("parameter_version")),"FORMAT","Invalid parameter version");
    if(t.contains("id"))require(logical_id(t.at("id").get<std::string>()),"FORMAT","Invalid task ID");
    auto &points=t.at("points");require(points.is_array()&&!points.empty()&&points.size()<=1000,"RESOURCE_LIMIT","Task requires 1..1000 points");
    for(auto &p:points){fields(p,{"xyz_mm","duration_us","dwell_us"});require(p.at("xyz_mm").is_array()&&p.at("xyz_mm").size()==3,"FORMAT","Point needs XYZ");for(auto &x:p.at("xyz_mm"))require(x.is_number()&&std::isfinite(x.get<double>()),"FORMAT","Invalid XYZ");
        for(auto k:{"duration_us","dwell_us"})if(p.contains(k)&&!p.at(k).is_null())require(u64(p.at(k),k)<=3600000000ULL,"RESOURCE_LIMIT","Point duration exceeds fixture limit");}
    auto repeat=t.value("repeat",Json{{"mode","finite"},{"count","1"}});fields(repeat,{"mode","count"});auto mode=repeat.at("mode").get<std::string>();
    require(mode=="finite"||mode=="until_stopped","FORMAT","Unknown repetition mode");if(mode=="finite")require(u64(repeat.at("count"),"repeat.count")>=1&&u64(repeat.at("count"),"repeat.count")<=1000,"RESOURCE_LIMIT","Repeat count must be 1..1000");
    else require(!repeat.contains("count"),"FORMAT","Infinite repeat must not carry count");Json out=t;out["schema_version"]=1;out["repeat"]=repeat;return out;
}
struct Service::Impl {
    struct Preview:PlannedTask {std::string id,position,owner;uint64_t version=0,epoch=0,expires=0;};
    ps_fs::path root,data;
    std::string boot=random_id(),owner,mode="task",phase="idle",position_id=random_id(),parameter_id="host_demo_v1",active_id,last_id,pose_parameter;
    Json params,pose=nullptr,commanded=nullptr,commands=Json::object(),recovery=nullptr,telemetry_history=Json::array(),latest=Json::object();
    std::shared_ptr<const Preview> preview;
    std::unique_ptr<ExecutionBackend> backend;
    std::mutex mutex,file_mutex,preview_mutex,admission_mutex;
    std::atomic<uint64_t> stop_epoch{0};
    std::atomic<bool> quit{false};
    std::string last_hardware_phase;uint64_t last_calibration_sample=0;
    uint64_t handled_stop=0,state_version=1,last_telemetry=0,telem_serial=0,telem_dropped=0,pose_time=0,iteration=0;
    bool position_valid=false;
    bool calibration_verified=false;
    std::string verified_home,verified_generation,verified_revision,work_revision=random_id();
    Json work_origin=Json::array({0,0,0}),last_stationary_joint=nullptr;
    uint64_t stationary_since=0;
    const bool allow_simulation_injection;
    std::string jog_id,jog_owner;uint64_t jog_seq=0,jog_refresh=0,jog_tick=0;int jog_axis=0,jog_sign=1;double jog_speed=0,jog_actual_speed=0;
    Json jog_parameters,jog_planned_pose;std::set<std::string> used_jogs,used_home_requests;
    Logs logs;
    std::thread worker;
    Impl(ps_fs::path r,ps_fs::path d,bool inject,bool hardware,std::shared_ptr<BoardDevice> device):root(std::move(r)),data(std::move(d)),backend(hardware?std::unique_ptr<ExecutionBackend>(new HardwareBackend(device?std::move(device):linux_board(),boot)):simulation_backend()),allow_simulation_injection(inject&&!hardware),logs(boot,data/"logs",!hardware){
        auto request=read_json(root/"scenarios/ps-host.json");params={{"schema_version",1},{"id",parameter_id},{"fixture",request.at("fixture")},{"golden",request.at("golden")}};
        if(ps_fs::exists(data/"selected-parameters.json"))try{auto selected=read_json(data/"selected-parameters.json");std::string id=selected.at("id");require(logical_id(id),"FORMAT","Invalid saved parameter identity");auto p=read_json(data/"parameters"/(id+".json"));validate_calibration(p);params=p;parameter_id=id;}catch(const std::exception &e){logs.emit("parameter_restore_rejected","storage","error",{{"reason",e.what()}});}
        if(ps_fs::exists(data/"work-origin.json"))try{auto w=read_json(data/"work-origin.json");require(w.at("parameter_version")==parameter_id,"VERSION","Stored origin belongs to another calibration");(void)calibrated_vec(w.at("origin_machine_mm"));work_origin=w.at("origin_machine_mm");work_revision=w.at("revision");}catch(const std::exception &e){logs.emit("origin_restore_rejected","storage","warning",{{"reason",e.what()}});}
        if(ps_fs::exists(data/"recovery.json"))try{recovery=read_json(data/"recovery.json");recovery["status"]="unknown";recovery["reason"]="service_restart_requires_reconciliation";}catch(...){recovery={{"status","unknown"},{"reason","recovery_record_unreadable"}};}
        logs.emit("service_started","service","info",{{"position","unknown"},{"recovery",recovery}});worker=std::thread([this]{tick();});
    }
    ~Impl(){quit=true;worker.join();}
    void control(const std::string &session){require(owner==session,"CONTROL_REQUIRED","Acquire control before this operation");}
    void idle(){require(phase=="idle"&&stop_epoch==handled_stop,"BUSY","An execution, stop or fault requires attention");}
    void invalidate(){preview.reset();++state_version;}
    bool production()const{return params.value("schema_version",1)==2;}
    bool valid_position()const{return position_valid&&pose_parameter==parameter_id&&(backend->simulation()||(calibration_verified&&monotonic_us()-pose_time<=u64(params.at("calibration").at("max_age_us"),"max_age_us")));}
    void set_pose(const Json &p,const std::string &parameter=""){pose=p;position_valid=true;position_id=random_id();pose_parameter=parameter.empty()?parameter_id:parameter;pose_time=monotonic_us();}
    Json start()const{return {{"valid",valid_position()},{"position_id",position_id},{"xyz_mm",valid_position()?pose.at("xyz_mm"):Json()},
                             {"steps",valid_position()?pose.at("steps"):Json()}};}
    void transition(const std::string &s){phase=s;if(!active_id.empty()&&commands.contains(active_id)){commands[active_id]["status"]=s;commands[active_id]["updated_monotonic_us"]=std::to_string(monotonic_us());}
        std::string task=active_id.empty()?"":commands.at(active_id).value("task_id",std::string());
        logs.emit(s,"command",s=="failed"?"error":"info",Json::object(),active_id,task);}
    void begin_stop(uint64_t now){handled_stop=stop_epoch.load();if(backend->simulation())backend->request_stop(now);jog_id.clear();invalidate();transition("stopping");}
    void tick(){while(!quit){auto now=monotonic_us();{
        std::lock_guard<std::mutex> lock(mutex);
        if(stop_epoch.load()!=handled_stop)begin_stop(now);
        auto update=backend->poll(now);
        if(!backend->simulation()){
            auto hardware=backend->status();auto hp=hardware.at("phase").get<std::string>();
            if(production())try{
                auto publication=backend->telemetry();
                require(hardware.at("home_ready")==true&&hardware.at("home_done_us")!="0","POSITION_UNKNOWN","Complete HOME required for calibrated feedback");
                auto measured=calibrated_pose(publication,params,monotonic_us());
                bool same=!last_stationary_joint.is_null();
                if(same)for(int a=0;a<3;a++)same= same&&std::abs(double(last_stationary_joint[a])-double(measured.at("joint_deg")[a]))<=0.01;
                if(!same||hardware.at("pulse_safe")!=true||hp!="idle"){stationary_since=now;last_stationary_joint=measured.at("joint_deg");}
                if(!stationary_since){stationary_since=now;last_stationary_joint=measured.at("joint_deg");}
                if(calibration_verified){
                    require(hardware.at("home_done_us")==verified_home&&measured.at("collector_generation")==verified_generation&&measured.at("revision")==verified_revision,"CALIBRATION_STALE","HOME or feedback configuration identity changed");
                    if(!position_valid||pose.at("steps")!=measured.at("steps")||pose.at("joint_deg")!=measured.at("joint_deg")){set_pose(measured);invalidate();}
                    else {pose=measured;pose_time=now;}
                }
            }catch(const std::exception &){if(position_valid){position_valid=false;invalidate();}stationary_since=0;last_stationary_joint=nullptr;
                if(calibration_verified){calibration_verified=false;if(phase=="submitted"||phase=="running"){++stop_epoch;begin_stop(now);}}}
            if(hp!=last_hardware_phase||(hp=="homing"&&now-last_calibration_sample>=100000)){
                auto t=backend->telemetry();Json sample={{"backend",hardware}};
                if(t.is_object()){
                    sample["observed_monotonic_us"]=t.at("observed_monotonic_us");sample["source_time_us"]=t.at("source_time_us");
                    sample["command_position"]=t.at("command_position");sample["calibration"]=t.at("calibration");
                    if(t.at("raw").is_object()){sample["safety_snapshot"]=t.at("raw").at("global");sample["config_id"]=t.at("raw").at("config_id");sample["snapshot_ids"]=t.at("raw").at("snapshot_ids");}
                    if(t.at("driver_feedback").is_object()){
                        auto f=t.at("driver_feedback");sample["feedback_snapshot_id"]=f.at("snapshot_id");sample["feedback_source_time_us"]=f.at("source_time_us");
                        sample["feedback_rows"]=Json::array();for(auto &row:f.at("rows"))if(row.at("slot")==0||row.at("slot")==1)sample["feedback_rows"].push_back(row);
                    }
                }
                logs.emit("home_calibration_observation","hardware","info",sample);
                last_hardware_phase=hp;last_calibration_sample=now;
            }
            if(phase=="homing"&&hp=="idle")phase="idle";
        }
        if(!backend->simulation()&&phase=="fault"&&backend->status().at("phase")=="idle"){phase="idle";active_id.clear();}
        if(update.failed&&phase!="fault"){position_valid=false;invalidate();transition("failed");phase="fault";}
        if(phase=="stopping"&&update.stopped){if(!update.pulse_safe){position_valid=false;transition("failed");phase="fault";}else{transition("cancelled");phase="idle";active_id.clear();}logs.emit("stop_result","backend",update.pulse_safe?"info":"error",{{"pulse_safe",update.pulse_safe},{"simulation",backend->simulation()}});}
        if(!jog_id.empty()&&(now-jog_refresh>350000)){logs.emit("jog_input_timeout","command","warning");++stop_epoch;begin_stop(now);}
        if(!backend->simulation()&&!jog_id.empty()&&phase=="running"&&jog_tick<=now+100000){
            try{while(jog_tick<=now+100000){auto chunk=calibrated_jog_chunk(jog_parameters,jog_planned_pose,jog_axis,jog_sign,jog_speed,jog_actual_speed);backend->manual_target({chunk,jog_id+"_"+std::to_string(jog_tick),50000});jog_planned_pose=chunk.at("last_pose");jog_tick+=50000;}}
            catch(const Error &e){logs.emit("jog_rejected","planner","error",e.detail);++stop_epoch;begin_stop(now);}
        }
        if(backend->simulation()&&!jog_id.empty()&&now-jog_tick>=10000&&phase=="running"){
            double dt=std::min(0.02,double(now-jog_tick)/1e6);jog_tick=now;double acc=jog_parameters.at("fixture").at("acceleration_mm_s2");jog_actual_speed=std::min(jog_speed,jog_actual_speed+acc*dt);
            Json point=pose.at("xyz_mm");point[jog_axis]=double(point[jog_axis])+jog_sign*jog_actual_speed*dt;
            try{auto next=kinematics({{"op","ik"},{"xyz_mm",point},{"golden",jog_parameters.at("golden")}});auto &f=jog_parameters.at("fixture");
                for(int a=0;a<3;a++){require(double(point[a])>=double(f.at("workspace").at("min")[a])&&double(point[a])<=double(f.at("workspace").at("max")[a]),"WORKSPACE_RANGE","Jog reached fixture workspace");
                    require(double(next.at("joint_deg")[a])>=double(f.at("joint_min_deg")[a])&&double(next.at("joint_deg")[a])<=double(f.at("joint_max_deg")[a]),"JOINT_RANGE","Jog joint limit");}
                for(const auto &b:f.at("forbidden_boxes")){double enter=0,leave=1;bool hit=true;for(int a=0;a<3;a++){double begin=pose.at("xyz_mm")[a],delta=double(point[a])-begin,lo=b.at("min")[a],hi=b.at("max")[a];if(delta==0){if(begin<lo||begin>hi)hit=false;}else{double p=(lo-begin)/delta,q=(hi-begin)/delta;if(p>q)std::swap(p,q);enter=std::max(enter,p);leave=std::min(leave,q);}}require(!hit||enter>leave,"PATH_FORBIDDEN","Jog enters forbidden region");}
                uint64_t demand=0;for(int a=0;a<3;a++){require(std::abs(double(next.at("joint_deg")[a])-double(pose.at("joint_deg")[a]))<=double(f.at("max_joint_step_deg")),"PATH_DISCONTINUITY","Jog branch jump");demand=std::max(demand,uint64_t(std::abs(i64(next.at("steps")[a],"steps")-i64(pose.at("steps")[a],"steps"))));}
                require(!demand||double(u64(f.at("segment_guard_us"),"guard")+demand*u64(f.at("pulse_interval_us"),"interval"))<=dt*1e6,"PULSE_RATE","Jog pulse demand exceeds fixture");
                // Validate intermediate IK samples, including narrow singular regions.
                const double distance=std::abs(double(point[jog_axis])-double(pose.at("xyz_mm")[jog_axis]));
                const auto count=size_t(std::ceil(distance/double(f.at("max_sample_distance_mm"))));
                require(count<=1000,"RESOURCE_LIMIT","Jog tick exceeds bounded validation budget");
                Json previous=pose;
                for(size_t n=1;n<=std::max<size_t>(1,count);n++){
                    Json xyz=pose.at("xyz_mm");xyz[jog_axis]=double(xyz[jog_axis])+(double(point[jog_axis])-double(xyz[jog_axis]))*double(n)/std::max<size_t>(1,count);
                    auto sample=n==std::max<size_t>(1,count)?next:kinematics({{"op","ik"},{"xyz_mm",xyz},{"golden",jog_parameters.at("golden")}});
                    for(int a=0;a<3;a++){require(double(sample.at("joint_deg")[a])>=double(f.at("joint_min_deg")[a])&&double(sample.at("joint_deg")[a])<=double(f.at("joint_max_deg")[a]),"JOINT_RANGE","Intermediate jog joint limit");
                        require(std::abs(double(sample.at("joint_deg")[a])-double(previous.at("joint_deg")[a]))<=double(f.at("max_joint_step_deg")),"PATH_DISCONTINUITY","Intermediate jog branch jump");}previous=std::move(sample);
                }
                backend->manual_target({next,jog_id+"_"+std::to_string(jog_tick),uint64_t(dt*1e6)});set_pose(next,jog_parameters.at("id"));commanded=next;
            }catch(const Error &e){logs.emit("jog_rejected","planner","error",e.detail);++stop_epoch;begin_stop(now);}
        }
        if(jog_id.empty()&&(phase=="submitted"||phase=="running")){
            if(phase=="submitted"&&(backend->simulation()||update.accepted))transition("running");
            if(!update.pose.is_null())set_pose(update.pose,update.parameter);
            if(update.iteration!=iteration){iteration=update.iteration;if(!update.completed)logs.emit("task_iteration","backend","info",{{"iteration",std::to_string(iteration)}},active_id,commands.at(active_id).value("task_id",std::string()));}
            if(update.completed){invalidate();transition("completed");phase="idle";active_id.clear();}
        }
    }std::this_thread::sleep_for(std::chrono::milliseconds(5));}}
    Json status(){auto log_stats=logs.stats();std::lock_guard<std::mutex> lock(mutex);auto now=monotonic_us();bool valid=valid_position();Json position={{"source",valid?(backend->simulation()?"simulation":"encoder_0x30_calibrated_fk"):"unknown"},{"model",backend->simulation()?"sample_endpoint_simulation":"golden_sphere_fk"},{"valid",valid},{"stale",!valid},
        {"position_id",position_id},{"parameter_version",pose_parameter},{"xyz_mm",valid?pose.at("xyz_mm"):Json()},{"joint_deg",valid?pose.at("joint_deg"):Json()},{"steps",valid?pose.at("steps"):Json()},{"updated_monotonic_us",std::to_string(pose_time)}};
        position["machine_xyz_mm"]=valid?pose.at("xyz_mm"):Json();position["work_xyz_mm"]=valid?translated(pose.at("xyz_mm"),work_origin,-1):Json();position["work_origin_machine_mm"]=work_origin;position["work_revision"]=work_revision;
        return {{"schema_version",1},{"boot_id",boot},{"simulation",backend->simulation()},{"simulation_injection_enabled",allow_simulation_injection},{"calibration_verified",calibration_verified},{"mode",mode},{"phase",stop_epoch!=handled_stop?"stopping":phase},{"state_version",std::to_string(state_version)},
            {"monotonic_us",std::to_string(now)},{"stop_epoch",std::to_string(stop_epoch)},{"handled_stop_epoch",std::to_string(handled_stop)},{"parameter_version",parameter_id},{"position",position},{"target",commanded},
            {"active_command_id",active_id.empty()?Json():Json(active_id)},{"command",last_id.empty()?Json():commands.at(last_id)},
            {"recovery",recovery},{"control_owned",!owner.empty()},{"preview_id",preview?Json(preview->id):Json()},{"backend",backend->status()},{"logs",log_stats}};
    }
};
Service::Service(const ps_fs::path &r,const ps_fs::path &d,bool inject,bool hardware,std::shared_ptr<BoardDevice> device):impl_(new Impl(r,d,inject,hardware,std::move(device))){}
Service::~Service(){delete impl_;}
std::string Service::boot_id()const{return impl_->boot;}
Json Service::state(){return impl_->status();}
void Service::revoke_session(const std::string &session){auto &s=*impl_;std::lock_guard<std::mutex> l(s.mutex);if(s.owner!=session)return;s.owner.clear();s.invalidate();if(s.jog_owner==session&&!s.jog_id.empty())++s.stop_epoch;s.logs.emit("control_revoked","service");}
Json Service::stop(const std::string &session){(void)session;auto &s=*impl_;auto epoch=++s.stop_epoch;if(!s.backend->simulation())s.backend->request_stop(monotonic_us());s.logs.emit("stop_requested","command","info",{{"stop_epoch",std::to_string(epoch)}});return {{"status","received"},{"stop_epoch",std::to_string(epoch)},{"simulation",s.backend->simulation()}};}
Json Service::events(uint64_t id){return impl_->logs.events_after(id);}
std::string Service::export_log(const std::string &id){return impl_->logs.export_jsonl(id);}
Json Service::handle(const std::string &method,const std::string &path,const std::map<std::string,std::string> &query,const Json &body,const std::string &session){auto &s=*impl_;
    if(method=="GET"&&path=="/state"){auto r=state();{std::lock_guard<std::mutex> l(s.mutex);r["you_control"]=s.owner==session;}return r;}
    if(method=="POST"&&path=="/stop")return stop(session);
    if(method=="POST"&&path=="/calibration/verify"){
        fields(body,{"boot_id","parameter_version","home_done_us"});std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();
        require(!s.backend->simulation()&&s.production(),"CALIBRATION_REQUIRED","Versioned real calibration required");
        auto b=s.backend->status();auto now=monotonic_us();
        require(body.at("boot_id")==s.boot&&body.at("parameter_version")==s.parameter_id&&body.at("home_done_us")==b.at("home_done_us"),"STALE_INPUT","Verification bindings changed");
        require(b.at("home_ready")==true&&b.at("pulse_safe")==true&&b.at("phase")=="idle"&&s.stationary_since&&now-s.stationary_since>=200000,"NOT_SETTLED","Fresh HOME and 200ms stable encoder observations required");
        auto publication=s.backend->telemetry();auto measured=calibrated_pose(publication,s.params,monotonic_us());s.verified_home=b.at("home_done_us");s.verified_generation=measured.at("collector_generation");s.verified_revision=measured.at("revision");s.calibration_verified=true;s.set_pose(measured);s.invalidate();
        s.logs.emit("calibration_verified","service","info",{{"parameters",s.parameter_id},{"home_done_us",s.verified_home},{"source_rows",measured.at("source_rows")}});return {{"verified",true},{"position",measured},{"executed",false}};
    }
    if(method=="POST"&&path=="/coordinates/zero"){
        fields(body,{"boot_id","parameter_version","position_id"});Json saved;
        {std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();
            require(body.at("boot_id")==s.boot&&body.at("parameter_version")==s.parameter_id&&body.at("position_id")==s.position_id,"STALE_INPUT","Zero-point identity changed");
            require(s.valid_position(),"POSITION_UNKNOWN","Reliable fresh machine position required");
            if(!s.backend->simulation()){auto b=s.backend->status();require(b.at("phase")=="idle"&&b.at("pulse_safe")==true&&s.stationary_since&&monotonic_us()-s.stationary_since>=200000,"NOT_SETTLED","Stopped and stable feedback required");}
            s.work_origin=s.pose.at("xyz_mm");s.work_revision=random_id();s.invalidate();saved={{"schema_version",1},{"revision",s.work_revision},{"parameter_version",s.parameter_id},{"origin_machine_mm",s.work_origin},{"position_id",s.position_id},{"boot_id",s.boot}};
        }
        {std::lock_guard<std::mutex> f(s.file_mutex);atomic_save(s.data/"work-origin.json",saved);}
        s.logs.emit("work_origin_set","service","info",saved);return saved;
    }
    if(method=="POST"&&path=="/hardware/action"){
        fields(body,{"action","boot_id","owner_id","cancel_epoch","request_id","deadline_monotonic_us"});std::lock_guard<std::mutex> l(s.mutex);s.control(session);
        if(s.phase!="fault")s.idle();
        require(body.at("boot_id")==s.boot,"BOOT_MISMATCH","Old hardware action rejected");
        if(body.at("action")=="home"){
            s.idle();auto b=s.backend->status();auto now=monotonic_us();
            require(body.contains("owner_id")&&body.contains("cancel_epoch")&&body.contains("request_id")&&body.contains("deadline_monotonic_us"),"HOME_BINDING_REQUIRED","HOME requires current owner/cancel identity, request ID and deadline");
            require(body.at("owner_id")==b.at("owner_id")&&body.at("cancel_epoch")==b.at("cancel_epoch"),"STALE_ACTION","HOME owner/cancel binding changed");
            auto deadline=u64(body.at("deadline_monotonic_us"),"deadline_monotonic_us");
            require(deadline>now&&deadline-now>=100000&&deadline-now<=2000000,"EXPIRED","HOME start deadline requires 0.1..2 seconds remaining");
            auto request=body.at("request_id").get<std::string>();require(logical_id(request)&&s.used_home_requests.size()<1024&&!s.used_home_requests.count(request),"ID_CONFLICT","HOME request already used or ledger full");
            s.used_home_requests.insert(request);
        }
        s.backend->action(body.at("action").get<std::string>());s.logs.emit("hardware_action_queued","hardware","info",body);if(body.at("action")=="home")s.phase="homing";s.position_valid=false;s.calibration_verified=false;s.stationary_since=0;s.invalidate();return {{"status","queued"},{"simulation",false}};
    }
    if(method=="POST"&&path=="/control"){fields(body,{"action"});std::lock_guard<std::mutex> l(s.mutex);if(!s.backend->simulation()&&s.phase=="fault")require(s.stop_epoch==s.handled_stop,"BUSY","STOP still pending");else s.idle();auto a=body.value("action",std::string("acquire"));require(a=="acquire"||a=="release","FORMAT","Unknown control action");
        require(s.owner.empty()||s.owner==session,"CONTROL_BUSY","Control belongs to another session");s.owner=a=="release"?"":session;s.invalidate();s.logs.emit("control_"+a);return {{"you_control",s.owner==session}};}
    if(method=="POST"&&path=="/mode"){fields(body,{"mode"});auto m=body.at("mode").get<std::string>();require(m=="task"||m=="manual","FORMAT","Unknown mode");std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();s.mode=m;s.invalidate();return {{"mode",m}};}
    if(method=="POST"&&path=="/preview/cancel"){fields(body,{});std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.invalidate();return {{"cancelled",true}};}
    if(method=="POST"&&path=="/preview"){
        fields(body,{"schema_version","parameter_version","start_position_id","task"});require(body.value("schema_version",1)==1,"VERSION","Unsupported request version");
        std::unique_lock<std::mutex> planning(s.preview_mutex,std::try_to_lock);require(bool(planning),"BUSY","Another preview is being computed");auto p=std::make_shared<Impl::Preview>();Json params,start;
        {std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();require(s.mode=="task","MODE","Select coordinate/task mode");s.preview.reset();
            require(body.at("parameter_version")==s.parameter_id&&body.at("start_position_id")==s.position_id,"PREVIEW_STALE","Parameter or start identity changed");
            p->id=random_id();p->parameter=s.parameter_id;p->position=s.position_id;p->owner=session;p->version=s.state_version;p->epoch=s.stop_epoch;p->expires=monotonic_us()+30000000;params=s.params;start=s.start();}
        p->task=task_checked(body.at("task"));if(p->task.contains("parameter_version"))require(p->task.at("parameter_version")==p->parameter,"PARAMETER_MISMATCH","Task binds another parameter version");p->task["parameter_version"]=p->parameter;
        {std::lock_guard<std::mutex> l(s.mutex);if(s.production())require(p->task.value("work_revision",std::string())==s.work_revision,"COORDINATE_STALE","Task belongs to an old work origin; explicitly edit/reteach it");}
        Json origin;{std::lock_guard<std::mutex> l(s.mutex);origin=s.work_origin;}
        p->first=params.value("schema_version",1)==2?calibrated_plan(params,start,p->task.at("points"),origin):plan({{"op","plan"},{"fixture",params.at("fixture")},{"golden",params.at("golden")},{"start",start},{"points",p->task.at("points")}});
        auto rep=p->task.at("repeat");bool loop=rep.at("mode")=="until_stopped"||u64(rep.at("count"),"count")>1;
        if(loop&&p->first.at("executable").get<bool>()){auto target=p->first.at("target");if(params.value("schema_version",1)==2)p->cycle=calibrated_plan(params,{{"valid",true},{"position_id","validated_cycle_start"},{"xyz_mm",target.at("machine_xyz_mm")},{"steps",target.at("steps")}},p->task.at("points"),origin);else p->cycle=plan({{"op","plan"},{"fixture",params.at("fixture")},{"golden",params.at("golden")},
            {"start",{{"valid",true},{"position_id","validated_cycle_start"},{"xyz_mm",target.at("xyz_mm")},{"steps",target.at("steps")}}},{"points",p->task.at("points")}});}
        {std::lock_guard<std::mutex> l(s.mutex);require(s.state_version==p->version&&s.position_id==p->position&&s.stop_epoch==p->epoch&&s.phase=="idle","PREVIEW_STALE","State changed during planning");s.preview=p;s.commanded=p->first.at("target");}
        auto result=p->first;result.erase("samples");result["sample_count"]=p->first.at("samples").size();result["preview_id"]=p->id;result["parameter_version"]=p->parameter;result["state_version"]=std::to_string(p->version);result["expires_monotonic_us"]=std::to_string(p->expires);
        result["repeat"]=rep;result["cycle_duration_us"]=loop&&p->first.at("executable").get<bool>()?p->cycle.at("duration_us"):Json();s.logs.emit("preview_validated","planner","info",{{"executable",p->first.at("executable")}});return result;
    }
    if(method=="POST"&&path=="/commands"){
        fields(body,{"boot_id","client_command_id","preview_id","deadline_monotonic_us"});std::string id=body.at("client_command_id");require(logical_id(id),"FORMAT","Invalid command ID");
        require(body.at("preview_id").is_string()&&logical_id(body.at("preview_id")),"FORMAT","Invalid preview identity");(void)u64(body.at("deadline_monotonic_us"),"deadline_monotonic_us");
        {std::lock_guard<std::mutex> l(s.mutex);require(body.at("boot_id")==s.boot,"BOOT_MISMATCH","Old boot identity is never replayed");
            if(s.commands.contains(id)){require(s.commands[id].at("request")==body,"ID_CONFLICT","ID already used for different command");
                if(s.commands[id].contains("error")){auto d=s.commands[id].at("error");Error e(d.at("code"),d.at("message"));e.detail=d;throw e;}return s.commands[id];}
            s.control(session);require(s.commands.size()<1024,"RESOURCE_LIMIT","Command identity ledger full; no identities evicted");
            s.commands[id]={{"boot_id",s.boot},{"command_id",id},{"status","received"},{"request",body},{"simulation",s.backend->simulation()},{"task_id",""}};}
        s.logs.emit("received","command","info",Json::object(),id);
        try{
            std::unique_lock<std::mutex> admission(s.admission_mutex,std::try_to_lock);require(bool(admission),"BUSY","Another command is being admitted");
            std::shared_ptr<const Impl::Preview> p;uint64_t epoch;
            {std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();require(s.mode=="task","MODE","Select task mode");
                p=s.preview;require(p&&p->id==body.at("preview_id")&&p->owner==session,"PREVIEW_STALE","Preview missing or superseded");epoch=s.stop_epoch;
                require(p->first.at("executable").get<bool>(),"POSITION_UNKNOWN","Preview is not executable");require(p->version==s.state_version&&p->position==s.position_id&&p->parameter==s.parameter_id&&p->epoch==epoch,"PREVIEW_STALE","Preview bindings changed");
                auto now=monotonic_us(),deadline=u64(body.at("deadline_monotonic_us"),"deadline_monotonic_us");require(now<deadline&&deadline<=now+2000000&&now<p->expires,"EXPIRED","Command or preview deadline invalid");
                s.commands[id]["status"]="validated";s.commands[id]["task_id"]=p->task.value("id",std::string());}
            s.logs.emit("validated","command","info",Json::object(),id,p->task.value("id",std::string()));
            // Admission is serialized, but disk/network never hold the motion mutex.
            {std::lock_guard<std::mutex> file(s.file_mutex);atomic_save(s.data/"recovery.json",{{"boot_id",s.boot},{"command_id",id},{"status","unknown"},{"reason","accepted_execution_requires_reconciliation_on_restart"}});}
            std::lock_guard<std::mutex> l(s.mutex);s.idle();require(s.stop_epoch==epoch&&p==s.preview&&s.position_id==p->position&&s.parameter_id==p->parameter&&monotonic_us()<u64(body.at("deadline_monotonic_us"),"deadline"),"PREVIEW_STALE","Execution conditions changed before submission");
            s.active_id=s.last_id=id;s.iteration=0;ExecutionBinding binding;
            if(!s.backend->simulation()){auto bs=s.backend->status();binding.boot_id=s.boot;binding.command_id=id;binding.parameter_revision=p->parameter;binding.start_position_id=bs.at("position_id");binding.cancel_epoch=u64(bs.at("cancel_epoch"),"cancel");binding.generation=uint32_t(u64(bs.at("generation"),"generation"));for(int a=0;a<3;a++)binding.start_steps[a]=i64(s.pose.at("steps")[a],"steps");}
            s.backend->submit(p,monotonic_us(),binding);s.preview.reset();s.transition("submitted");return s.commands[id];
        }catch(const Error &e){std::lock_guard<std::mutex> l(s.mutex);s.commands[id]["status"]="failed";s.commands[id]["error"]=e.detail;s.logs.emit("rejected","command","warning",e.detail,id,s.commands[id].value("task_id",std::string()));throw;}
        catch(const std::exception &){Error e("STORAGE","Admission failed before execution; inspect local storage");std::lock_guard<std::mutex> l(s.mutex);s.commands[id]["status"]="failed";s.commands[id]["error"]=e.detail;throw e;}
    }
    if(method=="GET"&&path.rfind("/commands/",0)==0){auto id=path.substr(10);std::lock_guard<std::mutex> l(s.mutex);require(s.commands.contains(id),"UNKNOWN_ID","No dedupe result for this identity");return s.commands[id];}
    if(path.rfind("/parameters/",0)==0||path.rfind("/tasks/",0)==0){bool parameter=path.rfind("/parameters/",0)==0;auto id=path.substr(parameter?12:7);require(logical_id(id),"FORMAT","Only logical document IDs accepted");auto dir=s.data/(parameter?"parameters":"tasks"),file=dir/(id+".json");
        if(method=="GET"){if(parameter){{std::lock_guard<std::mutex> l(s.mutex);if(id==s.parameter_id)return s.params;}if(id=="host_demo_v1"){auto d=read_json(s.root/"scenarios/ps-host.json");return {{"schema_version",1},{"id",id},{"fixture",d.at("fixture")},{"golden",d.at("golden")}};}}std::lock_guard<std::mutex> f(s.file_mutex);return read_json(file);}
        if(method=="PUT"){Json value=body;{std::lock_guard<std::mutex> l(s.mutex);s.control(session);}require(value.at("id")==id,"FORMAT","Document identity mismatch");
            if(parameter){fields(value,{"schema_version","id","fixture","golden","calibration"});require(value.at("schema_version")==1||value.at("schema_version")==2,"VERSION","Unsupported parameter version");
                if(value.at("schema_version")==2)validate_calibration(value);
                require(s.backend->simulation()||value.at("schema_version")==2,"CALIBRATION_REQUIRED","Host fixtures cannot qualify physical motion");
                if(id=="host_demo_v1"){auto d=read_json(s.root/"scenarios/ps-host.json");require(value.at("fixture")==d.at("fixture")&&value.at("golden")==d.at("golden"),"VERSION_CONFLICT","Built-in parameter version is immutable");}
                if(value.at("schema_version")==1)(void)plan({{"op","plan"},{"fixture",value.at("fixture")},{"golden",value.at("golden")},{"start",{{"valid",false},{"position_id","unknown"},{"xyz_mm",nullptr},{"steps",nullptr}}},{"points",Json::array({{{"xyz_mm",{0,0,-140}}}})}});}
            else{value=task_checked(value);std::lock_guard<std::mutex> l(s.mutex);if(!value.contains("parameter_version"))value["parameter_version"]=s.parameter_id;}
            {std::lock_guard<std::mutex> f(s.file_mutex);if(ps_fs::exists(file))require(read_json(file)==value,"VERSION_CONFLICT","Existing versions are immutable; choose a new ID");else atomic_save(file,value);}
            if(parameter){
                if(value.at("schema_version")==2){std::lock_guard<std::mutex> f(s.file_mutex);atomic_save(s.data/"selected-parameters.json",{{"id",id}});}
                std::lock_guard<std::mutex> l(s.mutex);if(!s.backend->simulation())s.idle();bool changed=s.parameter_id!=id;s.params=value;s.parameter_id=id;s.calibration_verified=false;if(!s.backend->simulation())s.position_valid=false;s.stationary_since=0;s.last_stationary_joint=nullptr;if(changed){s.work_origin=Json::array({0,0,0});s.work_revision=random_id();}s.invalidate();}
            s.logs.emit("document_saved","storage","info",{{"kind",parameter?"parameters":"task"},{"id",id}});return {{"saved",true},{"id",id},{"executed",false}};}
    }
    if(method=="GET"&&(path=="/parameters"||path=="/tasks")){bool parameter=path=="/parameters";Json ids=Json::array();std::lock_guard<std::mutex> f(s.file_mutex);auto dir=s.data/(parameter?"parameters":"tasks");if(ps_fs::exists(dir))for(auto &e:ps_fs::directory_iterator(dir))if(e.path().extension()==".json")ids.push_back(e.path().stem().string());if(parameter&&std::find(ids.begin(),ids.end(),"host_demo_v1")==ids.end())ids.push_back("host_demo_v1");return {{"ids",ids}};}
    if(method=="POST"&&path=="/teach"){std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();require(s.valid_position(),"POSITION_UNKNOWN","Cannot teach unknown position");if(!s.backend->simulation())require(s.stationary_since&&monotonic_us()-s.stationary_since>=200000&&s.backend->status().at("pulse_safe")==true,"NOT_SETTLED","Teach requires stopped and stable encoder observations");return {{"point",{{"xyz_mm",translated(s.pose.at("xyz_mm"),s.work_origin,-1)}}},{"source",s.backend->simulation()?"simulation":"encoder_0x30_calibrated_fk"},{"position_id",s.position_id},{"parameter_version",s.parameter_id},{"work_revision",s.work_revision}};}
    if(method=="POST"&&path=="/jog/start"){
        fields(body,{"boot_id","jog_id","axis","sign","speed_mm_s","refresh_seq","stop_epoch","deadline_monotonic_us"});std::lock_guard<std::mutex> l(s.mutex);s.control(session);s.idle();require(s.mode=="manual","MODE","Select manual mode");require(s.valid_position(),"POSITION_UNKNOWN","Jog requires valid simulation position");require(body.at("boot_id")==s.boot,"BOOT_MISMATCH","Old jog boot identity");
        require(u64(body.at("stop_epoch"),"stop_epoch")==s.stop_epoch,"STALE_INPUT","A newer STOP invalidated this start");auto now=monotonic_us(),deadline=u64(body.at("deadline_monotonic_us"),"deadline");require(deadline>now&&deadline<=now+2000000,"EXPIRED","Jog start expired");
        auto axis=body.at("axis").get<std::string>(),id=body.at("jog_id").get<std::string>();require(axis=="x"||axis=="y"||axis=="z","FORMAT","One axis required");require(logical_id(id),"FORMAT","Invalid jog identity");
        int sign=body.at("sign");double speed=body.at("speed_mm_s");require((sign==1||sign==-1)&&std::isfinite(speed)&&speed>0&&speed<=double(s.params.at("fixture").at("speed_mm_s")),"CONFIG_RANGE","Jog speed/sign invalid");
        require(!s.used_jogs.count(id),"STALE_INPUT","Jog IDs cannot be replayed");require(s.used_jogs.size()<1024,"RESOURCE_LIMIT","Jog identity ledger full");
        require(u64(body.at("refresh_seq"),"refresh_seq")==0,"STALE_INPUT","Jog session starts at sequence zero");s.used_jogs.insert(id);s.jog_parameters=s.params;s.jog_planned_pose=s.pose;s.jog_id=id;s.jog_owner=session;s.jog_seq=0;s.jog_refresh=s.jog_tick=monotonic_us();s.jog_axis=axis=="x"?0:axis=="y"?1:2;s.jog_sign=sign;s.jog_speed=speed;s.jog_actual_speed=0;s.invalidate();s.phase="running";s.logs.emit("jog_started");return {{"jog_id",id},{"status","running"},{"expires_in_us","350000"}};
    }
    if(method=="POST"&&(path=="/jog/refresh"||path=="/jog/end")){fields(body,{"boot_id","jog_id","refresh_seq"});{std::lock_guard<std::mutex> l(s.mutex);require(body.at("boot_id")==s.boot&&body.at("jog_id")==s.jog_id&&s.jog_owner==session&&!s.jog_id.empty(),"STALE_INPUT","Jog session is no longer active");auto seq=u64(body.at("refresh_seq"),"refresh_seq");require(seq>s.jog_seq,"STALE_INPUT","Old refresh rejected without renewing lease");s.jog_seq=seq;if(path=="/jog/refresh"){s.jog_refresh=monotonic_us();return {{"status","running"}};}}return stop(session);}
    if(method=="POST"&&path.rfind("/simulation/",0)==0)require(s.backend->simulation()&&s.allow_simulation_injection,"SIMULATION_DISABLED","Simulation injection requires explicit launch capability");
    if(method=="POST"&&path=="/simulation/inject"){
        fields(body,{"kind","disk_failure","pause_log_writer","count"});auto kind=body.at("kind").get<std::string>();
        if(kind=="logs"){s.logs.inject(body.value("disk_failure",false),body.value("pause_log_writer",false));return {{"applied",true}};}
        if(kind=="log_burst"){auto n=u64(body.at("count"),"count");require(n<=12000,"RESOURCE_LIMIT","Burst capped at 12000");for(uint64_t i=0;i<n;i++)s.logs.emit("fixture_event","simulation","info",{{"text","中文日志\n第二行"},{"ordinal",std::to_string(i)}});return s.logs.stats();}
        std::lock_guard<std::mutex> l(s.mutex);s.control(session);
        if(kind=="stop_failure"){dynamic_cast<SimulationControl&>(*s.backend).inject_stop_failure(true);return {{"applied",true}};}
        if(kind=="clear_stop_failure"){dynamic_cast<SimulationControl&>(*s.backend).inject_stop_failure(false);return {{"applied",true}};}
        if(kind=="fault"){s.backend->request_stop(monotonic_us());s.jog_id.clear();s.position_valid=false;s.transition("failed");s.phase="fault";s.invalidate();return {{"applied",true}};}
        s.idle();if(kind=="position_unknown")s.position_valid=false;
        else if(kind=="reference_position"){s.set_pose(kinematics({{"op","ik"},{"xyz_mm",{0,0,-140}},{"golden",s.params.at("golden")}}));s.recovery=nullptr;}
        else throw Error("FORMAT","Unknown simulation injection");s.invalidate();s.logs.emit(kind,"simulation");return {{"applied",true},{"simulation",s.backend->simulation()}};
    }
    if(method=="POST"&&path=="/simulation/telemetry"){
        {std::lock_guard<std::mutex> l(s.mutex);s.control(session);}std::ifstream f(s.root/"ps_partner_v1_1_20261022_005289b/ps_partner_v1/samples/telemetry_rtl_frames.hex");require(bool(f),"NOT_FOUND","Frozen telemetry fixture missing");Json rows=Json::array();std::string line;while(std::getline(f,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();if(!line.empty())rows.push_back(telemetry_decode({{"op","telemetry_decode"},{"hex",line},{"byte_order","verilog_msb_hex"}}));}
        std::lock_guard<std::mutex> l(s.mutex);s.latest=Json::object();s.telemetry_history=Json::array();s.telem_serial=0;s.telem_dropped=0;
        for(auto row:rows){uint64_t serial=u64(row.at("completion_serial"),"serial");if(s.telem_serial&&serial>s.telem_serial+1)s.telem_dropped+=serial-s.telem_serial-1;s.telem_serial=serial;
            std::string key=std::to_string(row.at("address").get<int>())+":"+std::to_string(row.at("query").get<int>());auto &entry=s.latest[key];
            if(entry.is_null()||entry.at("last_result").at("collector_generation")!=row.at("collector_generation")||entry.at("last_result").at("transport_generation")!=row.at("transport_generation")||entry.at("last_result").at("revision")!=row.at("revision"))entry={{"last_valid",nullptr}};
            if(row.at("data_valid").get<bool>())entry["last_valid"]=row;entry["last_result"]=row;entry["observed_monotonic_us"]=std::to_string(monotonic_us());s.telemetry_history.push_back(row);
        }s.last_telemetry=monotonic_us();s.logs.emit("telemetry_replayed","telemetry","info",{{"frames",rows.size()},{"missing_serials",std::to_string(s.telem_dropped)}});return {{"frames",rows.size()},{"simulation",s.backend->simulation()}};
    }
    if(method=="GET"&&path=="/telemetry/history"&&!s.backend->simulation()){auto r=s.backend->history();return r.is_null()?Json{{"source","unavailable"},{"history",Json::array()},{"history_complete",false}}:r;}
    if(method=="GET"&&path=="/telemetry"&&!s.backend->simulation()){auto r=s.backend->telemetry();if(r.is_null())return {{"simulation",false},{"source","unavailable"},{"stale",true}};r["stale"]=monotonic_us()-u64(r.at("observed_monotonic_us"),"observation")>=250000;return r;}
    if(method=="GET"&&path=="/telemetry"){std::lock_guard<std::mutex> l(s.mutex);auto latest=s.latest;bool stale=!s.last_telemetry||monotonic_us()-s.last_telemetry>500000;for(auto i=latest.begin();i!=latest.end();++i){i.value()["stale"]=stale;i.value()["source"]="frozen_fixture_replay";}
        Json active=nullptr;if(!s.telemetry_history.empty()){auto &last=s.telemetry_history.back();active={{"collector_generation",last.at("collector_generation")},{"transport_generation",last.at("transport_generation")},{"revision",last.at("revision")}};
            for(auto &entry:latest){bool current=true;for(auto k:{"collector_generation","transport_generation","revision"})current&=entry.at("last_result").at(k)==active.at(k);entry["current_generation"]=current;entry["stale"]=stale||!current;}}
        return {{"simulation",s.backend->simulation()},{"latest",latest},{"history",s.telemetry_history},{"active_identity",active},{"stale",stale},{"missing_serials",std::to_string(s.telem_dropped)},{"xyz_feedback",nullptr}};}
    if(method=="POST"&&path=="/logs/snapshots")return s.logs.snapshot(body);
    if(method=="GET"&&path=="/logs"){for(auto &q:query)require(q.first=="snapshot"||q.first=="cursor"||q.first=="limit","FORMAT","Unknown log query field");auto id=query.at("snapshot");size_t offset=0;if(query.count("cursor")){auto c=query.at("cursor");require(c.rfind(id+":",0)==0,"FORMAT","Cursor belongs to another snapshot");offset=size_t(u64(c.substr(id.size()+1),"cursor"));}size_t limit=query.count("limit")?size_t(u64(query.at("limit"),"limit")):50;return s.logs.page(id,offset,limit);}
    if(method=="GET"&&path=="/logs/boots"){require(query.empty(),"FORMAT","Unexpected boot query");return s.logs.boots();}
    if(method=="GET"&&path.rfind("/logs/",0)==0){for(const auto &q:query)require(q.first=="boot_id","FORMAT","Unknown detail query");return s.logs.detail(path.substr(6),query.count("boot_id")?query.at("boot_id"):"");}
    throw Error("NOT_FOUND","Unknown API endpoint");
}
}
