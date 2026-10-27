#include "ps_hardware_port.hpp"
#include "ps_runtime.hpp"
#include "ps_home_calibration.hpp"
#include "ps_feedback_cache.hpp"
#include <cassert>
#include <chrono>
#include <functional>
#include <iostream>
using namespace ps;
static void check(bool v,const char *what){if(!v)throw std::runtime_error(what);}
struct FakeBoard final:BoardDevice {
    std::mutex lock;BoardState s;std::atomic<unsigned> opens{0},feeds{0},packets{0},starts{0},stops{0};uint64_t last_seq=0;
    bool reject=false,stop_fail=false,packet_fail=false,hold_packet=false,stop_stuck=false;
    FakeBoard(){s.ready=true;s.position_valid=true;s.pulse_safe=true;s.stopped=true;}
    BoardState read()override{std::lock_guard<std::mutex> l(lock);s.pl_time_us+=5000;return s;}
    uint64_t safety(SafetyAction a,uint64_t owner)override{std::lock_guard<std::mutex> l(lock);
        if(a==SafetyAction::open){check(!s.owner_active,"old owner cannot be opened");opens++;s.qualified=s.heartbeat=false;s.owner_active=true;s.owner=100+opens;last_seq=0;return s.owner;}
        check(a==SafetyAction::recover||owner==s.owner,"action owner");
        if(a==SafetyAction::close){check(s.stopped,"close idle");s.owner_active=false;}
        if(a==SafetyAction::home){s.ready=false;s.home_active=true;s.position_valid=false;s.home_start_us+=1000;}
        if(a==SafetyAction::clear)s.fault=false;
        if(a==SafetyAction::recover){check(!s.quarantine,"quarantine retained");s.dma_owned=false;++s.generation;}
        return 0;
    }
    void feed(uint64_t owner,uint64_t sequence)override{std::lock_guard<std::mutex> l(lock);check(s.owner_active&&s.owner==owner&&sequence>last_seq,"fresh heartbeat");last_seq=sequence;feeds++;s.qualified=s.heartbeat=true;}
    uint64_t motion(uint32_t op)override{std::lock_guard<std::mutex> l(lock);if(reject)throw Error("REJECTED","fake rejection");if(op==2){++s.session;s.stopped=false;s.accepted_valid=s.done_valid=false;return s.session;}if(op==4){check(!s.stopped,"START cannot revive after STOP");starts++;}return 0;}
    void packet(const std::vector<uint8_t>&b)override{
        bool hold,fail;{std::lock_guard<std::mutex> l(lock);hold=hold_packet;fail=packet_fail;s.dma_owned=true;packets++;}
        if(hold)std::this_thread::sleep_for(std::chrono::milliseconds(100));
        std::lock_guard<std::mutex> l(lock);if(fail){s.quarantine=true;throw Error("TIMEOUT","packet timeout quarantine");}
        check(b.size()%72==0&&b.size()/72<=32,"bounded packet");
        for(size_t r=0;r<b.size();r+=72){uint32_t crc=~0u;for(size_t i=0;i<68;i++){crc^=b[r+i];for(int bit=0;bit<8;bit++)crc=(crc>>1)^((crc&1)?0xedb88320u:0);}
            uint32_t stored=uint32_t(b[r+68])|uint32_t(b[r+69])<<8|uint32_t(b[r+70])<<16|uint32_t(b[r+71])<<24;
            check(~crc==stored&&b[r+22]==7&&b[r+23]==0,"independent CRC and M4 disabled");}

        if(s.stopped){s.quarantine=true;return;} // late IOC: DMA still uncertain
        auto n=b.size()-72+16;s.accepted=uint32_t(b[n])|(uint32_t(b[n+1])<<8)|(uint32_t(b[n+2])<<16)|(uint32_t(b[n+3])<<24);s.accepted_valid=true;s.dma_owned=false;
    }
    void stop()override{std::lock_guard<std::mutex> l(lock);stops++;if(stop_fail)throw Error("STOP_FAILED","fake stop failed");if(!stop_stuck){s.stopped=s.pulse_safe=true;s.position_valid=false;s.buffered=0;}if(s.dma_owned)s.quarantine=true;}
    void complete(){std::lock_guard<std::mutex> l(lock);s.done=s.accepted;s.done_valid=true;s.end_count++;}
    void mutate(const std::function<void(FakeBoard&)>&f){std::lock_guard<std::mutex> l(lock);f(*this);}
};
static std::shared_ptr<PlannedTask> plan_for(unsigned n=1,uint64_t duration=1000000){
    auto p=std::make_shared<PlannedTask>();p->parameter="approved_test_revision";p->task={{"repeat",{{"mode","finite"},{"count","1"}}}};
    Json samples=Json::array();for(unsigned i=0;i<n;i++)samples.push_back({{"duration_us",std::to_string(duration/n)},{"steps",{"1","-2","3","0"}}});
    p->first={{"samples",samples},{"duration_us",std::to_string(duration)}};return p;
}
static BackendUpdate wait_for(HardwareBackend &b,const std::function<bool(const BackendUpdate&)>&f,unsigned ms=3000){auto end=monotonic_us()+ms*1000;while(monotonic_us()<end){auto r=b.poll(monotonic_us());if(f(r))return r;std::this_thread::sleep_for(std::chrono::milliseconds(5));}throw std::runtime_error("wait timeout: "+b.status().dump());}
static void ready(HardwareBackend &b){b.poll(monotonic_us());b.action("open");wait_for(b,[&](const BackendUpdate&){return b.status().at("owner_id")!="0"&&b.telemetry().is_object();});std::this_thread::sleep_for(std::chrono::milliseconds(20));b.poll(monotonic_us());}
static void submit(HardwareBackend &b,std::shared_ptr<PlannedTask> p,uint64_t now){
    static unsigned serial=0;auto st=b.status();auto t=b.telemetry();ExecutionBinding binding;
    binding.boot_id=st.at("boot_id");binding.command_id="fake_"+std::to_string(++serial);binding.parameter_revision=p->parameter;binding.start_position_id=st.at("position_id");binding.cancel_epoch=u64(st.at("cancel_epoch"),"cancel");binding.generation=uint32_t(u64(st.at("generation"),"gen"));
    for(unsigned i=0;i<3;i++)binding.start_steps[i]=i64(t.at("command_position").at("steps")[i],"steps");
    b.submit(std::move(p),now,binding);
}
int main(int argc,char **argv){try{unsigned cases=0;
    {const uint32_t expected[8]=HC_CONFIG_WORDS;uint32_t bad[8];std::copy(expected,expected+8,bad);
     check(home_config_matches(expected,true)&&!home_config_matches(expected,false),"HOME config validity gate");
     bad[7]^=1;check(!home_config_matches(bad,true),"every config identity word checked");cases++;}
    {uint32_t w[512]={};w[RT_SNAP_GENERATION]=3;w[RT_SNAP_REVISION]=5;auto*r=w+32;r[0]=7;r[2]=3;r[3]=5;
     auto put=[](uint32_t *raw,unsigned shift,unsigned width,uint64_t value){for(unsigned n=0;n<width;n++)if((value>>n)&1)raw[(shift+n)/32]|=1u<<((shift+n)%32);};
     auto*raw=r+8;put(raw,RS_VERSION_LSB,8,1);put(raw,RS_ADDRESS_LSB,8,0xe0);put(raw,RS_QUERY_LSB,8,RS_QUERY_ENCODER);put(raw,RS_LENGTH_LSB,8,6);put(raw,0,48,UINT64_C(0xffffffff8000));
     std::copy(raw,raw+8,r+16);auto f=feedback_cache(w,7,1000);check(f.at("rows")[0].at("valid").get<bool>(),"fresh real cache identity");
     check(f.at("rows")[0].at("last_valid").at("value").at("carry")=="-1","signed encoder carry remains separate");
     r[0]|=RT_FLAG_STALE;check(feedback_cache(w,8,2000).at("rows")[0].at("stale").get<bool>(),"cache stale preserved");
     r[0]=7;r[3]=4;check(!feedback_cache(w,9,3000).at("rows")[0].at("valid").get<bool>(),"old revision not promoted");
     r[3]=5;auto d=std::make_shared<FakeBoard>();d->s.driver_feedback=feedback_cache(w,10,4000);HardwareBackend b(d,"feedback_schema");
     wait_for(b,[&](auto&){return b.telemetry().is_object();});auto t=b.telemetry();t["stale"]=false;std::cout<<t.dump()<<'\n';cases++;}
    {auto d=std::make_shared<FakeBoard>();d->s.home_capable=true;d->s.calibration_only=true;HardwareBackend b(d,"home_only");ready(b);
     bool refused=false;try{submit(b,plan_for(),monotonic_us());}catch(const Error&e){refused=e.detail.at("code")=="CALIBRATION_ONLY";}check(refused,"HOME calibration never permits ordinary plan");
     b.action("home");wait_for(b,[&](auto&){return b.status().at("phase")=="homing";});
     d->mutate([](auto&f){f.s.ready=true;f.s.home_active=false;f.s.position_valid=true;f.s.position={0,0,0};f.s.home_done_us=f.s.home_start_us+1500000;});
     wait_for(b,[&](auto&){return b.status().at("phase")=="idle";});check(b.telemetry().at("xyz_estimate").is_null(),"HOME_DONE does not calibrate XYZ");cases++;}
    {auto d=std::make_shared<FakeBoard>();d->s.home_capable=true;HardwareBackend b(d,"home_fault");ready(b);b.action("home");
     wait_for(b,[&](auto&){return b.status().at("phase")=="homing";});d->mutate([](auto&f){f.s.fault=true;});wait_for(b,[](auto&r){return r.failed;});check(d->stops>0,"HOME fault stops without waiting for watchdog");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"home_gate");bool refused=false;
     try{b.action("home");}catch(const Error&e){refused=e.detail.at("code")=="PRODUCTION_HOME_UNAPPROVED";}
     check(refused&&d->opens==0&&d->starts==0,"unapproved fixture HOME refused before device action");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot1");ready(b);submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.accepted;});
     auto r=b.poll(monotonic_us());check(!r.completed,"IOC not motion done");d->complete();wait_for(b,[](auto&r){return r.completed;});cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot2");ready(b);d->mutate([](auto&f){f.reject=true;});submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.failed;});check(b.status().at("phase")=="fault","reject fails");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot3");ready(b);submit(b,plan_for(1,1),monotonic_us());wait_for(b,[](auto&r){return r.failed;});cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot4");ready(b);d->mutate([](auto&f){f.stop_fail=true;});b.request_stop(monotonic_us());auto r=wait_for(b,[](auto&r){return r.stopped;});check(!r.pulse_safe,"failed STOP never safe");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot5");ready(b);submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.accepted;});b.request_stop(monotonic_us());wait_for(b,[](auto&r){return r.stopped;});d->complete();for(int i=0;i<30;i++){check(!b.poll(monotonic_us()).completed,"late done cannot revive");std::this_thread::sleep_for(std::chrono::milliseconds(5));}check(d->starts==1,"no restart after STOP");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot6");ready(b);d->mutate([](auto&f){f.hold_packet=true;});submit(b,plan_for(),monotonic_us());wait_for(b,[&](auto&){return d->read().dma_owned;});b.request_stop(monotonic_us());wait_for(b,[](auto&r){return r.stopped;});std::this_thread::sleep_for(std::chrono::milliseconds(120));check(d->read().quarantine,"uncertain cancel quarantines");check(d->starts==0,"late IOC no START");b.action("recover");wait_for(b,[](auto&r){return r.failed;});check(d->read().quarantine,"recovery cannot clear quarantine");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot7");ready(b);submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.accepted;});d->mutate([](auto&f){f.s.owner_active=false;});wait_for(b,[](auto&r){return r.failed;});auto before=d->feeds.load();std::this_thread::sleep_for(std::chrono::milliseconds(550));check(d->feeds==before,"lost owner no feed");cases++;}
    {auto d=std::make_shared<FakeBoard>();{HardwareBackend b(d,"oldboot");ready(b);}unsigned before=d->feeds;{HardwareBackend b(d,"newboot");for(int i=0;i<120;i++){b.poll(monotonic_us());std::this_thread::sleep_for(std::chrono::milliseconds(5));}check(d->feeds==before&&d->opens==1,"restart no adoption/open/feed");b.action("open");wait_for(b,[](auto&r){return r.failed;});check(d->opens==1,"explicit open cannot steal owner");}cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot8");ready(b);submit(b,plan_for(),monotonic_us());bool refused=false;try{submit(b,plan_for(),monotonic_us());}catch(const Error&){refused=true;}check(refused,"capacity rejection");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot9");ready(b);submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.accepted;});unsigned before=d->feeds;std::this_thread::sleep_for(std::chrono::milliseconds(650));check(d->feeds==before,"stalled critical service no heartbeat");check(b.status().at("phase")=="fault","stalled service cancels active");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot10");ready(b);d->mutate([](auto&f){f.packet_fail=true;});submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.failed;});check(d->read().quarantine,"DMA timeout quarantine");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot11");ready(b);submit(b,plan_for(),monotonic_us());wait_for(b,[](auto&r){return r.accepted;});d->mutate([](auto&f){++f.s.generation;});wait_for(b,[](auto&r){return r.failed;});cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot12");ready(b);submit(b,plan_for(65),monotonic_us());wait_for(b,[](auto&r){return r.accepted;});wait_for(b,[&](auto&){return d->read().accepted==64;});check(d->packets==3,"bounded multi-packet supply");d->complete();wait_for(b,[](auto&r){return r.completed;});cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot13");ready(b);d->mutate([](auto&f){f.stop_stuck=true;f.s.stopped=false;f.s.pulse_safe=false;});b.request_stop(monotonic_us());auto r=wait_for(b,[](auto&r){return r.stopped;});check(!r.pulse_safe,"STOP timeout fails closed");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot14");ready(b);auto p=plan_for();ExecutionBinding wrong;bool rejected=false;try{b.submit(p,monotonic_us(),wrong);}catch(const Error&){rejected=true;}check(rejected,"missing boot/start binding rejected");cases++;}
    {auto d=std::make_shared<FakeBoard>();HardwareBackend b(d,"boot15");ready(b);auto p=plan_for();p->cycle=p->first;p->task["repeat"]["count"]="2";submit(b,p,monotonic_us());wait_for(b,[](auto&r){return r.accepted;});auto initial=d->read().session;d->complete();wait_for(b,[&](auto&){auto s=d->read();return s.session>initial&&s.accepted_valid;});d->complete();auto r=wait_for(b,[](auto&r){return r.completed;});check(r.iteration==2&&d->starts==2,"finite repeat has fresh sessions");cases++;}
    if(argc==3){auto d=std::make_shared<FakeBoard>();Service s(ps_fs::u8path(argv[1]),ps_fs::u8path(argv[2]),true,true,d);auto state=s.state();check(!state.at("simulation").get<bool>()&&!state.at("simulation_injection_enabled").get<bool>(),"real source labels");
        s.handle("POST","/control",{},{{"action","acquire"}},"serial");bool refused=false;try{s.handle("POST","/simulation/inject",{},{{"kind","reference_position"}},"serial");}catch(const Error&){refused=true;}check(refused,"hardware no simulation injection");
        s.handle("POST","/hardware/action",{},{{"action","open"},{"boot_id",s.boot_id()}},"serial");std::this_thread::sleep_for(std::chrono::milliseconds(50));auto t=s.handle("GET","/telemetry",{},{},"serial");check(!t.at("simulation").get<bool>()&&t.at("xyz_estimate").is_null(),"readonly hardware telemetry unknown XYZ");
        auto reject_home=[&](Json body,const std::string &code){bool rejected=false;try{s.handle("POST","/hardware/action",{},body,"serial");}catch(const Error &e){rejected=e.detail.at("code")==code;}check(rejected,"HOME intent binding rejection");};
        Json home={{"action","home"},{"boot_id",s.boot_id()}};reject_home(home,"HOME_BINDING_REQUIRED");
        auto bs=s.state().at("backend");home["owner_id"]=bs.at("owner_id");home["cancel_epoch"]=bs.at("cancel_epoch");home["request_id"]="home_binding_test";home["deadline_monotonic_us"]=std::to_string(monotonic_us()+1500000);
        auto bad=home;bad["owner_id"]="0";reject_home(bad,"STALE_ACTION");bad=home;bad["cancel_epoch"]="999";reject_home(bad,"STALE_ACTION");bad=home;bad["deadline_monotonic_us"]="1";reject_home(bad,"EXPIRED");
        reject_home(home,"PRODUCTION_HOME_UNAPPROVED");reject_home(home,"ID_CONFLICT");
        d->mutate([](auto&f){f.s.owner_active=false;});auto end=monotonic_us()+1000000;while(s.state().at("phase")!="fault"&&monotonic_us()<end)std::this_thread::sleep_for(std::chrono::milliseconds(5));
        check(s.state().at("phase")=="fault","service observes owner loss");s.revoke_session("serial");auto acquired=s.handle("POST","/control",{},{{"action","acquire"}},"recovery_client");check(acquired.at("you_control").get<bool>(),"new controller can explicitly recover a hardware fault");
        std::cout<<s.state().dump()<<'\n'<<t.dump()<<'\n';cases++;}
    std::cout<<"PASS "<<cases<<" fake-board backend scenarios (no devices)\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
