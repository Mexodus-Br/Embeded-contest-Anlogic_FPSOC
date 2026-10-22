#pragma once
#include "ps_core.hpp"
#include <atomic>
#include <condition_variable>
#include <deque>
#include "ps_fs.hpp"
#include <map>
#include <mutex>
#include <thread>

namespace ps {
uint64_t monotonic_us();
std::string random_id();
bool logical_id(const std::string &s);
void atomic_save(const ps_fs::path &path,const Json &value);
Json read_json(const ps_fs::path &path);

class Logs {
    struct Snapshot {uint64_t expires;Json rows,metadata;};
    std::string boot_;
    ps_fs::path directory_;
    std::mutex mutex_,queue_mutex_;
    std::condition_variable wake_;
    std::deque<Json> queue_,history_,archive_;
    uint64_t archive_errors_=0,archive_retired_=0;
    void load_archive();
    Json in_flight_=nullptr;
    std::atomic<size_t> queue_depth_{0};
    std::map<std::string,Snapshot> snapshots_;
    std::atomic<uint64_t> serial_{0},dropped_{0},write_errors_{0},persisted_{0};
    std::atomic<bool> stop_{false},fail_disk_{false},pause_writer_{false};
    std::thread writer_;
    uint64_t retired_=0;
    void writer();
public:
    Logs(std::string boot,ps_fs::path directory);
    ~Logs();
    void emit(const std::string &event,const std::string &component="command",const std::string &level="info",Json details=Json::object(),const std::string &command="",const std::string &task="");
    Json stats();
    Json snapshot(const Json &filter);
    Json page(const std::string &id,size_t offset,size_t limit);
    Json boots();
    Json detail(const std::string &id,const std::string &boot="");
    std::string export_jsonl(const std::string &id);
    Json events_after(uint64_t id);
    void inject(bool disk,bool pause){fail_disk_=disk;pause_writer_=pause;wake_.notify_all();}
};

class Service {
    struct Impl;
    Impl *impl_;
public:
    Service(const ps_fs::path &root,const ps_fs::path &data,bool allow_simulation_injection=false);
    ~Service();
    Json handle(const std::string &method,const std::string &path,const std::map<std::string,std::string> &query,const Json &body,const std::string &session);
    Json state();
    Json stop(const std::string &session);
    void revoke_session(const std::string &session);
    std::string export_log(const std::string &id);
    Json events(uint64_t after);
    std::string boot_id() const;
};
}
