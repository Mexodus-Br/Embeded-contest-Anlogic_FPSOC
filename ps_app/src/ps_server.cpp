#include "ps_runtime.hpp"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cctype>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <thread>
#ifndef _WIN32
#include <fcntl.h>
#endif
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
using Socket=SOCKET;
static void close_socket(Socket s){closesocket(s);}
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
using Socket=int;
constexpr int INVALID_SOCKET=-1;
static void close_socket(Socket s){close(s);}
#endif

namespace {
using ps::Json;
struct Request {std::string method,path;std::map<std::string,std::string> headers,query;Json body=Json::object();};
struct Session {std::string csrf;uint64_t expires;};
struct Http {
    std::shared_ptr<ps::Service> service;
    ps_fs::path root;
    std::string token,origin,localhost;
    std::mutex sessions_mutex;
    std::map<std::string,Session> sessions;
    std::atomic<int> connections{0},controls{0},exports{0},streams{0};
};
static bool send_all(Socket s,const std::string &text){size_t done=0;while(done<text.size()){
#ifdef _WIN32
    int n=send(s,text.data()+done,int(std::min<size_t>(16384,text.size()-done)),0);
#else
    auto n=send(s,text.data()+done,std::min<size_t>(16384,text.size()-done),MSG_NOSIGNAL);
#endif
    if(n<=0)return false;done+=size_t(n);}return true;}
static void reply(Socket s,int status,const std::string &body,const std::string &type="application/json; charset=utf-8",const std::string &extra=""){
    std::string header="HTTP/1.1 "+std::to_string(status)+" Result\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\n";
    header+="Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'\r\n";
    header+="Content-Type: "+type+"\r\nContent-Length: "+std::to_string(body.size())+"\r\n"+extra+"\r\n";if(send_all(s,header))send_all(s,body);
}
static std::string decode(const std::string &s){std::string out;for(size_t i=0;i<s.size();i++){
    if(s[i]=='%'){ps::require(i+2<s.size(),"FORMAT","Bad URL encoding");auto hex=[](char c){if(c>='0'&&c<='9')return c-'0';c=char(std::tolower(static_cast<unsigned char>(c)));return c>='a'&&c<='f'?c-'a'+10:-1;};int a=hex(s[i+1]),b=hex(s[i+2]);ps::require(a>=0&&b>=0,"FORMAT","Bad URL encoding");out+=char(a*16+b);i+=2;}else out+=s[i]=='+'?' ':s[i];}
    ps::require(out.find('\0')==std::string::npos,"FORMAT","NUL in URL");return out;
}
static Request receive(Socket fd){std::string buffer;char chunk[4096];size_t boundary=std::string::npos;
    while((boundary=buffer.find("\r\n\r\n"))==std::string::npos){int n=recv(fd,chunk,sizeof(chunk),0);ps::require(n>0,"FORMAT","Incomplete request header");buffer.append(chunk,size_t(n));ps::require(buffer.size()<=16384,"RESOURCE_LIMIT","Request headers too large");}
    Request r;std::istringstream stream(buffer.substr(0,boundary));std::string line,url,version;std::getline(stream,line);std::istringstream first(line);first>>r.method>>url>>version;
    ps::require(version=="HTTP/1.1"&&(r.method=="GET"||r.method=="POST"||r.method=="PUT"||r.method=="DELETE"),"FORMAT","Unsupported method/protocol");
    while(std::getline(stream,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();auto colon=line.find(':');ps::require(colon!=std::string::npos,"FORMAT","Malformed header");std::string key=line.substr(0,colon),value=line.substr(colon+1);while(!value.empty()&&value.front()==' ')value.erase(value.begin());
        std::transform(key.begin(),key.end(),key.begin(),[](unsigned char c){return char(std::tolower(c));});ps::require(!r.headers.count(key),"FORMAT","Duplicate header");r.headers[key]=value;}
    ps::require(!r.headers.count("transfer-encoding"),"FORMAT","Chunked request bodies unsupported");size_t length=0;
    if(r.headers.count("content-length"))length=size_t(ps::u64(r.headers.at("content-length"),"Content-Length"));ps::require(length<=2*1024*1024,"RESOURCE_LIMIT","Request body exceeds 2 MiB");
    size_t start=boundary+4;while(buffer.size()-start<length){int n=recv(fd,chunk,sizeof(chunk),0);ps::require(n>0,"FORMAT","Incomplete request body");buffer.append(chunk,size_t(n));}
    if(length){ps::require(r.headers["content-type"].rfind("application/json",0)==0,"FORMAT","JSON content type required");r.body=Json::parse(buffer.substr(start,length));}
    auto q=url.find('?');r.path=decode(url.substr(0,q));if(q!=std::string::npos){std::istringstream parts(url.substr(q+1));std::string part;while(std::getline(parts,part,'&')){auto eq=part.find('=');ps::require(eq!=std::string::npos,"FORMAT","Query requires key=value");auto key=decode(part.substr(0,eq));ps::require(!r.query.count(key),"FORMAT","Duplicate query field");r.query[key]=decode(part.substr(eq+1));}}
    return r;
}
static bool equal_secret(const std::string &a,const std::string &b){unsigned diff=unsigned(a.size()^b.size());for(size_t i=0;i<std::min(a.size(),b.size());i++)diff|=unsigned(a[i]^b[i]);return diff==0;}
static std::string cookie(const Request &r){auto it=r.headers.find("cookie");if(it==r.headers.end())return "";std::istringstream cookies(it->second);std::string x;while(std::getline(cookies,x,';')){while(!x.empty()&&x.front()==' ')x.erase(x.begin());if(x.rfind("ps_session=",0)==0)return x.substr(11);}return "";}
static void serve(std::shared_ptr<Http> h,Socket fd,bool control){
    struct Guard{std::shared_ptr<Http> h;Socket fd;bool control;~Guard(){close_socket(fd);if(control)--h->controls;else --h->connections;}}guard{h,fd,control};
    try{auto r=receive(fd);ps::require(r.headers.count("host")&&(r.headers.at("host")==h->origin.substr(7)||r.headers.at("host")==h->localhost.substr(7)),"AUTH","Host must match configured origin");
        std::vector<std::string> expired;
        {std::lock_guard<std::mutex> l(h->sessions_mutex);for(auto i=h->sessions.begin();i!=h->sessions.end();)if(i->second.expires<=ps::monotonic_us()){expired.push_back(i->first);i=h->sessions.erase(i);}else ++i;}
        for(const auto &id:expired)h->service->revoke_session(id);
        if(r.method!="GET")ps::require(r.headers.count("origin")&&(r.headers.at("origin")==h->origin||r.headers.at("origin")==h->localhost),"AUTH","Same-origin request required");
        if(r.path=="/api/v1/auth"&&r.method=="POST"){
            ps::require(r.body.is_object()&&r.body.size()==1&&r.body.contains("token")&&r.body.at("token").is_string(),"AUTH","Token required");ps::require(equal_secret(r.body.at("token"),h->token),"AUTH","Authentication failed");
            std::lock_guard<std::mutex> l(h->sessions_mutex);
            ps::require(h->sessions.size()<16,"RESOURCE_LIMIT","Session capacity reached");std::string id=ps::random_id(),csrf=ps::random_id();h->sessions[id]={csrf,ps::monotonic_us()+3600000000ULL};
            reply(fd,200,Json({{"csrf",csrf},{"boot_id",h->service->boot_id()}}).dump(),"application/json; charset=utf-8","Set-Cookie: ps_session="+id+"; HttpOnly; SameSite=Strict; Path=/api/v1; Max-Age=3600\r\n");return;
        }
        if(r.path.rfind("/api/v1/",0)==0){std::string session=cookie(r),csrf;
            {std::lock_guard<std::mutex> l(h->sessions_mutex);auto i=h->sessions.find(session);ps::require(i!=h->sessions.end()&&i->second.expires>ps::monotonic_us(),"AUTH","Login required");csrf=i->second.csrf;}
            if(r.method!="GET")ps::require(r.headers.count("x-csrf-token")&&equal_secret(r.headers.at("x-csrf-token"),csrf),"AUTH","CSRF check failed");
            auto path=r.path.substr(7);
            if(path=="/auth"&&r.method=="GET"){reply(fd,200,Json({{"csrf",csrf},{"boot_id",h->service->boot_id()}}).dump());return;}
            if(path=="/auth"&&r.method=="DELETE"){{std::lock_guard<std::mutex> l(h->sessions_mutex);h->sessions.erase(session);}h->service->revoke_session(session);reply(fd,200,"{\"logged_out\":true}","application/json","Set-Cookie: ps_session=; HttpOnly; SameSite=Strict; Path=/api/v1; Max-Age=0\r\n");return;}
            if(path=="/logs/export"&&r.method=="GET"){
                int n=h->exports.fetch_add(1);struct ExportGuard{std::atomic<int>&n;~ExportGuard(){--n;}}eg{h->exports};ps::require(n<2,"RESOURCE_LIMIT","Two exports already active");
                ps::require(r.query.size()==1&&r.query.count("snapshot"),"FORMAT","Export accepts only snapshot identity");std::string id=r.query.at("snapshot");ps::require(ps::logical_id(id),"FORMAT","Invalid snapshot identity");
                auto text=h->service->export_log(id);reply(fd,200,text,"application/x-ndjson; charset=utf-8","Content-Disposition: attachment; filename=ps-log-"+id+".jsonl\r\n");return;
            }
            if(path=="/events"&&r.method=="GET"){
                int n=h->streams.fetch_add(1);struct StreamGuard{std::atomic<int>&n;~StreamGuard(){--n;}}sg{h->streams};ps::require(n<4,"RESOURCE_LIMIT","Four SSE streams already active");uint64_t after=0;bool wrong_boot=false;
                if(r.headers.count("last-event-id")){auto id=r.headers.at("last-event-id");auto colon=id.find(':');ps::require(colon!=std::string::npos,"FORMAT","Invalid event ID");wrong_boot=id.substr(0,colon)!=h->service->boot_id();if(!wrong_boot)after=ps::u64(id.substr(colon+1),"event_id");}
                if(!send_all(fd,"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream; charset=utf-8\r\nCache-Control: no-store\r\nConnection: close\r\nX-Content-Type-Options: nosniff\r\n\r\n"))return;
                if(wrong_boot&&!send_all(fd,"event: gap\ndata: {\"reason\":\"boot_changed\"}\n\n"))return;
                std::string dropped="0";
                for(;;){auto events=h->service->events(after);bool gap=events.at("gap").get<bool>()||events.at("dropped")!=dropped;dropped=events.at("dropped");if(gap)if(!send_all(fd,"event: gap\ndata: {\"reason\":\"events_missing\"}\n\n"))return;
                    for(auto &e:events.at("events")){after=ps::u64(e.at("event_id"),"event_id");if(!send_all(fd,"id: "+h->service->boot_id()+":"+std::to_string(after)+"\nevent: log\ndata: "+e.dump()+"\n\n"))return;}
                    if(!send_all(fd,"event: state\ndata: "+h->service->state().dump()+"\n\n"))return;
                    {std::lock_guard<std::mutex> l(h->sessions_mutex);auto i=h->sessions.find(session);if(i==h->sessions.end()||i->second.expires<=ps::monotonic_us())return;}
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));}
            }
            auto result=h->service->handle(r.method,path,r.query,r.body,session);reply(fd,200,result.dump());return;
        }
        if(r.path=="/api/health"&&r.method=="GET"){reply(fd,200,Json({{"app",h->service->state().at("simulation").get<bool>()?"ps-simulation":"ps-hardware"},{"version",1},{"simulation",h->service->state().at("simulation")}}).dump());return;}
        ps::require(r.method=="GET","NOT_FOUND","Unknown resource");static const std::map<std::string,std::string> assets={{"/","index.html"},{"/index.html","index.html"},{"/app.js","app.js"},{"/style.css","style.css"}};
        auto it=assets.find(r.path);ps::require(it!=assets.end(),"NOT_FOUND","Unknown static resource");std::ifstream f(h->root/"web/ps"/it->second,std::ios::binary);ps::require(bool(f),"NOT_FOUND","Static resource missing");std::ostringstream bytes;bytes<<f.rdbuf();reply(fd,200,bytes.str(),it->second=="app.js"?"application/javascript; charset=utf-8":it->second=="style.css"?"text/css; charset=utf-8":"text/html; charset=utf-8");
    }catch(const ps::Error &e){auto code=e.detail.at("code").get<std::string>();int status=code=="AUTH"?401:code=="NOT_FOUND"?404:code=="RESOURCE_LIMIT"?429:400;
        if(code=="BUSY"||code=="PREVIEW_STALE"||code=="ID_CONFLICT"||code=="CONTROL_BUSY"||code=="VERSION_CONFLICT")status=409;
        reply(fd,status,Json({{"ok",false},{"error",e.detail}}).dump());}
    catch(const std::exception &){reply(fd,400,Json({{"ok",false},{"error",ps::Error("FORMAT","Malformed or incomplete request").detail}}).dump());}
}
}
static void nonblocking(Socket fd,bool enabled){
#ifdef _WIN32
    u_long mode=enabled?1:0;ioctlsocket(fd,FIONBIO,&mode);
#else
    auto flags=fcntl(fd,F_GETFL,0);fcntl(fd,F_SETFL,enabled?flags|O_NONBLOCK:flags&~O_NONBLOCK);
#endif
}
int main(int argc,char **argv){try{
    int port=18083;std::string backend,bind_address="127.0.0.1";bool allow_injection=false;ps_fs::path root=ps_fs::current_path(),data=root/"runs/ps",token_file=root/".cache/ps-token";
    for(int i=1;i<argc;i++){std::string arg=argv[i];ps::require(i+1<argc,"FORMAT","Option needs value");std::string value=argv[++i];if(arg=="--backend")backend=value;else if(arg=="--bind")bind_address=value;else if(arg=="--allow-simulation-injection"){ps::require(value=="true"||value=="false","FORMAT","Expected true or false");allow_injection=value=="true";}else if(arg=="--port")port=std::stoi(value);else if(arg=="--data")data=ps_fs::u8path(value);else if(arg=="--token-file")token_file=ps_fs::u8path(value);else throw ps::Error("FORMAT","Unknown option");}
    ps::require(backend=="simulation"||backend=="hardware","BACKEND_UNAVAILABLE","Select --backend simulation or hardware explicitly (no fallback)");
    ps::require(backend!="hardware"||!allow_injection,"FORMAT","Simulation injection forbidden in hardware mode");
    ps::require(port>1024&&port<65536,"FORMAT","Invalid port");
#ifdef _WIN32
    WSADATA wsa;ps::require(WSAStartup(MAKEWORD(2,2),&wsa)==0,"NETWORK","Winsock startup failed");
#endif
    in_addr bind_ip{};
    ps::require(inet_pton(AF_INET,bind_address.c_str(),&bind_ip)==1&&bind_ip.s_addr!=htonl(INADDR_ANY)&&bind_ip.s_addr!=htonl(INADDR_BROADCAST),"FORMAT","--bind requires a concrete local IPv4 address");
    auto h=std::make_shared<Http>();h->root=root;h->origin="http://"+bind_address+":"+std::to_string(port);h->localhost=bind_address=="127.0.0.1"?"http://localhost:"+std::to_string(port):h->origin;
    if(!ps_fs::exists(token_file)){ps_fs::create_directories(token_file.parent_path());std::ofstream f(token_file);f.exceptions(std::ios::failbit|std::ios::badbit);f<<ps::random_id()<<ps::random_id()<<'\n';f.close();}
    {std::ifstream f(token_file);std::getline(f,h->token);ps::require(h->token.size()>=32&&ps::logical_id(h->token),"AUTH","Token file invalid");}
    Socket listener=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);ps::require(listener!=INVALID_SOCKET,"NETWORK","Cannot create listener");sockaddr_in address{};address.sin_family=AF_INET;address.sin_port=htons(uint16_t(port));address.sin_addr=bind_ip;
    ps::require(bind(listener,reinterpret_cast<sockaddr*>(&address),sizeof(address))==0,"NETWORK","Port unavailable");ps::require(listen(listener,32)==0,"NETWORK","Listen failed");
    h->service=std::make_shared<ps::Service>(root,data,allow_injection,backend=="hardware");std::cout<<"PS "+backend+": "<<h->origin<<" (explicit bind; login required)"<<std::endl;
    struct Pending {Socket fd;uint64_t deadline;};std::deque<Pending> pending;
    nonblocking(listener,true);
    for(;;){
      // No body or slow header is read on this accept/admission thread.
      fd_set readable;FD_ZERO(&readable);FD_SET(listener,&readable);
      Socket largest=listener;for(const auto &p:pending){FD_SET(p.fd,&readable);largest=std::max(largest,p.fd);}
      timeval poll{0,10000};select(int(largest+1),&readable,nullptr,nullptr,&poll);
      auto now=ps::monotonic_us();
      for(auto it=pending.begin();it!=pending.end();){
        bool remove=now>=it->deadline;
        if(!remove&&FD_ISSET(it->fd,&readable)){
          char header[16385];int count=recv(it->fd,header,16384,MSG_PEEK);
          if(count<=0)remove=true;
          else {std::string text(header,size_t(count));auto end=text.find("\r\n\r\n");
            if(end!=std::string::npos){
              bool control=text.rfind("POST /api/v1/stop HTTP/1.1\r\n",0)==0||text.rfind("GET /api/v1/state HTTP/1.1\r\n",0)==0;
              if(control){
                // Validate a bounded complete request before reserving control capacity.
                // A slow-body peer is still only an evictable admission candidate.
                std::string lower=text.substr(0,end);std::transform(lower.begin(),lower.end(),lower.begin(),[](unsigned char c){return char(std::tolower(c));});
                size_t length=0;auto at=lower.find("\r\ncontent-length:");
                try{if(at!=std::string::npos){auto value=lower.substr(at+17);value=value.substr(0,value.find("\r\n"));auto first=value.find_first_not_of(' ');length=size_t(ps::u64(value.substr(first),"Content-Length"));}}catch(...){remove=true;}
                if(length>1024||lower.find("\r\ntransfer-encoding:")!=std::string::npos)remove=true;
                if(remove){close_socket(it->fd);it=pending.erase(it);continue;}
                if(text.size()<end+4+length){++it;continue;}
              }
              auto &budget=control?h->controls:h->connections;int limit=control?4:32;
              if(budget.load()<limit){auto fd=it->fd;++budget;nonblocking(fd,false);std::thread([h,fd,control]{serve(h,fd,control);}).detach();it=pending.erase(it);continue;}
              // Avoid network writes in admission: shed complete ordinary requests.
              remove=true;
            }else if(count>=16384)remove=true;
          }
        }
        if(remove){close_socket(it->fd);it=pending.erase(it);}else ++it;
      }
      // Bounded accept batch prevents a connection flood starving ready headers.
      for(int accepted=0;accepted<16;accepted++){
        Socket fd=accept(listener,nullptr,nullptr);if(fd==INVALID_SOCKET)break;
#ifdef _WIN32
        DWORD timeout=5000;setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,reinterpret_cast<const char*>(&timeout),sizeof(timeout));setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,reinterpret_cast<const char*>(&timeout),sizeof(timeout));
#else
        timeval timeout{5,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
#endif
        nonblocking(fd,true);
        // A silent peer cannot reserve admission forever or exclude a new STOP.
        if(pending.size()>=48){close_socket(pending.front().fd);pending.pop_front();}
        pending.push_back({fd,ps::monotonic_us()+1000000});
      }
    }
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
