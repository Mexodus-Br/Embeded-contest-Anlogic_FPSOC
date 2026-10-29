// Test-only BoardDevice implementation. Never linked into release binaries.
#include "ps_hardware_port.hpp"
#include "ps_runtime.hpp"
#include <deque>
#include <cmath>
namespace ps {
class FakeTimedBoard final:public BoardDevice {
    struct Point {uint32_t sequence;uint64_t duration;std::array<int64_t,3> target;bool end;};
    std::mutex mutex_;BoardState s_;std::deque<Point> points_;bool running_=false;uint64_t due_=0,home_due_=0;
    static uint64_t word(const std::vector<uint8_t> &b,size_t at,size_t n){uint64_t x=0;for(size_t i=0;i<n;i++)x|=uint64_t(b[at+i])<<(8*i);return x;}
public:
    FakeTimedBoard(){s_.pulse_safe=s_.stopped=true;s_.home_capable=true;}
    BoardState read()override{std::lock_guard<std::mutex> l(mutex_);auto now=monotonic_us();s_.pl_time_us=now;
        if(home_due_&&now>=home_due_){home_due_=0;s_.ready=s_.position_valid=true;s_.home_active=false;s_.home_done_us=now;s_.position={0,0,0};}
        if(running_){while(!points_.empty()&&now>=due_){auto p=points_.front();points_.pop_front();s_.position=p.target;s_.done=p.sequence;s_.done_valid=true;if(p.end){s_.end_count++;running_=false;s_.pulse_safe=true;break;}if(!points_.empty())due_+=points_.front().duration;}}
        s_.buffered=uint32_t(points_.size());Json rows=Json::array();for(int a=0;a<3;a++){
            double q=20+(a==1?-1:1)*double(s_.position[a])/40;int64_t units=std::llround(1000+(q-20)*819.2);int64_t carry=int64_t(std::floor(double(units)/65536));int value=int(units-carry*65536);
            rows.push_back({{"axis",a},{"slot",0},{"valid",true},{"stale",false},{"valid_generation","1"},{"valid_revision","1"},{"age_us","0"},{"last_valid",{{"query",48},{"address",224+a},{"data_valid",true},{"event_us",std::to_string(now)},{"sequence",std::to_string(now)},{"value",{{"carry",std::to_string(carry)},{"value",value}}}}}});
        }
        s_.driver_feedback={{"snapshot_id",1},{"source_time_us",std::to_string(now)},{"observed_monotonic_us",std::to_string(now)},{"collector_generation","1"},{"revision","1"},{"rows",rows}};return s_;
    }
    uint64_t safety(SafetyAction a,uint64_t)override{std::lock_guard<std::mutex> l(mutex_);
        if(a==SafetyAction::open){s_.owner=1;s_.owner_active=true;return 1;}
        if(a==SafetyAction::home){s_.home_start_us=monotonic_us();home_due_=s_.home_start_us+100000;s_.ready=s_.position_valid=false;s_.home_active=true;}
        if(a==SafetyAction::recover){s_.generation++;s_.fault=false;}
        if(a==SafetyAction::clear)s_.fault=false;
        if(a==SafetyAction::close)s_.owner_active=false;
        return 0;
    }
    void feed(uint64_t,uint64_t)override{std::lock_guard<std::mutex> l(mutex_);s_.qualified=s_.heartbeat=true;}
    uint64_t motion(uint32_t op)override{std::lock_guard<std::mutex> l(mutex_);require(s_.owner_active&&s_.qualified&&s_.ready,"FAKE_GATE","No qualification");
        if(op==2){s_.session++;s_.stopped=false;s_.accepted_valid=s_.done_valid=false;return s_.session;}
        if(op==4){require(!points_.empty(),"FAKE_GATE","No prefetched points");running_=true;s_.pulse_safe=false;due_=monotonic_us()+points_.front().duration;}return 0;
    }
    void packet(const std::vector<uint8_t> &b)override{std::lock_guard<std::mutex> l(mutex_);require(b.size()%72==0,"FAKE_PACKET","MOT2 framing");
        for(size_t at=0;at<b.size();at+=72){Point p{};require(word(b,at+8,8)==s_.session,"FAKE_PACKET","Session binding");p.sequence=uint32_t(word(b,at+16,4));p.end=word(b,at+20,2)&1;p.duration=word(b,at+24,8);for(int a=0;a<3;a++)p.target[a]=int64_t(word(b,at+32+8*a,8));points_.push_back(p);s_.accepted=p.sequence;s_.accepted_valid=true;}
    }
    void stop()override{std::lock_guard<std::mutex> l(mutex_);points_.clear();running_=false;home_due_=0;s_.home_active=false;s_.buffered=0;s_.stopped=s_.pulse_safe=true;}
};
std::shared_ptr<BoardDevice> linux_board(){return std::make_shared<FakeTimedBoard>();}
}
