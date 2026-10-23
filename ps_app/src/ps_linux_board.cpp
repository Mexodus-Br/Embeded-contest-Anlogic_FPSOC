#include "ps_hardware_port.hpp"
#ifndef _WIN32
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <cerrno>
#include <cstring>
#include <chrono>
#include <thread>
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
class LinuxBoard final:public BoardDevice {
    int safety_=-1,motion_=-1;uint32_t txn_=0;
    void call(int fd,unsigned long op,void *arg=nullptr){if(ioctl(fd,op,arg)<0)throw Error("BSP_IO",std::string("typed ioctl failed: ")+std::strerror(errno));}
    static uint64_t pair(const __u32 *w){return uint64_t(w[1])<<32|w[0];}
public:
    LinuxBoard(){safety_=::open("/dev/bsp-saf2-exec",O_RDWR|O_CLOEXEC);require(safety_>=0,"BSP_OPEN","Cannot open controlled safety device");
        motion_=::open("/dev/bsp-motion",O_RDWR|O_CLOEXEC);if(motion_<0){::close(safety_);throw Error("BSP_OPEN","Cannot open controlled motion device");}}
    ~LinuxBoard(){if(motion_>=0)::close(motion_);if(safety_>=0)::close(safety_);}
    BoardState read()override{
        saf2_snapshot s{};motion_snapshot m{};call(safety_,SAF2_SNAPSHOT,&s);call(motion_,MOTION_SNAPSHOT,&m);
        require(s.profile==SI_PROFILE&&s.version==SI_VERSION&&s.caps==SI_CAPS&&s.features==SI_FEATURES,"PROFILE","SAF2 required");
        BoardState b;auto status=s.interlock[SI_SNAP_STATUS];auto *w=m.words;
        b.owner=pair(s.interlock+SI_SNAP_OWNER_LO);b.owner_active=status&SI_STATUS_OWNER_ACTIVE;b.heartbeat=status&SI_STATUS_HEARTBEAT_QUALIFIED;
        b.qualified=(status&(SI_STATUS_PERMIT|SI_STATUS_HEARTBEAT_QUALIFIED|SI_STATUS_FEEDBACK_QUALIFIED))==(SI_STATUS_PERMIT|SI_STATUS_HEARTBEAT_QUALIFIED|SI_STATUS_FEEDBACK_QUALIFIED);
        b.ready=s.global[SAF_SNAPSHOT_STATE]==SAF_STATES_READY;b.fault=s.global[SAF_SNAPSHOT_CAUSES]||w[P(SNAP_WORD_ERROR)];
        b.session=pair(w+P(SNAP_WORD_SESSION_LO));b.generation=m.generation;
        b.accepted=w[P(SNAP_WORD_ACCEPT_SEQ)];b.done=w[P(SNAP_WORD_DONE_SEQ)];b.end_count=w[P(SNAP_WORD_END_COUNT)];b.buffered=w[P(SNAP_WORD_BUFFERED)];
        b.accepted_valid=w[P(SNAP_WORD_VALIDITY)]&P(SNAP_VALIDITY_ACCEPT_VALID_MASK);b.done_valid=w[P(SNAP_WORD_VALIDITY)]&P(SNAP_VALIDITY_DONE_VALID_MASK);
        b.stopped=(w[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_STOP_COMPLETE_MASK))&&(status&SI_STATUS_DRAINED);
        b.pulse_safe=s.global[SAF_SNAPSHOT_PULSE_SAFE]!=0;b.quarantine=m.quarantined;b.dma_owned=m.dma_owned;
        b.position_valid=(s.global[SAF_SNAPSHOT_VALID]&7)==7;b.pl_time_us=pair(s.global+SAF_SNAPSHOT_TIME_LO);
        for(unsigned i=0;i<3;i++){b.position[i]=int64_t(pair(s.global+SAF_SNAPSHOT_POSITION_0+i*2));b.pulses[i]=pair(s.global+SAF_SNAPSHOT_PULSES_0+i*2);}
        b.raw={{"global",std::vector<__u32>(s.global,s.global+64)},{"interlock",std::vector<__u32>(s.interlock,s.interlock+32)},{"motion",std::vector<__u32>(w,w+64)},{"config_id",std::vector<__u32>(s.config_id,s.config_id+8)},{"snapshot_ids",{s.global_id,s.interlock_id,m.id}}};return b;
    }
    uint64_t safety(SafetyAction a,uint64_t owner)override{
        saf2_owner o{owner,0};saf2_action c{};
        switch(a){
        case SafetyAction::open:call(safety_,SAF2_OWNER_OPEN,&o);return o.id;
        case SafetyAction::close:call(safety_,SAF2_OWNER_CLOSE,&o);break;
        case SafetyAction::recover:call(motion_,MOTION_RECOVER);break;
        case SafetyAction::clear:case SafetyAction::home:
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
    uint64_t motion(uint32_t opcode)override{motion_command c{};c.opcode=opcode;c.axis_mask=7;c.timeout_ms=100;call(motion_,MOTION_COMMAND,&c);require(!c.ack_error,"PL_REJECTED","Motion command rejected");return c.session;}
    void packet(const std::vector<uint8_t> &bytes)override{
        require(!bytes.empty()&&bytes.size()%72==0&&bytes.size()/72<=910,"FORMAT","MOT2 packet size");motion_packet p{};p.data=reinterpret_cast<uintptr_t>(bytes.data());p.count=bytes.size()/72;p.timeout_ms=100;call(motion_,MOTION_PACKET,&p);require(!p.result,"DMA_FAILURE","Packet transport failed");
    }
    void stop()override{
        // Both paths attempted even if one ioctl fails; neither waits on the producer.
        int a=ioctl(safety_,SAF2_STOP),b=ioctl(motion_,MOTION_STOP);require(a==0&&b==0,"STOP_FAILED","Safety or motion STOP write failed");
    }
};
std::shared_ptr<BoardDevice> linux_board(){return std::make_shared<LinuxBoard>();}
}
#else
namespace ps {std::shared_ptr<BoardDevice> linux_board(){throw Error("BACKEND_UNAVAILABLE","Linux typed BSP devices required; no fallback to simulation");}}
#endif
