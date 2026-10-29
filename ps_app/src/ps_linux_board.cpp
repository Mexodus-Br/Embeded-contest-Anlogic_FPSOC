#include "ps_hardware_port.hpp"
#include "ps_runtime.hpp"
#include "ps_home_calibration.hpp"
#ifndef _WIN32
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <cerrno>
#include <cstring>
#include <chrono>
#include <thread>
#include <algorithm>
#include <deque>
#include "ps_feedback_cache.hpp"
#include "../../integration/home_calibration_20261027/software/telemetry/rs485_uapi.h"
#include "../../bsp/safety_execution/execution_uapi.h"
#include "../../integration/controlled_v1_20261021/safety/generated/interlock_defs.h"
#include "../../integration/controlled_v1_20261021/safety/generated/safety_defs.h"
#include "../../bsp/motion/motion_uapi.h"
#include "../../bsp/motion/generated/interface_defs.h"
#define P(x) PLI_MOTION_GP_MOTION_V1_##x
namespace ps {
static_assert(sizeof(saf2_snapshot)==464,"Diagnostic ABI must remain unchanged");
static_assert(sizeof(saf2_owner)==16&&sizeof(saf2_action)==16,"Execution ABI size");
static_assert(sizeof(motion_command)==64&&sizeof(motion_packet)==56&&sizeof(motion_snapshot)==280,"Motion ABI size");
static_assert(sizeof(struct rs485_snapshot)==2056&&sizeof(rs485_config)==56&&sizeof(rs485_run)==16,"RS485 ABI size");
class LinuxBoard final:public BoardDevice {
    int safety_=-1,motion_=-1,feedback_=-1;uint32_t txn_=0;
    uint64_t last_feedback_=0;Json feedback_copy_=nullptr;
    mutable std::mutex feedback_mutex_;std::thread observer_;std::atomic<bool> quit_{false},history_active_{false};
    Json history_copy_=nullptr;
    void call(int fd,unsigned long op,void *arg=nullptr){if(ioctl(fd,op,arg)<0)throw Error("BSP_IO",std::string("typed ioctl failed: ")+std::strerror(errno));}
    static uint64_t pair(const __u32 *w){return uint64_t(w[1])<<32|w[0];}
    void observe_feedback(){
        std::deque<Json> history;uint64_t retired=0,missing=0,last_serial=0;std::string stream_identity,error;uint64_t last_snapshot=0,last_publish=0;
        while(!quit_){auto now=monotonic_us();try{
            if(!last_snapshot||now-last_snapshot>=100000){struct rs485_snapshot f{};call(feedback_,RS485_SNAPSHOT,&f);auto snapshot=feedback_cache(f.word,f.id,now);{std::lock_guard<std::mutex> l(feedback_mutex_);feedback_copy_=std::move(snapshot);}last_snapshot=now;}
            if(history_active_){
                std::vector<uint8_t> bytes(64*32);rs485_packet p{};p.data=reinterpret_cast<uintptr_t>(bytes.data());
                int ret=ioctl(feedback_,RS485_RX,&p);
                if(ret<0&&errno!=EAGAIN)throw Error("TELEMETRY_DMA",std::string("HP1 receive failed: ")+std::strerror(errno));
                if(!ret){
                    require(p.bytes==p.records*64&&p.bytes<=bytes.size(),"TELEMETRY_FORMAT","Invalid bounded DMA record count");
                    std::vector<Json> decoded;decoded.reserve(p.records);
                    for(unsigned r=0;r<p.records;r++){std::string hex;hex.reserve(128);const char *digits="0123456789abcdef";for(unsigned n=0;n<64;n++){auto b=bytes[r*64+n];hex+=digits[b>>4];hex+=digits[b&15];}
                        auto row=telemetry_decode({{"op","telemetry_decode"},{"hex",hex},{"byte_order","little_endian_bytes"}});row["observed_monotonic_us"]=std::to_string(now);decoded.push_back(std::move(row));}
                    // Only exact successful DMA, frame CRC and COMPLETE retire the buffer.
                    call(feedback_,RS485_COMPLETE,&p);
                    for(auto &row:decoded){auto key=row.at("collector_generation").get<std::string>()+"/"+row.at("transport_generation").get<std::string>();auto serial=u64(row.at("completion_serial"),"serial");
                        if(key==stream_identity&&last_serial&&serial>last_serial+1)missing+=serial-last_serial-1;
                        if(key==stream_identity&&last_serial&&serial<=last_serial)throw Error("TELEMETRY_ORDER","Non-monotonic raw history serial");
                        stream_identity=key;last_serial=serial;history.push_back(std::move(row));if(history.size()>512){history.pop_front();++retired;}}
                }
                error.clear();
            }
        }catch(const std::exception &e){error=e.what();history_active_=false;/* Never recover or reuse an uncertain buffer automatically. */}
            rs485_state state{};bool known=ioctl(feedback_,RS485_STATE,&state)==0;
            if(!last_publish||now-last_publish>=250000){Json rows=Json::array();for(const auto &r:history)rows.push_back(r);
                std::lock_guard<std::mutex> l(feedback_mutex_);history_copy_={{"source","hp1_ddr_raw64"},{"enabled",history_active_.load()},{"history",std::move(rows)},{"history_complete",false},{"retained_from_start",retired==0&&missing==0&&error.empty()},{"retired_records",std::to_string(retired)},{"missing_serials",std::to_string(missing)},{"error",error},{"state_known",known},{"quarantine",known?Json(bool(state.quarantine)):Json()},{"dma_owned",known?Json(bool(state.owned)):Json()},{"observed_monotonic_us",std::to_string(now)}};last_publish=now;}
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
public:
    LinuxBoard(){safety_=::open("/dev/bsp-saf2-exec",O_RDWR|O_CLOEXEC);require(safety_>=0,"BSP_OPEN","Cannot open controlled safety device");
        motion_=::open("/dev/bsp-motion",O_RDWR|O_CLOEXEC);if(motion_<0){::close(safety_);throw Error("BSP_OPEN","Cannot open controlled motion device");}
        feedback_=::open("/dev/bsp-rs485",O_RDWR|O_CLOEXEC);if(feedback_<0){::close(motion_);::close(safety_);throw Error("BSP_OPEN","Cannot open unique RS485 cache owner");}observer_=std::thread([this]{observe_feedback();});}
    ~LinuxBoard(){quit_=true;observer_.join();if(feedback_>=0)::close(feedback_);if(motion_>=0)::close(motion_);if(safety_>=0)::close(safety_);}
    BoardState read()override{
        saf2_snapshot s{};motion_snapshot m{};call(safety_,SAF2_SNAPSHOT,&s);call(motion_,MOTION_SNAPSHOT,&m);
        require(s.profile==SI_PROFILE&&s.version==SI_VERSION&&s.caps==SI_CAPS&&s.features==SI_FEATURES,"PROFILE","SAF2 required");
        BoardState b;auto status=s.interlock[SI_SNAP_STATUS];auto *w=m.words;
        b.calibration_only=!HC_NORMAL_MOTION_APPROVED;b.home_capable=home_config_matches(s.config_id,s.config_valid!=0);
        b.home_start_us=pair(s.global+SAF_SNAPSHOT_HOME_START_LO);b.home_done_us=pair(s.global+SAF_SNAPSHOT_HOME_DONE_LO);
        b.home_active=s.global[SAF_SNAPSHOT_STATE]>=SAF_STATES_PRE&&s.global[SAF_SNAPSHOT_STATE]<=SAF_STATES_FINISH;
        b.owner=pair(s.interlock+SI_SNAP_OWNER_LO);b.owner_active=status&SI_STATUS_OWNER_ACTIVE;b.heartbeat=status&SI_STATUS_HEARTBEAT_QUALIFIED;
        b.qualified=(status&(SI_STATUS_PERMIT|SI_STATUS_HEARTBEAT_QUALIFIED|SI_STATUS_FEEDBACK_QUALIFIED))==(SI_STATUS_PERMIT|SI_STATUS_HEARTBEAT_QUALIFIED|SI_STATUS_FEEDBACK_QUALIFIED);
        b.ready=s.global[SAF_SNAPSHOT_STATE]==SAF_STATES_READY;b.fault=s.global[SAF_SNAPSHOT_CAUSES]||w[P(SNAP_WORD_ERROR)];
        b.session=pair(w+P(SNAP_WORD_SESSION_LO));b.generation=m.generation;
        b.accepted=w[P(SNAP_WORD_ACCEPT_SEQ)];b.done=w[P(SNAP_WORD_DONE_SEQ)];b.end_count=w[P(SNAP_WORD_END_COUNT)];b.buffered=w[P(SNAP_WORD_BUFFERED)];
        b.accepted_valid=w[P(SNAP_WORD_VALIDITY)]&P(SNAP_VALIDITY_ACCEPT_VALID_MASK);b.done_valid=w[P(SNAP_WORD_VALIDITY)]&P(SNAP_VALIDITY_DONE_VALID_MASK);
        // Ordinary STOP preserves EN. SAF2 DRAINED additionally requires EN off
        // and belongs to configuration/owner-close admission, not STOP proof.
        // Pulse safety and DMA ownership are checked independently by the owner.
        b.stopped=w[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_STOP_COMPLETE_MASK);
        b.pulse_safe=s.global[SAF_SNAPSHOT_PULSE_SAFE]!=0;b.quarantine=m.quarantined;b.dma_owned=m.dma_owned;
        b.position_valid=(s.global[SAF_SNAPSHOT_VALID]&7)==7;b.pl_time_us=pair(s.global+SAF_SNAPSHOT_TIME_LO);
        for(unsigned i=0;i<3;i++){b.position[i]=int64_t(pair(s.global+SAF_SNAPSHOT_POSITION_0+i*2));b.pulses[i]=pair(s.global+SAF_SNAPSHOT_PULSES_0+i*2);}
        auto now=uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());
        {std::lock_guard<std::mutex> l(feedback_mutex_);b.driver_feedback=feedback_copy_;}
        b.raw={{"global",std::vector<__u32>(s.global,s.global+64)},{"interlock",std::vector<__u32>(s.interlock,s.interlock+32)},{"motion",std::vector<__u32>(w,w+64)},{"config_id",std::vector<__u32>(s.config_id,s.config_id+8)},{"snapshot_ids",{s.global_id,s.interlock_id,m.id}}};return b;
    }
    uint64_t safety(SafetyAction a,uint64_t owner)override{
        saf2_owner o{owner,0};saf2_action c{};
        switch(a){
        case SafetyAction::disable:{motion_command c{};c.opcode=PLI_CMD_DISABLE;c.axis_mask=7;c.timeout_ms=100;call(motion_,MOTION_COMMAND,&c);require(!c.ack_error,"PL_REJECTED","DISABLE rejected");break;}
        case SafetyAction::configure:{saf2_snapshot s{};call(safety_,SAF2_SNAPSHOT,&s);require(s.config_accepted!=UINT32_MAX,"EXHAUSTED","Safety config transaction exhausted");
            saf2_config cfg{};cfg.txn=s.config_accepted+1;cfg.axes=7;cfg.feedback_us=2000000;cfg.watchdog_us=2000000;call(safety_,SAF2_CONFIG,&cfg);break;}
        case SafetyAction::feedback_on:{rs485_config cfg{};const uint32_t periods[5]={125000,500000,125000,1000000,1000000};
            std::copy(periods,periods+5,cfg.periods);cfg.mask=31;cfg.run=1;
            if(HC_NORMAL_MOTION_APPROVED&&!history_active_)call(feedback_,RS485_RECOVER);
            call(feedback_,RS485_CONFIG,&cfg);if(HC_NORMAL_MOTION_APPROVED)history_active_=true;break;}
        case SafetyAction::feedback_off:{rs485_run r{};call(feedback_,RS485_RUN,&r);break;}
        case SafetyAction::open:call(safety_,SAF2_OWNER_OPEN,&o);return o.id;
        case SafetyAction::close:call(safety_,SAF2_OWNER_CLOSE,&o);break;
        case SafetyAction::recover:call(motion_,MOTION_RECOVER);break;
        case SafetyAction::clear:case SafetyAction::home:
            if(a==SafetyAction::home){saf2_snapshot s{};call(safety_,SAF2_SNAPSHOT,&s);require(home_config_matches(s.config_id,s.config_valid!=0),"PRODUCTION_HOME_UNAPPROVED","HOME calibration config changed before submission");}
            call(safety_,SAF2_ACK,&c);txn_=std::max(txn_,c.ack_id);require(txn_!=UINT32_MAX,"EXHAUSTED","Safety transaction exhausted");c.txn=++txn_;
            call(safety_,a==SafetyAction::home?SAF2_HOME:SAF2_CLEAR,&c);
            {auto until=std::chrono::steady_clock::now()+std::chrono::milliseconds(100);do{
                call(safety_,SAF2_ACK,&c);
                if(c.ack_id==txn_&&(c.ack_status&1)){require((c.ack_status&2)&&!c.ack_error,"PL_REJECTED","Safety command rejected");return 0;}
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }while(std::chrono::steady_clock::now()<until);throw Error("TIMEOUT","Safety acceptance unknown");}
            break;
        }return 0;
    }
    void feed(uint64_t owner,uint64_t sequence)override{saf2_owner o{owner,sequence};call(safety_,SAF2_OWNER_FEED,&o);}
    void ordinary_qualified(){
        require(HC_NORMAL_MOTION_APPROVED,"CALIBRATION_ONLY","This build does not authorize ordinary motion");
        saf2_snapshot s{};call(safety_,SAF2_SNAPSHOT,&s);auto status=s.interlock[SI_SNAP_STATUS];
        require(home_config_matches(s.config_id,s.config_valid!=0),"PROFILE","Full-function PL/software configuration mismatch");
        require(s.global[SAF_SNAPSHOT_STATE]==SAF_STATES_READY&&(s.global[SAF_SNAPSHOT_VALID]&7)==7&&!s.global[SAF_SNAPSHOT_CAUSES]&&
            (status&(SI_STATUS_PERMIT|SI_STATUS_HEARTBEAT_QUALIFIED|SI_STATUS_FEEDBACK_QUALIFIED|SI_STATUS_OWNER_ACTIVE))==(SI_STATUS_PERMIT|SI_STATUS_HEARTBEAT_QUALIFIED|SI_STATUS_FEEDBACK_QUALIFIED|SI_STATUS_OWNER_ACTIVE),"QUALIFICATION_MISSING","HOME, safety, feedback and live owner required");
    }
    uint64_t motion(uint32_t opcode)override{
        require(opcode==PLI_CMD_ENABLE||opcode==PLI_CMD_OPEN_SESSION||opcode==PLI_CMD_START,"FORMAT","Only execution operations allowed");ordinary_qualified();
        motion_command c{};c.opcode=opcode;c.axis_mask=7;c.timeout_ms=100;call(motion_,MOTION_COMMAND,&c);
        require(!c.ack_error&&(c.ack_status&2),"PL_REJECTED","Motion command rejected");return c.session;
    }
    void packet(const std::vector<uint8_t> &bytes)override{
        ordinary_qualified();
        require(!bytes.empty()&&bytes.size()%72==0&&bytes.size()/72<=910,"FORMAT","MOT2 packet size");motion_packet p{};p.data=reinterpret_cast<uintptr_t>(bytes.data());p.count=bytes.size()/72;p.timeout_ms=100;call(motion_,MOTION_PACKET,&p);require(!p.result,"DMA_FAILURE","Packet transport failed");
    }
    void stop()override{
        // Both paths attempted even if one ioctl fails; neither waits on the producer.
        int a=ioctl(safety_,SAF2_STOP),b=ioctl(motion_,MOTION_STOP);require(a==0&&b==0,"STOP_FAILED","Safety or motion STOP write failed");
    }
    Json history()const override{std::lock_guard<std::mutex> l(feedback_mutex_);return history_copy_;}
};
std::shared_ptr<BoardDevice> linux_board(){return std::make_shared<LinuxBoard>();}
}
#else
namespace ps {std::shared_ptr<BoardDevice> linux_board(){throw Error("BACKEND_UNAVAILABLE","Linux typed BSP devices required; no fallback to simulation");}}
#endif
