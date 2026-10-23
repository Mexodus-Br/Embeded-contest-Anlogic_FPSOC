#include "ps_hardware_port.hpp"
#include "ps_runtime.hpp"
#include <iostream>
// Local line adapter for an authenticated serial supervisor. Never opens a UART.
int main(int argc,char **argv){try{
    ps::require(argc==3,"FORMAT","Usage: ps_control simulation|hardware DATA_DIRECTORY (run from ps_app)");
    const std::string mode=argv[1],session="local_serial_supervisor";
    ps::require(mode=="simulation"||mode=="hardware","FORMAT","Explicit backend required");
    ps::Service service(ps_fs::current_path(),ps_fs::u8path(argv[2]),false,mode=="hardware");
    std::mutex jobs_mutex,output_mutex;
    std::condition_variable wake;
    std::deque<ps::Json> jobs;
    bool closing=false;
    auto output=[&](ps::Json row,const ps::Json &request){
        row["request_id"]=request.value("request_id",ps::Json());
        std::lock_guard<std::mutex> lock(output_mutex);std::cout<<row.dump()<<std::endl;
    };
    auto execute=[&](const ps::Json &request){try{
        auto result=service.handle(request.at("method"),request.at("path"),{},request.value("body",ps::Json::object()),session);
        output({{"ok",true},{"result",result}},request);
    }catch(const ps::Error&e){output({{"ok",false},{"error",e.detail}},request);}
     catch(const std::exception&e){output({{"ok",false},{"error",e.what()}},request);}};
    std::thread worker([&]{for(;;){ps::Json request;
        {std::unique_lock<std::mutex> lock(jobs_mutex);wake.wait(lock,[&]{return closing||!jobs.empty();});
         if(closing)return;request=std::move(jobs.front());jobs.pop_front();}
        execute(request);
    }});
    // Main reader accepts STOP while the bounded ordinary worker plans or waits.
    std::string line;
    while(std::cin){line.clear();bool oversized=false;char ch;
        while(std::cin.get(ch)&&ch!='\n'){if(line.size()<2*1024*1024)line.push_back(ch);else oversized=true;}
        if(line.empty()&&!std::cin)break;
        ps::Json request=ps::Json::object();
        try{
            ps::require(!oversized,"RESOURCE_LIMIT","Line exceeds 2MiB");request=ps::Json::parse(line);
            ps::require(request.is_object()&&request.at("method").is_string()&&request.at("path").is_string(),"FORMAT","method/path required");
            if(request.contains("request_id"))ps::require(request.at("request_id").is_string()&&ps::logical_id(request.at("request_id")),"FORMAT","Invalid correlation ID");
            if(request.at("method")=="POST"&&request.at("path")=="/stop"){execute(request);continue;}
            std::lock_guard<std::mutex> lock(jobs_mutex);ps::require(jobs.size()<8,"RESOURCE_LIMIT","Ordinary serial queue full");jobs.push_back(request);wake.notify_one();
        }catch(const ps::Error&e){output({{"ok",false},{"error",e.detail}},request.is_object()?request:ps::Json::object());}
         catch(const std::exception&e){output({{"ok",false},{"error",e.what()}},ps::Json::object());}
    }
    {std::lock_guard<std::mutex> lock(jobs_mutex);closing=true;jobs.clear();}
    service.stop(session);wake.notify_all();worker.join();
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
