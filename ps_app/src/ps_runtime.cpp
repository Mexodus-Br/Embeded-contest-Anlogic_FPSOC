#include "ps_runtime.hpp"
#include <algorithm>
#include <chrono>
#include <fstream>
#include <sstream>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#else
#include <fcntl.h>
#include <sys/random.h>
#include <unistd.h>
#endif

namespace ps {
uint64_t monotonic_us(){return uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());}
std::string random_id(){unsigned char bytes[16];
#ifdef _WIN32
    require(BCryptGenRandom(nullptr,bytes,sizeof(bytes),BCRYPT_USE_SYSTEM_PREFERRED_RNG)==0,"INTERNAL","System entropy unavailable");
#else
    require(getrandom(bytes,sizeof(bytes),0)==sizeof(bytes),"INTERNAL","System entropy unavailable");
#endif
    const char *h="0123456789abcdef";std::string s;for(auto b:bytes){s+=h[b>>4];s+=h[b&15];}return s;
}
bool logical_id(const std::string &s){return !s.empty()&&s.size()<=128&&std::all_of(s.begin(),s.end(),[](unsigned char c){return(c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-';});}
Json read_json(const ps_fs::path &p){std::ifstream f(p);require(bool(f),"NOT_FOUND","Stored document not found");return Json::parse(f);}
void atomic_save(const ps_fs::path &path,const Json &value){
    auto tmp=path;tmp+=ps_fs::u8path("."+random_id()+".tmp");std::string text=value.dump(2)+"\n";
    try{
    ps_fs::create_directories(path.parent_path());
#ifdef _WIN32
        HANDLE h=CreateFileW(tmp.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
        require(h!=INVALID_HANDLE_VALUE,"STORAGE","Cannot create temporary document");DWORD n=0;
        bool ok=WriteFile(h,text.data(),DWORD(text.size()),&n,nullptr)&&n==text.size()&&FlushFileBuffers(h);CloseHandle(h);
        require(ok,"STORAGE","Cannot persist temporary document");
        require(MoveFileExW(tmp.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0,"STORAGE","Atomic replacement failed");
#else
        int fd=open(tmp.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);require(fd>=0,"STORAGE","Cannot create temporary document");
        size_t done=0;while(done<text.size()){auto n=write(fd,text.data()+done,text.size()-done);if(n<=0)break;done+=size_t(n);}bool ok=done==text.size()&&fsync(fd)==0;close(fd);
        require(ok,"STORAGE","Cannot persist temporary document");require(rename(tmp.c_str(),path.c_str())==0,"STORAGE","Atomic replacement failed");
        int directory=open(path.parent_path().c_str(),O_RDONLY|O_DIRECTORY);if(directory>=0){bool synced=fsync(directory)==0;close(directory);require(synced,"STORAGE","Directory sync failed; durability unknown");}
#endif
    }catch(const Error &){std::error_code ec;ps_fs::remove(tmp,ec);throw;}
    catch(...){std::error_code ec;ps_fs::remove(tmp,ec);throw Error("STORAGE","Document write failed; existing version preserved");}
}
Logs::Logs(std::string b,ps_fs::path d):boot_(std::move(b)),directory_(std::move(d)),writer_(){load_archive();writer_=std::thread([this]{writer();});}
void Logs::load_archive(){
    // Only approved fixed rotation segments; no client paths, no recursive scan.
    size_t bytes=0;
    for(int segment=3;segment>=0;--segment){
        auto path=directory_/(segment?"events."+std::to_string(segment)+".jsonl":"events.jsonl");
        std::error_code ec;auto type=ps_fs::symlink_status(path,ec);
        if(ec||!ps_fs::exists(type))continue;
        if(!ps_fs::is_regular_file(type)){++archive_errors_;continue;}
        std::ifstream file(path,std::ios::binary);if(!file){++archive_errors_;continue;}
        // Bound total scanned bytes even for externally oversized/corrupt files.
        size_t scanned=0;std::string line;bool oversized=false;
        char c;while(file.get(c)){
            if(++scanned>4*1024*1024+16384){++archive_errors_;break;}
            if(c!='\n'){if(line.size()<8192)line+=c;else oversized=true;continue;}
            try{
                require(!oversized,"FORMAT","Oversized archived event");auto row=Json::parse(line);
                for(auto key:{"schema_version","boot_id","event_id","monotonic_us","wall_time_valid","wall_time","severity","component","command_id","task_id","event","details","simulation"})require(row.contains(key),"FORMAT","Incomplete archived event");
                require(row.at("schema_version")==1&&row.at("boot_id").is_string()&&logical_id(row.at("boot_id"))&&row.at("simulation")==true,"FORMAT","Invalid archived identity/source");
                (void)u64(row.at("event_id"),"event_id");(void)u64(row.at("monotonic_us"),"monotonic_us");
                require(row.at("event").is_string()&&row.at("component").is_string()&&row.at("details").is_object(),"FORMAT","Invalid archived fields");
                archive_.push_back(row);bytes+=row.dump().size();
                while(archive_.size()>10000||bytes>16*1024*1024){bytes-=archive_.front().dump().size();archive_.pop_front();++archive_retired_;}
            }catch(...){++archive_errors_;}
            line.clear();oversized=false;
        }
        if(!line.empty()||oversized)++archive_errors_; // interrupted/truncated final record
    }
}
Json Logs::boots(){
    std::lock_guard<std::mutex> lock(mutex_);Json ids=Json::array({boot_});
    for(const auto &r:archive_){auto b=r.at("boot_id");if(std::find(ids.begin(),ids.end(),b)==ids.end())ids.push_back(b);}
    return {{"boot_ids",ids},{"current_boot_id",boot_},{"history_incomplete",true},{"archive_errors",std::to_string(archive_errors_)},{"archive_retired",std::to_string(archive_retired_)}};
}
Logs::~Logs(){stop_=true;wake_.notify_all();writer_.join();}
void Logs::emit(const std::string &event,const std::string &component,const std::string &level,Json details,const std::string &command,const std::string &task){
    Json row={{"schema_version",1},{"boot_id",boot_},{"event_id",""},{"monotonic_us",""},
        {"wall_time_valid",false},{"wall_time",nullptr},{"severity",level},{"component",component},{"command_id",command.empty()?Json():Json(command)},
        {"task_id",task.empty()?Json():Json(task)},{"event",event},{"details",std::move(details)},{"simulation",true}};
    if(row.dump().size()>8192)row["details"]={{"truncated",true},{"reason","event exceeds 8192 byte fixture limit"}};
    std::unique_lock<std::mutex> lock(queue_mutex_,std::try_to_lock);
    if(!lock||queue_.size()>=1024){++dropped_;return;}
    row["event_id"]=std::to_string(++serial_);row["monotonic_us"]=std::to_string(monotonic_us());
    queue_.push_back(std::move(row));queue_depth_=queue_.size();lock.unlock();wake_.notify_one();
}
void Logs::writer(){
    while(!stop_){Json row;{std::unique_lock<std::mutex> lock(queue_mutex_);wake_.wait_for(lock,std::chrono::milliseconds(20),[&]{return stop_||(!queue_.empty()&&!pause_writer_);});
        if(stop_)break;if(queue_.empty()||pause_writer_)continue;row=std::move(queue_.front());queue_.pop_front();queue_depth_=queue_.size();in_flight_=row;}
        {std::lock_guard<std::mutex> lock(mutex_);history_.push_back(row);if(history_.size()>10000){history_.pop_front();++retired_;}}
        {std::lock_guard<std::mutex> lock(queue_mutex_);in_flight_=nullptr;}
        try{if(fail_disk_)throw std::runtime_error("injected disk failure");ps_fs::create_directories(directory_);
            auto current=directory_/"events.jsonl";std::error_code ec;
            if(ps_fs::exists(current)&&ps_fs::file_size(current)>4*1024*1024){
                ps_fs::remove(directory_/"events.3.jsonl",ec);
                for(int i=2;i>=0;i--){auto a=i?directory_/("events."+std::to_string(i)+".jsonl"):current;auto b=directory_/("events."+std::to_string(i+1)+".jsonl");if(ps_fs::exists(a))ps_fs::rename(a,b);}}
            std::ofstream f(current,std::ios::app|std::ios::binary);f.exceptions(std::ios::failbit|std::ios::badbit);f<<row.dump()<<'\n';f.flush();f.close();persisted_=u64(row.at("event_id"),"event_id");
        }catch(...){++write_errors_;}
    }
}
Json Logs::stats(){std::lock_guard<std::mutex> lock(mutex_);return {{"last_event_id",std::to_string(serial_)},{"queue_depth",queue_depth_.load()},
    {"dropped",std::to_string(dropped_)},{"write_errors",std::to_string(write_errors_)},{"last_flushed_event_id",std::to_string(persisted_)},
    {"retired",std::to_string(retired_)},{"durability","stream_flushed_not_power_loss_verified"},{"history_count",history_.size()}};}
Json Logs::snapshot(const Json &filter){
    require(filter.is_object(),"FORMAT","Log filter must be object");
    for(auto i=filter.begin();i!=filter.end();++i)require(i.key()=="boot_id"||i.key()=="clock"||i.key()=="from_us"||i.key()=="to_us"||i.key()=="severity"||i.key()=="component"||i.key()=="command_id"||i.key()=="task_id","FORMAT","Unknown log filter",i.key());
    require(filter.value("clock",std::string("monotonic"))=="monotonic","CLOCK_INVALID","Fixture wall clock is not trusted; use boot monotonic time");
    auto selected=filter.value("boot_id",boot_);require(logical_id(selected),"FORMAT","Invalid boot identity");
    uint64_t from=filter.contains("from_us")?u64(filter.at("from_us"),"from_us"):0,to=filter.contains("to_us")?u64(filter.at("to_us"),"to_us"):UINT64_MAX;
    require(from<=to,"FORMAT","Reversed time range");uint64_t now=monotonic_us();std::lock_guard<std::mutex> lock(mutex_);
    for(auto it=snapshots_.begin();it!=snapshots_.end();)if(it->second.expires<=now)it=snapshots_.erase(it);else ++it;
    require(snapshots_.size()<4,"SNAPSHOT_LIMIT","Four live snapshots already exist; wait for expiry");Json rows=Json::array();size_t bytes=0;bool truncated=false;
    std::deque<Json> source;
    if(selected==boot_)source=history_;
    else {for(const auto &r:archive_)if(r.at("boot_id")==selected)source.push_back(r);require(!source.empty(),"LOG_RETIRED","Boot unavailable or outside retention");}
    uint64_t upper=source.empty()?0:u64(source.back().at("event_id"),"event_id");
    if(selected==boot_){std::lock_guard<std::mutex> queued(queue_mutex_);if(!in_flight_.is_null()&&u64(in_flight_.at("event_id"),"event_id")>upper){source.push_back(in_flight_);upper=u64(in_flight_.at("event_id"),"event_id");}
        for(const auto &r:queue_){source.push_back(r);upper=u64(r.at("event_id"),"event_id");}}
    for(const auto &r:source){auto t=u64(r.at("monotonic_us"),"time");if(t<from||t>to)continue;bool match=true;
        for(auto key:{"severity","component","command_id","task_id"})if(filter.contains(key)&&!filter.at(key).is_null()&&filter.at(key)!=""&&filter.at(key)!=r.at(key))match=false;
        if(!match)continue;bytes+=r.dump().size()+1;if(bytes>16*1024*1024||rows.size()>=10000){truncated=true;break;}rows.push_back(r);}
    std::string id=random_id();Json meta={{"schema_version",1},{"record_type","snapshot"},{"snapshot_id",id},{"boot_id",selected},{"filters",filter},
        {"count",rows.size()},{"lower_event_id",rows.empty()?Json():rows.front().at("event_id")},{"upper_event_id",std::to_string(upper)},{"truncated",truncated},{"gaps",selected!=boot_||dropped_.load()!=0||retired_!=0||write_errors_.load()!=0},
        {"dropped",std::to_string(dropped_)},{"retired",std::to_string(retired_)},{"write_errors",std::to_string(write_errors_)},
        {"expires_monotonic_us",std::to_string(now+60000000)},{"simulation",true},{"durability",selected==boot_?"memory_snapshot; stream_flush_only; failures_reported":"reloaded_retained_segments; historical_completeness_unknown; flush_only"}};
    snapshots_.emplace(id,Snapshot{now+60000000,std::move(rows),meta});return meta;
}
Json Logs::page(const std::string &id,size_t offset,size_t limit){std::lock_guard<std::mutex> lock(mutex_);auto it=snapshots_.find(id);
    require(it!=snapshots_.end()&&it->second.expires>monotonic_us(),"SNAPSHOT_EXPIRED","Snapshot missing or expired");auto &s=it->second;
    require(limit>=1&&limit<=100&&offset<=s.rows.size(),"FORMAT","Invalid page bounds");Json rows=Json::array();size_t end=std::min(offset+limit,s.rows.size());for(size_t i=offset;i<end;i++)rows.push_back(s.rows[i]);
    return {{"metadata",s.metadata},{"events",rows},{"next_cursor",end<s.rows.size()?Json(id+":"+std::to_string(end)):Json()}};
}
Json Logs::detail(const std::string &id,const std::string &boot){auto selected=boot.empty()?boot_:boot;require(logical_id(selected),"FORMAT","Invalid boot identity");(void)u64(id,"event_id");std::lock_guard<std::mutex> lock(mutex_);for(const auto &r:selected==boot_?history_:archive_)if(r.at("boot_id")==selected&&r.at("event_id")==id)return r;
    for(const auto &s:snapshots_)if(s.second.expires>monotonic_us())for(const auto &r:s.second.rows)if(r.at("boot_id")==selected&&r.at("event_id")==id)return r;
    throw Error("LOG_RETIRED","Event missing, dropped or outside retention");}
std::string Logs::export_jsonl(const std::string &id){Json rows,meta;{std::lock_guard<std::mutex> lock(mutex_);auto i=snapshots_.find(id);require(i!=snapshots_.end()&&i->second.expires>monotonic_us(),"SNAPSHOT_EXPIRED","Snapshot missing or expired");rows=i->second.rows;meta=i->second.metadata;}
    std::string result=meta.dump()+"\n";for(auto &r:rows)result+=r.dump()+"\n";return result;}
Json Logs::events_after(uint64_t id){std::lock_guard<std::mutex> lock(mutex_);Json rows=Json::array();bool gap=id>serial_;if(gap)id=0;gap|=(!history_.empty()&&id+1<u64(history_.front().at("event_id"),"event_id"));
    uint64_t previous=id;for(auto &r:history_)if(u64(r.at("event_id"),"event_id")>id){auto n=u64(r.at("event_id"),"event_id");gap|=n!=previous+1;previous=n;if(rows.size()<100)rows.push_back(r);else break;}
    return {{"events",rows},{"gap",gap},{"dropped",std::to_string(dropped_)},{"boot_id",boot_}};}
}
