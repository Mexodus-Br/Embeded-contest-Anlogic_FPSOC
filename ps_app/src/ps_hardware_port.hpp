#pragma once
#include "ps_backend.hpp"
#include <array>
#include <atomic>
#include <mutex>
#include <thread>
#include <vector>
#include <set>
namespace ps {
struct BoardState {
    uint64_t owner=0,session=0,pl_time_us=0;
    uint32_t generation=0,accepted=0,done=0,end_count=0,buffered=0;
    bool owner_active=false,heartbeat=false,qualified=false,ready=false;
    bool accepted_valid=false,done_valid=false,stopped=false,pulse_safe=false;
    bool fault=false,quarantine=false,dma_owned=false;
    std::array<int64_t,3> position{};
    std::array<uint64_t,3> pulses{};
    bool position_valid=false;
    Json raw=nullptr;
};
enum class SafetyAction {open,close,clear,home,recover};
// Typed BSP seam; no physical address or arbitrary MMIO API.
class BoardDevice {
public:
    virtual ~BoardDevice()=default;
    virtual BoardState read()=0;
    virtual uint64_t safety(SafetyAction,uint64_t owner)=0;
    virtual void feed(uint64_t owner,uint64_t sequence)=0;
    virtual uint64_t motion(uint32_t opcode)=0;
    // Success means IOC AND packet closed, never motion completion.
    virtual void packet(const std::vector<uint8_t>&)=0;
    virtual void stop()=0; // independent of command/packet locks
};
std::shared_ptr<BoardDevice> linux_board();
// Web and serial adapters share this backend and the same device owner.
class HardwareBackend final:public ExecutionBackend {
    std::shared_ptr<BoardDevice> device_;
    std::string boot_;
    mutable std::mutex mutex_;
    std::shared_ptr<const PlannedTask> pending_;
    ExecutionBinding pending_binding_;
    std::set<std::string> used_commands_;
    std::string position_id_,command_id_,parameter_revision_;
    uint64_t position_revision_=0;
    std::atomic<bool> quit_{false};
    std::atomic<uint64_t> cancel_{0},lease_{0},stop_write_result_{0};
    std::thread worker_;
    BoardState board_;
    Json publication_=nullptr;
    std::string phase_="unknown",error_;
    uint64_t owner_=0,observed_cancel_=0,iteration_=0;
    bool completion_=false,stop_result_=false,stop_ok_=false;
    std::vector<SafetyAction> actions_;
    void run();
public:
    HardwareBackend(std::shared_ptr<BoardDevice>,std::string boot);
    ~HardwareBackend();
    void submit(std::shared_ptr<const PlannedTask>,uint64_t,const ExecutionBinding &binding={})override;
    void manual_target(const ManualSegment&)override;
    void request_stop(uint64_t)override;
    BackendUpdate poll(uint64_t)override;
    Json status()const override;
    bool simulation()const override{return false;}
    Json telemetry()const override;
    void action(const std::string&)override;
};
}
