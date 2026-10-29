#pragma once
#include "ps_core.hpp"
#include <array>
#include <cmath>
#include <algorithm>

namespace ps {
// PS-only schema v2. No PL register or frozen Golden protocol is changed.
inline double calibrated_number(const Json &v){require(v.is_number(),"FORMAT","Calibration requires numeric values");double x=v.get<double>();require(std::isfinite(x),"FORMAT","Nonfinite calibration value");return x;}
inline std::array<double,3> calibrated_vec(const Json &v){require(v.is_array()&&v.size()==3,"FORMAT","Expected three calibration values");std::array<double,3> r{};for(int a=0;a<3;a++)r[a]=calibrated_number(v[a]);return r;}
inline Json translated(const Json &v,const Json &offset,double sign){auto p=calibrated_vec(v),o=calibrated_vec(offset);for(int a=0;a<3;a++)p[a]+=sign*o[a];return p;}
inline double encoder_units(const Json &v){
    // Explicit calibrated interpretation, not a reinterpretation of raw48.
    require(v.is_object()&&v.contains("carry")&&v.contains("value"),"FORMAT","Encoder carry/value required");
    auto carry=i64(v.at("carry"),"carry");auto value=calibrated_number(v.at("value"));
    require(carry>=INT32_MIN&&carry<=INT32_MAX&&value>=0&&value<=65535&&std::floor(value)==value,"CONFIG_RANGE","Invalid raw encoder fields");
    return double(carry)*65536.0+value;
}
inline Json calibration_home(const Json &p){return forward_kinematics({{"op","fk"},{"joint_deg",p.at("calibration").at("home_joint_deg")},{"golden",p.at("golden")}});}
inline void validate_calibration(const Json &p){
    require(p.at("schema_version")==2,"VERSION","Production calibration requires schema 2");
    require(p.at("golden").is_object()&&p.at("golden").empty(),"CONFIG_RANGE","Frozen factory Golden geometry/gearing must be retained");
    const auto &c=p.at("calibration"),&f=p.at("fixture");
    require(c.at("reference_id").is_string()&&!c.at("reference_id").get<std::string>().empty(),"CONFIG_RANGE","Mechanical reference identity required");
    require(c.at("encoder_interpretation")=="signed_turns_plus_u16_fraction","CONFIG_RANGE","Explicit encoder interpretation required");
    auto home=calibrated_vec(c.at("home_joint_deg")),scale=calibrated_vec(c.at("encoder_units_per_joint_deg")),sign=calibrated_vec(c.at("pl_sign"));
    auto lo=calibrated_vec(c.at("physical_min_deg")),hi=calibrated_vec(c.at("physical_max_deg")),ml=calibrated_vec(c.at("margin_min_deg")),mh=calibrated_vec(c.at("margin_max_deg"));
    auto jl=calibrated_vec(f.at("joint_min_deg")),jh=calibrated_vec(f.at("joint_max_deg"));
    require(c.at("encoder_home").is_array()&&c.at("encoder_home").size()==3,"FORMAT","Three encoder references required");
    auto tol=calibrated_number(c.at("tracking_tolerance_deg"));require(tol>0&&tol<=1,"CONFIG_RANGE","Tracking tolerance must be in (0,1] degrees");
    for(int a=0;a<3;a++){
        require(std::abs(scale[a])>=1&&std::abs(scale[a])<=1e9&&(sign[a]==1||sign[a]==-1),"CONFIG_RANGE","Encoder scale or PL sign invalid");
        require(lo[a]<hi[a]&&ml[a]>tol&&mh[a]>tol&&lo[a]+ml[a]<hi[a]-mh[a],"CONFIG_RANGE","Independent positive mechanical margins must exceed tracking tolerance");
        require(jl[a]>=lo[a]+ml[a]&&jh[a]<=hi[a]-mh[a]&&jl[a]<jh[a],"CONFIG_RANGE","Software bounds exceed measured mechanical margins");
        require(home[a]>=jl[a]&&home[a]<=jh[a],"CONFIG_RANGE","Formal HOME pull pose must be inside software joint bounds");
        (void)encoder_units(c.at("encoder_home")[a]);
    }
    require(u64(c.at("max_age_us"),"max_age_us")>0&&u64(c.at("max_age_us"),"max_age_us")<=500000,"CONFIG_RANGE","Encoder age limit must be <=500ms");
    require(u64(c.at("max_skew_us"),"max_skew_us")>0&&u64(c.at("max_skew_us"),"max_skew_us")<=u64(c.at("max_age_us"),"max_age_us"),"CONFIG_RANGE","Invalid asynchronous encoder skew limit");
    require(calibrated_number(f.at("speed_mm_s"))>0&&calibrated_number(f.at("speed_mm_s"))<=20&&calibrated_number(f.at("acceleration_mm_s2"))>0&&calibrated_number(f.at("acceleration_mm_s2"))<=20,"CONFIG_RANGE","First-test speed and acceleration ceilings are 20");
    require(u64(f.at("pulse_interval_us"),"pulse_interval_us")>=63&&u64(f.at("segment_guard_us"),"segment_guard_us")>=32,"CONFIG_RANGE","MOTOR3125 pulse/edge guards cannot be relaxed");
    require(calibrated_number(f.at("max_sample_distance_mm"))<=0.05&&calibrated_number(f.at("max_joint_step_deg"))<=0.1,"CONFIG_RANGE","Production path sampling too coarse");
    require(u64(f.at("max_samples"),"max_samples")<=50000,"RESOURCE_LIMIT","Production plan memory budget is at most 50000 samples");
    require(f.contains("xy_envelope"),"CONFIG_RANGE","Measured nonrectangular XY envelope and clearance required");
    auto h=calibration_home(p);auto fixture=f;auto hp=h.at("xyz_mm");
    // Workspace is stored in machine coordinates, home is the display origin.
    fixture["workspace"]["min"]=translated(f.at("workspace").at("min"),hp,1);
    fixture["workspace"]["max"]=translated(f.at("workspace").at("max"),hp,1);
    for(int a=0;a<2;a++)fixture["xy_envelope"]["center_mm"][a]=calibrated_number(f.at("xy_envelope").at("center_mm")[a])+double(hp[a]);
    for(auto &b:fixture["forbidden_boxes"]){b["min"]=translated(b.at("min"),hp,1);b["max"]=translated(b.at("max"),hp,1);}
    (void)plan({{"op","plan"},{"fixture",fixture},{"golden",p.at("golden")},{"start",{{"valid",false}}},{"points",Json::array({{{"xyz_mm",hp}}})}});
}
inline Json mapped_steps(const Json &golden_steps,const Json &p,const Json &home_steps=Json()){
    auto home=home_steps.is_null()?calibration_home(p).at("steps"):home_steps;auto signs=calibrated_vec(p.at("calibration").at("pl_sign"));Json out=Json::array();
    for(int a=0;a<3;a++)out.push_back(std::to_string(int64_t(signs[a])*(i64(golden_steps[a],"steps")-i64(home[a],"home.steps"))));
    out.push_back("0");return out;
}
// Only measured 0x30 rows with their original generation/revision can establish
// pose. The caller additionally binds this to an explicit HOME verification.
inline Json calibrated_pose(const Json &publication,const Json &p,uint64_t now){
    const auto &command=publication.at("command_position"),&f=publication.at("driver_feedback"),&c=p.at("calibration");
    require(command.at("valid")==true,"POSITION_UNKNOWN","HOME referenced command position unavailable");
    auto observed=u64(f.at("observed_monotonic_us"),"observation"),limit=u64(c.at("max_age_us"),"max_age_us");
    require(now>=observed&&now-observed<=limit,"STALE_INPUT","Feedback observation stale");
    auto home=calibrated_vec(c.at("home_joint_deg")),scale=calibrated_vec(c.at("encoder_units_per_joint_deg"));
    std::array<double,3> q{};std::array<bool,3> seen{};uint64_t earliest=UINT64_MAX,latest=0;Json identity=Json::array();
    for(const auto &row:f.at("rows"))if(row.at("slot")==0){
        int a=row.at("axis");require(a>=0&&a<3&&!seen[a],"FEEDBACK_IDENTITY","Duplicate encoder axis");seen[a]=true;
        require(row.at("valid")==true&&row.at("stale")==false&&row.at("valid_generation")==f.at("collector_generation")&&row.at("valid_revision")==f.at("revision"),"STALE_INPUT","Encoder row invalid or identity stale");
        require(u64(row.at("age_us"),"age_us")+now-observed<=limit,"STALE_INPUT","Encoder source age exceeds calibrated limit");
        const auto &v=row.at("last_valid");require(v.at("query")==0x30&&v.at("address")==0xe0+a&&v.at("data_valid")==true,"FEEDBACK_IDENTITY","0x30 axis/address mismatch");
        q[a]=home[a]+(encoder_units(v.at("value"))-encoder_units(c.at("encoder_home")[a]))/scale[a];
        auto event=u64(v.at("event_us"),"event_us");earliest=std::min(earliest,event);latest=std::max(latest,event);identity.push_back({{"axis",a},{"event_us",v.at("event_us")},{"sequence",v.at("sequence")}});
    }
    require(seen[0]&&seen[1]&&seen[2]&&latest-earliest<=u64(c.at("max_skew_us"),"max_skew_us"),"STALE_INPUT","Missing or excessively skewed asynchronous encoders");
    auto pose=forward_kinematics({{"op","fk"},{"joint_deg",q},{"golden",p.at("golden")}}),h=calibration_home(p);auto predicted=mapped_steps(pose.at("steps"),p);
    double tolerance=calibrated_number(c.at("tracking_tolerance_deg"));
    for(int a=0;a<3;a++){auto actual=i64(command.at("steps")[a],"steps");require(actual>=INT32_MIN&&actual<=INT32_MAX,"POSITION_MISMATCH","Command counter outside calibrated mechanical domain");require(std::abs(actual-i64(predicted[a],"predicted"))<=std::ceil(tolerance*40)+1,"POSITION_MISMATCH","Encoder and HOME command mapping disagree");}
    pose["golden_xyz_mm"]=pose.at("xyz_mm");pose["golden_steps"]=pose.at("steps");pose["xyz_mm"]=translated(pose.at("xyz_mm"),h.at("xyz_mm"),-1);
    pose["steps"]=command.at("steps");if(pose["steps"].size()==3)pose["steps"].push_back("0");pose["source"]="encoder_0x30_calibrated_fk";pose["source_rows"]=identity;pose["asynchronous"]=true;pose["collector_generation"]=f.at("collector_generation");pose["revision"]=f.at("revision");return pose;
}
inline Json calibrated_plan(const Json &p,const Json &start,const Json &points,const Json &work_origin){
    validate_calibration(p);auto h=calibration_home(p);auto f=p.at("fixture"),converted=points,begin=start;
    f["workspace"]["min"]=translated(f.at("workspace").at("min"),h.at("xyz_mm"),1);f["workspace"]["max"]=translated(f.at("workspace").at("max"),h.at("xyz_mm"),1);
    for(int a=0;a<2;a++)f["xy_envelope"]["center_mm"][a]=calibrated_number(f.at("xy_envelope").at("center_mm")[a])+double(h.at("xyz_mm")[a]);
    for(auto &b:f["forbidden_boxes"]){b["min"]=translated(b.at("min"),h.at("xyz_mm"),1);b["max"]=translated(b.at("max"),h.at("xyz_mm"),1);}
    for(auto &point:converted)point["xyz_mm"]=translated(translated(point.at("xyz_mm"),work_origin,1),h.at("xyz_mm"),1);
    if(begin.at("valid")==true){for(int a=0;a<3;a++)require(i64(start.at("steps")[a],"steps")>=INT32_MIN&&i64(start.at("steps")[a],"steps")<=INT32_MAX,"POSITION_MISMATCH","Start counter outside calibrated domain");begin["xyz_mm"]=translated(begin.at("xyz_mm"),h.at("xyz_mm"),1);begin["steps"]=kinematics({{"op","ik"},{"xyz_mm",begin.at("xyz_mm")},{"golden",p.at("golden")}}).at("steps");}
    auto result=plan({{"op","plan"},{"fixture",f},{"golden",p.at("golden")},{"start",begin},{"points",converted}});
    auto map_pose=[&](Json &v){v["golden_xyz_mm"]=v.at("xyz_mm");v["machine_xyz_mm"]=translated(v.at("xyz_mm"),h.at("xyz_mm"),-1);v["xyz_mm"]=translated(v.at("machine_xyz_mm"),work_origin,-1);v["golden_steps"]=v.at("steps");v["steps"]=mapped_steps(v.at("steps"),p,h.at("steps"));};
    map_pose(result["target"]);Json prev=start.at("steps");
    for(auto &s:result["samples"]){require(double(s.at("xyz_mm")[2])<0,"WORKSPACE_RANGE","Path crosses forbidden Golden Z plane");map_pose(s);
        uint64_t demand=0;for(int a=0;a<3;a++)demand=std::max(demand,uint64_t(std::abs(i64(s.at("steps")[a],"steps")-i64(prev[a],"start.steps"))));
        require(!demand||u64(s.at("duration_us"),"duration")>=u64(f.at("segment_guard_us"),"guard")+demand*u64(f.at("pulse_interval_us"),"pulse"),"PULSE_RATE","Mapped first/remaining segment exceeds pulse budget");prev=s.at("steps");}
    if(result.contains("legs"))for(auto &leg:result["legs"])for(const char *key:{"from_mm","to_mm"})leg[key]=translated(translated(leg.at(key),h.at("xyz_mm"),-1),work_origin,-1);
    result["scope"]="calibrated_machine";return result;
}
// Fifty milliseconds of spatially sampled manual intent. The browser never
// supplies STEP timing. All poses remain machine coordinates in this helper.
inline Json calibrated_jog_chunk(const Json &p,const Json &start,int axis,int sign,double speed,double &velocity){
    const auto &f=p.at("fixture");double acc=calibrated_number(f.at("acceleration_mm_s2"));
    require(axis>=0&&axis<3&&(sign==1||sign==-1)&&speed>0&&speed<=20&&speed<=calibrated_number(f.at("speed_mm_s"))&&acc>0&&acc<=20,"CONFIG_RANGE","Jog speed/acceleration invalid");
    auto home=calibration_home(p),previous=start;Json samples=Json::array();
    const auto lo=calibrated_vec(f.at("workspace").at("min")),hi=calibrated_vec(f.at("workspace").at("max")),jl=calibrated_vec(f.at("joint_min_deg")),jh=calibrated_vec(f.at("joint_max_deg"));
    for(int n=0;n<20;n++){
        auto from=calibrated_vec(previous.at("xyz_mm")),to=from;double next_velocity=std::min(speed,velocity+acc*.0025);to[axis]+=sign*(velocity+next_velocity)*.00125;
        require(std::abs(to[axis]-from[axis])<=calibrated_number(f.at("max_sample_distance_mm"))+1e-12,"SAMPLING_LIMIT","Jog spatial spacing exceeds configured bound");
        for(const auto &box:f.at("forbidden_boxes")){auto low=calibrated_vec(box.at("min")),high=calibrated_vec(box.at("max"));double enter=0,leave=1;bool hit=true;
            for(int a=0;a<3;a++){double delta=to[a]-from[a];if(!delta){if(from[a]<low[a]||from[a]>high[a])hit=false;}else{double x=(low[a]-from[a])/delta,y=(high[a]-from[a])/delta;if(x>y)std::swap(x,y);enter=std::max(enter,x);leave=std::min(leave,y);}}
            require(!hit||enter>leave,"PATH_FORBIDDEN","Jog intersects machine forbidden region");}
        Json target;
        for(double fraction:{0.0,0.5,1.0}){
            std::array<double,3> point{};for(int a=0;a<3;a++){point[a]=from[a]+fraction*(to[a]-from[a]);require(point[a]>=lo[a]&&point[a]<=hi[a],"WORKSPACE_RANGE","Jog outside machine workspace");}
            const auto &e=f.at("xy_envelope");double radial=0;for(int a=0;a<2;a++){double radius=calibrated_number(e.at("radii_mm")[a])-calibrated_number(e.at("margin_mm"));double v=(point[a]-calibrated_number(e.at("center_mm")[a]))/radius;radial+=v*v;}require(radial<=1,"WORKSPACE_RANGE","Jog outside measured XY envelope");
            auto xyz=translated(point,home.at("xyz_mm"),1);require(double(xyz[2])<0,"WORKSPACE_RANGE","Jog outside negative Golden Z branch");
            auto pose=kinematics({{"op","ik"},{"xyz_mm",xyz},{"golden",p.at("golden")}});
            for(int a=0;a<3;a++){double q=pose.at("joint_deg")[a];require(q>=jl[a]&&q<=jh[a],"JOINT_RANGE","Jog outside software joint boundary");require(std::abs(q-double(previous.at("joint_deg")[a]))<=calibrated_number(f.at("max_joint_step_deg")),"PATH_DISCONTINUITY","Jog joint discontinuity");}
            pose["xyz_mm"]=point;pose["steps"]=mapped_steps(pose.at("steps"),p,home.at("steps"));target=std::move(pose);
        }
        uint64_t demand=0;for(int a=0;a<3;a++)demand=std::max(demand,uint64_t(std::abs(i64(target.at("steps")[a],"steps")-i64(previous.at("steps")[a],"steps"))));
        require(!demand||2500>=u64(f.at("segment_guard_us"),"guard")+demand*u64(f.at("pulse_interval_us"),"pulse"),"PULSE_RATE","Jog pulse demand exceeds interval");
        samples.push_back({{"duration_us","2500"},{"steps",target.at("steps")},{"machine_xyz_mm",target.at("xyz_mm")}});previous=std::move(target);velocity=next_velocity;
    }
    return {{"samples",samples},{"last_pose",previous},{"duration_us","50000"}};
}
}
