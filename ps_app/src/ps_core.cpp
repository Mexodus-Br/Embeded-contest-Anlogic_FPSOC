#include "ps_core.hpp"
#include "golden_model/src/model.hpp"
#include "pl_interface/generated/interface_defs.h"
extern "C" {
#include "pl_rs485/software/rs485_telem.h"
}
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <numeric>
#include <vector>

namespace ps {
Error::Error(std::string code,std::string message,std::string field,Json context)
    : std::runtime_error(message),detail{{"code",code},{"message",message},{"field",field.empty()?Json():Json(field)},
                                      {"leg",nullptr},{"sample",nullptr},{"details",context}} {}
void require(bool ok,const std::string &code,const std::string &message,const std::string &field) {
    if(!ok) throw Error(code,message,field);
}
template<class T> static T decimal(const Json &j,const std::string &field) {
    require(j.is_string(),"FORMAT","64-bit values must be decimal strings",field);
    auto s=j.get<std::string>();bool negative=!s.empty()&&s[0]=='-';size_t first=negative?1:0;
    require(!s.empty()&&first<s.size()&&(!negative||std::numeric_limits<T>::is_signed),"FORMAT","Invalid decimal integer",field);
    require(s[first]!='0'||(!negative&&s.size()==1),"FORMAT","Noncanonical decimal integer",field);
    const uint64_t limit=uint64_t(std::numeric_limits<T>::max())+(negative?1u:0u);uint64_t n=0;
    for(size_t i=first;i<s.size();i++){require(s[i]>='0'&&s[i]<='9',"FORMAT","Invalid decimal digit",field);auto digit=unsigned(s[i]-'0');
        require(n<=limit/10&&(n!=limit/10||digit<=limit%10),"FORMAT","Decimal integer out of range",field);n=n*10+digit;}
    return negative?T(-T(n-1)-1):T(n);
}
uint64_t u64(const Json &j,const std::string &f){return decimal<uint64_t>(j,f);}
int64_t i64(const Json &j,const std::string &f){return decimal<int64_t>(j,f);}
static double number(const Json &j,const std::string &f) {
    require(j.is_number(),"FORMAT","Expected number",f);double x=j.get<double>();
    require(std::isfinite(x),"FORMAT","Expected finite number",f);return x;
}
static void keys(const Json &j,std::initializer_list<const char*> allowed) {
    require(j.is_object(),"FORMAT","Expected object");
    for(auto it=j.begin();it!=j.end();++it) {
        bool found=false;for(auto k:allowed) found|=it.key()==k;
        require(found,"FORMAT","Unknown field",it.key());
    }
}
using Vec=std::array<double,3>;
static Vec vec(const Json &j,const std::string &f) {
    require(j.is_array()&&j.size()==3,"FORMAT","Expected XYZ/angle triple",f);Vec p{};
    for(int a=0;a<3;a++) p[a]=number(j[a],f);return p;
}
static double distance(const Vec &a,const Vec &b){double s=0;for(int i=0;i<3;i++)s+=(a[i]-b[i])*(a[i]-b[i]);return std::sqrt(s);}
static Vec mix(const Vec &a,const Vec &b,double u){Vec p{};for(int i=0;i<3;i++)p[i]=a[i]+(b[i]-a[i])*u;return p;}
static golden::Config config(const Json &j) {
    keys(j,{"base_radius_mm","effector_radius_mm","upper_length_mm","lower_length_mm","main_gear_teeth",
            "motor_gear_teeth","microsteps","steps_per_rev","angle_offset_deg","step_offset","inverse"});
    golden::Config c;
    auto f=[&](const char *name,float &value){if(j.contains(name)){double d=number(j.at(name),name);require(d>0&&d<=1e6,"CONFIG_RANGE","Invalid geometry",name);value=float(d);}};
    f("base_radius_mm",c.R);f("effector_radius_mm",c.r);f("upper_length_mm",c.L);f("lower_length_mm",c.l);
    auto d=[&](const char *name,double &v){if(j.contains(name))v=number(j.at(name),name);require(v>0&&v<=1e6,"CONFIG_RANGE","Invalid gearing",name);};
    d("main_gear_teeth",c.main_teeth);d("motor_gear_teeth",c.motor_teeth);
    auto n=[&](const char *name,int &v){if(j.contains(name)){double x=number(j.at(name),name);require(x>=1&&x<=1000000&&x==std::floor(x),"CONFIG_RANGE","Invalid integer",name);v=int(x);}};
    n("microsteps",c.microsteps);n("steps_per_rev",c.steps_per_rev);
    require(int64_t(c.microsteps)*c.steps_per_rev<=INT32_MAX,"CONFIG_RANGE","Golden factor integer overflow");
    if(j.contains("angle_offset_deg")){auto v=vec(j.at("angle_offset_deg"),"angle_offset_deg");for(int i=0;i<3;i++){require(std::abs(v[i])<=360,"CONFIG_RANGE","Angle offset out of range");c.angle_offset[i]=float(v[i]*golden::pi/180);}}
    if(j.contains("step_offset")){auto v=vec(j.at("step_offset"),"step_offset");for(int i=0;i<3;i++){require(v[i]>=INT32_MIN&&v[i]<=INT32_MAX&&v[i]==std::trunc(v[i]),"CONFIG_RANGE","Golden offset out of range");c.step_offset[i]=int(v[i]);}}
    if(j.contains("inverse")){auto v=j.at("inverse");require(v.is_array()&&v.size()==3,"FORMAT","inverse needs three booleans");for(int i=0;i<3;i++){require(v[i].is_boolean(),"FORMAT","inverse needs booleans");c.inverse[i]=v[i].get<bool>();}}
    return c;
}
static Json solve(const Vec &p,const golden::Config &c) {
    for(double x:p) require(std::abs(x)<=std::numeric_limits<float>::max(),"IK_UNREACHABLE","Input exceeds Golden float domain");
    auto ik=golden::xyz_to_angles(float(p[0]),float(p[1]),float(p[2]),c);
    if(!ik.valid)throw Error("IK_UNREACHABLE","Golden IK rejected position","xyz_mm",{{"reasons",ik.reasons}});
    auto steps=golden::angles_to_steps(ik.angles,c);
    if(!steps.valid)throw Error("STEP_RANGE","Golden reference step domain exceeded","xyz_mm",{{"reasons",steps.reasons}});
    Json angles=Json::array(),targets=Json::array();
    for(int a=0;a<3;a++){angles.push_back(double(ik.angles[a])*180/golden::pi);targets.push_back(std::to_string(steps.targets[a]));}
    targets.push_back("0");
    return {{"xyz_mm",p},{"joint_deg",angles},{"angles_rad",ik.angles},{"steps",targets},{"raw_steps",steps.unrounded},
            {"rad_to_step_factor",steps.factor},{"axis_order",{"high","low","rot","M4_disabled"}}};
}
Json kinematics(const Json &r){keys(r,{"op","xyz_mm","golden"});return solve(vec(r.at("xyz_mm"),"xyz_mm"),config(r.value("golden",Json::object())));}
static void box_valid(const Json &b){keys(b,{"min","max"});auto lo=vec(b.at("min"),"min"),hi=vec(b.at("max"),"max");for(int a=0;a<3;a++)require(lo[a]<hi[a],"CONFIG_RANGE","Box bounds are reversed");}
static bool inside(const Vec &p,const Json &b){auto lo=vec(b.at("min"),"min"),hi=vec(b.at("max"),"max");for(int a=0;a<3;a++)if(p[a]<lo[a]||p[a]>hi[a])return false;return true;}
// Slab intersection covers the entire straight segment, including narrow boxes between samples.
static bool intersects(const Vec &a,const Vec &b,const Json &box){
    auto lo=vec(box.at("min"),"min"),hi=vec(box.at("max"),"max");double enter=0,leave=1;
    for(int i=0;i<3;i++){double d=b[i]-a[i];if(d==0){if(a[i]<lo[i]||a[i]>hi[i])return false;}
        else{double p=(lo[i]-a[i])/d,q=(hi[i]-a[i])/d;if(p>q)std::swap(p,q);enter=std::max(enter,p);leave=std::min(leave,q);if(enter>leave)return false;}}
    return true;
}
Json plan(const Json &r){
    keys(r,{"op","fixture","golden","start","points"});
    auto c=config(r.value("golden",Json::object()));const auto &f=r.at("fixture");
    keys(f,{"id","speed_mm_s","acceleration_mm_s2","sample_us","max_sample_distance_mm","max_samples","workspace","forbidden_boxes",
            "joint_min_deg","joint_max_deg","max_joint_step_deg","pulse_interval_us","segment_guard_us","max_duration_us"});
    require(f.at("id").is_string()&&!f.at("id").get<std::string>().empty(),"CONFIG_RANGE","Explicit fixture ID required");
    double vmax=number(f.at("speed_mm_s"),"speed_mm_s"),acc=number(f.at("acceleration_mm_s2"),"acceleration_mm_s2"),spacing=number(f.at("max_sample_distance_mm"),"max_sample_distance_mm");
    require(vmax>0&&vmax<=10000&&acc>0&&acc<=1e6&&spacing>0&&spacing<=10,"CONFIG_RANGE","Invalid fixture speed/acceleration/spacing");
    auto sample_us=u64(f.at("sample_us"),"sample_us"),max_samples=u64(f.at("max_samples"),"max_samples"),guard=u64(f.at("segment_guard_us"),"segment_guard_us"),pulse=u64(f.at("pulse_interval_us"),"pulse_interval_us"),max_duration=u64(f.at("max_duration_us"),"max_duration_us");
    require(sample_us>=1&&sample_us<=1000000&&max_samples>=1&&max_samples<=200000&&pulse>=1&&pulse<=1000000&&guard<=1000000&&max_duration>=1&&max_duration<=3600000000ULL,"CONFIG_RANGE","Fixture resource bounds invalid");
    box_valid(f.at("workspace"));require(f.at("forbidden_boxes").is_array()&&f.at("forbidden_boxes").size()<=128,"RESOURCE_LIMIT","At most 128 forbidden boxes");for(auto &b:f.at("forbidden_boxes"))box_valid(b);
    auto jmin=vec(f.at("joint_min_deg"),"joint_min_deg"),jmax=vec(f.at("joint_max_deg"),"joint_max_deg");
    for(int a=0;a<3;a++)require(jmin[a]<jmax[a],"CONFIG_RANGE","Joint limits reversed");
    double max_joint=number(f.at("max_joint_step_deg"),"max_joint_step_deg");require(max_joint>0&&max_joint<=180,"CONFIG_RANGE","Invalid joint sampling limit");
    const auto &points=r.at("points");require(points.is_array()&&!points.empty()&&points.size()<=10000,"FORMAT","Expected 1..10000 path points");
    for(auto &p:points){keys(p,{"xyz_mm","duration_us","dwell_us"});(void)vec(p.at("xyz_mm"),"xyz_mm");}
    Json target=solve(vec(points.back().at("xyz_mm"),"xyz_mm"),c);
    require(inside(vec(target.at("xyz_mm"),"xyz_mm"),f.at("workspace")),"WORKSPACE_RANGE","Target outside fixture workspace");
    for(int a=0;a<3;a++)require(double(target.at("joint_deg")[a])>=jmin[a]&&double(target.at("joint_deg")[a])<=jmax[a],"JOINT_RANGE","Target outside fixture joint range");
    const auto &start=r.at("start");keys(start,{"valid","position_id","xyz_mm","steps"});
    require(start.at("valid").is_boolean(),"FORMAT","Start validity must be explicit");
    if(!start.at("valid").get<bool>())return {{"executable",false},{"target",target},{"samples",Json::array()},
        {"errors",Json::array({Error("POSITION_UNKNOWN","Target IK only; start position is unknown").detail})}};
    Vec from=vec(start.at("xyz_mm"),"start.xyz_mm");Json prev=solve(from,c);
    require(start.at("position_id").is_string()&&!start.at("position_id").get<std::string>().empty(),"FORMAT","Start identity required");
    require(start.at("steps")==prev.at("steps"),"START_MISMATCH","Start XYZ and reference steps disagree");
    Json samples=Json::array(),legs=Json::array();uint64_t elapsed=0;
    auto check=[&](const Vec &p,const Json &pose){require(inside(p,f.at("workspace")),"WORKSPACE_RANGE","Point outside explicit fixture workspace","xyz_mm");
        for(int a=0;a<3;a++){double q=pose.at("joint_deg")[a];require(q>=jmin[a]&&q<=jmax[a],"JOINT_RANGE","Joint outside fixture range","joint_deg");}};
    check(from,prev);
    for(size_t leg=0;leg<points.size();leg++)try{
        Vec to=vec(points[leg].at("xyz_mm"),"xyz_mm");check(to,solve(to,c));
        for(auto &b:f.at("forbidden_boxes"))require(!intersects(from,to,b),"PATH_FORBIDDEN","Straight path intersects forbidden box","xyz_mm");
        double length=distance(from,to);require(std::isfinite(length),"CONFIG_RANGE","Path length overflow");
        double minimum=length<=vmax*vmax/acc?2*std::sqrt(length/acc):length/vmax+vmax/acc;
        require(minimum*1e6<=double(max_duration),"RESOURCE_LIMIT","Path exceeds fixture duration budget");
        uint64_t ticks=std::max<uint64_t>(sample_us,uint64_t(std::ceil(minimum*1e6)));
        bool specified=points[leg].contains("duration_us")&&!points[leg].at("duration_us").is_null();
        if(specified){ticks=u64(points[leg].at("duration_us"),"duration_us");if(double(ticks)/1e6+1e-12<minimum)throw Error("DURATION_INSUFFICIENT","Requested duration violates speed/acceleration limits","duration_us",{{"minimum_us",std::to_string(uint64_t(std::ceil(minimum*1e6)))}});}
        require(ticks>0&&ticks<=max_duration&&elapsed<=max_duration-ticks,"RESOURCE_LIMIT","Duration outside fixture budget");
        double T=double(ticks)/1e6,root=std::sqrt(std::max(0.0,T*T-4*length/acc));
        double ta=length?2*length/(acc*(T+root)):0,peak=acc*ta;
        uint64_t dt=peak>0?std::min(sample_us,uint64_t(std::max(1.0,std::floor(spacing/peak*1e6)))):sample_us;
        uint64_t count=(ticks+dt-1)/dt;
        require(count<=max_samples-samples.size(),"RESOURCE_LIMIT","Path exceeds fixture sample budget");
        uint64_t last=0;Vec previous_point=from;
        for(uint64_t k=1;k<=count;k++)try{
            // Integer partition preserves exactly the caller's duration and avoids a tiny remainder segment.
            uint64_t t=ticks/count*k+(ticks%count*k)/count,duration=t-last;double seconds=double(t)/1e6;
            double travelled=seconds<ta?0.5*acc*seconds*seconds:(seconds<=T-ta?peak*(seconds-ta/2):length-0.5*acc*(T-seconds)*(T-seconds));
            double progress=length?std::clamp(travelled/length,0.0,1.0):1;Vec p=k==count?to:mix(from,to,progress);Json pose=solve(p,c);check(p,pose);
            require(distance(previous_point,p)<=spacing*(1+1e-9),"SAMPLING_LIMIT","Spatial sample interval too large");
            uint64_t demand=0;for(int a=0;a<3;a++){require(std::abs(double(pose.at("joint_deg")[a])-double(prev.at("joint_deg")[a]))<=max_joint,"PATH_DISCONTINUITY","Golden branch/joint jump exceeds fixture limit");
                auto d=i64(pose.at("steps")[a],"steps")-i64(prev.at("steps")[a],"steps");demand=std::max(demand,uint64_t(std::abs(d)));}
            if(demand&&duration<guard+demand*pulse)throw Error("PULSE_RATE","Duration cannot fit pulse and direction guards; no automatic stretching","duration_us",{{"required_us",std::to_string(guard+demand*pulse)},{"actual_us",std::to_string(duration)}});
            samples.push_back({{"sequence",samples.size()},{"leg",leg},{"duration_us",std::to_string(duration)},{"time_us",std::to_string(elapsed+t)},
                               {"xyz_mm",p},{"joint_deg",pose.at("joint_deg")},{"steps",pose.at("steps")},{"path_progress",progress},
                               {"speed_mm_s",seconds<ta?acc*seconds:(seconds<=T-ta?peak:acc*(T-seconds))},{"end",false}});
            prev=pose;previous_point=p;last=t;
        }catch(Error &e){e.detail["sample"]=k-1;throw;}
        legs.push_back({{"from_mm",from},{"to_mm",to},{"start_us",std::to_string(elapsed)},{"duration_us",std::to_string(ticks)},
                        {"acceleration_time_s",ta},{"peak_speed_mm_s",peak},{"profile",T>2*ta+1e-9?"trapezoid":"triangle"},{"specified_duration",specified}});
        elapsed+=ticks;from=to;
        uint64_t dwell=points[leg].contains("dwell_us")?u64(points[leg].at("dwell_us"),"dwell_us"):0;
        if(dwell){require(dwell<=max_duration&&elapsed<=max_duration-dwell&&samples.size()<max_samples,"RESOURCE_LIMIT","Dwell exceeds fixture budget");elapsed+=dwell;
            samples.push_back({{"sequence",samples.size()},{"leg",leg},{"duration_us",std::to_string(dwell)},{"time_us",std::to_string(elapsed)},
                {"xyz_mm",from},{"joint_deg",prev.at("joint_deg")},{"steps",prev.at("steps")},{"path_progress",1},{"speed_mm_s",0},{"end",false},{"dwell",true}});}
    }catch(Error &e){e.detail["leg"]=leg;throw;}
    samples.back()["end"]=true;
    return {{"executable",true},{"fixture_id",f.at("id")},{"scope","host_fixture_only"},{"start_position_id",start.at("position_id")},
            {"duration_us",std::to_string(elapsed)},{"target",target},{"legs",legs},{"samples",samples},{"errors",Json::array()}};
}
static std::vector<uint8_t> unhex(const Json &j,size_t size){
    require(j.is_string(),"FORMAT","Expected hex string");auto s=j.get<std::string>();require(s.size()==size*2,"FORMAT","Incorrect hex length");std::vector<uint8_t>b(size);
    auto digit=[](char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;throw Error("FORMAT","Invalid hex digit");};
    for(size_t i=0;i<size;i++)b[i]=uint8_t(digit(s[i*2])*16+digit(s[i*2+1]));return b;
}
static std::string hex(const std::vector<uint8_t>&b){const char *d="0123456789abcdef";std::string s;for(auto x:b){s+=d[x>>4];s+=d[x&15];}return s;}
Json motion_encode(const Json &r){
    keys(r,{"op","session_id","sequence","duration_us","steps","end"});
    uint64_t session=u64(r.at("session_id"),"session_id"),ticks=u64(r.at("duration_us"),"duration_us");
    double seq=number(r.at("sequence"),"sequence");require(seq>=0&&seq<=UINT32_MAX&&seq==std::floor(seq),"FORMAT","Invalid MOT2 sequence");
    require(session>0&&ticks>0&&ticks<=UINT64_MAX/PLI_MOTION_GP_MOTION_V1_CYCLES_PER_TICK,"FORMAT","MOT2 session/duration overflow");
    auto targets=r.at("steps");require(targets.is_array()&&targets.size()==4&&targets[3]=="0","FORMAT","Four targets required; M4 disabled");
    require(r.at("end").is_boolean(),"FORMAT","END must be boolean");
    std::vector<uint8_t>b(PLI_MOTION_STREAM_V2_LENGTH);auto put=[&](unsigned offset,unsigned n,uint64_t v){for(unsigned i=0;i<n;i++)b[offset+i]=uint8_t(v>>(8*i));};
#define PUT(name,value) put(PLI_MOTION_STREAM_V2_##name##_OFFSET,PLI_MOTION_STREAM_V2_##name##_SIZE,value)
    PUT(MAGIC,PLI_MOTION_STREAM_V2_MAGIC_VALUE);PUT(VERSION,PLI_MOTION_STREAM_V2_VERSION_VALUE);PUT(LENGTH,PLI_MOTION_STREAM_V2_LENGTH_VALUE);
    PUT(SESSION_ID,session);PUT(SEQUENCE,uint32_t(seq));PUT(FLAGS,r.at("end").get<bool>()?1:0);PUT(AXIS_MASK,7);PUT(DURATION_TICK,ticks);
    for(unsigned a=0;a<4;a++)put(PLI_MOTION_STREAM_V2_TARGET0_OFFSET+a*PLI_MOTION_STREAM_V2_TARGET0_SIZE,PLI_MOTION_STREAM_V2_TARGET0_SIZE,uint64_t(i64(targets[a],"steps")));
    uint32_t crc=~0u;for(unsigned i=0;i<PLI_MOTION_STREAM_V2_CRC_OFFSET;i++){crc^=b[i];for(int j=0;j<8;j++)crc=(crc>>1)^((crc&1)?PLI_MOTION_GP_MOTION_V1_CRC_REFLECTED_POLYNOMIAL:0);}PUT(CRC,~crc);
#undef PUT
    return {{"hex_le",hex(b)},{"bytes",b.size()},{"axis_mask",7}};
}
Json telemetry_decode(const Json &r){
    keys(r,{"op","hex","byte_order"});auto b=unhex(r.at("hex"),RT_RECORD_BYTES);auto order=r.value("byte_order",std::string("little_endian_bytes"));
    require(order=="little_endian_bytes"||order=="verilog_msb_hex","FORMAT","Unknown telemetry byte order");if(order=="verilog_msb_hex")std::reverse(b.begin(),b.end());
    rs485_telem_record t{};require(rs485_telem_decode(b.data(),&t)==RS485_SW_OK,"TELEMETRY_FORMAT","Telemetry header, payload format or CRC invalid");const auto &s=t.source;
    Json value=nullptr;std::string kind="unknown";
    if(s.query==0x30){kind="encoder_carry_value";if(s.data_valid)value={{"carry",std::to_string(s.encoder_carry)},{"value",s.encoder_value}};}
    else if(s.query==0x33||s.query==0x39){kind=s.query==0x33?"command_pulses":"error_counts";if(s.data_valid)value=std::to_string(s.signed_value);}
    else{kind=s.query==0x3a?"enable":"protect";if(s.data_valid)value={{"raw",s.enum_raw},{"known",bool(s.enum_known)}};}
    return {{"collector_generation",std::to_string(t.collector_generation)},{"transport_generation",std::to_string(t.transport_generation)},
            {"revision",std::to_string(t.revision)},{"completion_serial",std::to_string(t.completion_serial)},{"address",s.address},{"query",s.query},
            {"status",s.status},{"attempt",s.attempt},{"sequence",std::to_string(s.sequence)},{"request_us",std::to_string(s.request_us)},
            {"event_us",std::to_string(s.event_us)},{"payload",std::to_string(s.payload)},{"data_valid",bool(s.data_valid)},{"kind",kind},{"value",value},{"raw_hex_le",hex(b)}};
}
Json dispatch(const Json &r){auto op=r.at("op").get<std::string>();if(op=="ik")return kinematics(r);if(op=="plan")return plan(r);if(op=="motion_encode")return motion_encode(r);if(op=="telemetry_decode")return telemetry_decode(r);throw Error("FORMAT","Unknown operation","op");}
}
