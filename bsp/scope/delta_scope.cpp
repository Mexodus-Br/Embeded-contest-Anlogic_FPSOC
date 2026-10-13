// No-motor coordinate test. Single device owner, independent STOP/snapshot.
#include "model.hpp"
#include "motion_uapi.h"
#include "mot2_codec.h"
#include <atomic>
#include <algorithm>
#include <cstdlib>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <iostream>
#include <limits>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>
#include <vector>
#define P(x) PLI_MOTION_GP_MOTION_V1_##x
static_assert(sizeof(float)==4 && sizeof(double)==8,"Golden float32/double64 required");
static const char *sockpath="/run/delta-scope.sock";
static golden::Config config;
static int device=-1,listener=-1;
static std::mutex writer;
static std::atomic<unsigned> cancellation{0};
static std::atomic<bool> initialized{false},serving{true};
static thread_local bool touched=false;
static uint64_t pair(const uint32_t *p){return (uint64_t(p[1])<<32)|p[0];}
static void need(bool b,const std::string&s){if(!b)throw std::runtime_error(s);}
static void control(unsigned long op,void*p=nullptr){if(ioctl(device,op,p)<0)throw std::runtime_error("ioctl "+std::to_string(op)+": "+std::strerror(errno));}
static motion_snapshot snapshot(){motion_snapshot s{};control(MOTION_SNAPSHOT,&s);need(!s.quarantined,"QUARANTINE: buffer must be retained");return s;}
static motion_command command(unsigned op,unsigned mask,const std::array<int,3>*pos=nullptr){
 motion_command c{};c.opcode=op;c.axis_mask=mask;c.timeout_ms=2000;
 if(pos)for(unsigned i=0;i<3;i++)c.position[i]=(*pos)[i];
 control(MOTION_COMMAND,&c);need(!c.ack_error && (c.ack_status&7)==7,"command not completed");return c;
}
static void stable(const motion_snapshot&s){need(!(s.words[P(SNAP_WORD_STATUS)]&(P(STATUS_BITS_BUSY_MASK)|P(STATUS_BITS_RUNNING_MASK)|P(STATUS_BITS_PACKET_BUSY_MASK))),"not idle");need(!s.words[P(SNAP_WORD_BUFFERED)]&&!s.dma_owned,"queue or DMA owned");}
static void print_snapshot(std::ostream&o,const char*tag,const motion_snapshot&s){
 o<<"SNAP "<<tag<<" generation="<<s.generation<<" status=0x"<<std::hex<<s.words[P(SNAP_WORD_STATUS)]<<" error=0x"<<s.words[P(SNAP_WORD_ERROR)]<<" validity=0x"<<s.words[P(SNAP_WORD_VALIDITY)]<<std::dec
  <<" signals=0x"<<std::hex<<s.words[P(SNAP_WORD_SIGNALS)]<<std::dec<<" accepted="<<s.words[P(SNAP_WORD_ACCEPT_SEQ)]<<" active="<<s.words[P(SNAP_WORD_ACTIVE_SEQ)]<<" done="<<s.words[P(SNAP_WORD_DONE_SEQ)]<<" END="<<s.words[P(SNAP_WORD_END_COUNT)]<<" buffered="<<s.words[P(SNAP_WORD_BUFFERED)]<<" dma_owned="<<s.dma_owned<<" quarantine="<<s.quarantined;
 for(unsigned i=0;i<4;i++)o<<" pos"<<i<<'='<<int64_t(pair(s.words+16+4*i))<<" pulse"<<i<<'='<<pair(s.words+18+4*i);
 o<<'\n';
}
struct Point{golden::IK ik;golden::Steps steps;std::array<float,3>xyz;unsigned ms=0;};
static void encode_scope(uint8_t*b,uint64_t session,uint64_t ticks,const int64_t target[4]){
 mot_encode(b,session,0,ticks,target,1);
 mot_put(b+F(AXIS_MASK_OFFSET),7,F(AXIS_MASK_SIZE));mot_put(b+F(CRC_OFFSET),mot_crc(b,F(CRC_OFFSET)),F(CRC_SIZE));
}
static Point parse_point(const std::vector<std::string>&v,bool duration){
 need(v.size()==(duration?7u:5u)&&v[1]=="--xyz", "expected init/model --xyz x y z or move --xyz x y z --duration-ms integer");Point p{};
 for(unsigned i=0;i<3;i++){
  size_t used=0;double n=std::stod(v[i+2],&used);need(used==v[i+2].size()&&std::isfinite(n)&&std::abs(n)<=std::numeric_limits<float>::max(),"nonfinite/float overflow XYZ");p.xyz[i]=float(n);
 }
 p.ik=golden::xyz_to_angles(p.xyz[0],p.xyz[1],p.xyz[2],config);need(p.ik.valid,"unreachable/invalid IK");
 p.steps=golden::angles_to_steps(p.ik.angles,config);need(p.steps.valid,"step conversion overflow/invalid");
 if(duration){need(v[5]=="--duration-ms","missing duration-ms");size_t used=0;unsigned long ms=std::stoul(v[6],&used);need(used==v[6].size()&&v[6][0]!='-'&&ms>=1&&ms<=2000,"duration must be integer 1..2000ms");p.ms=unsigned(ms);}
 return p;
}
static void print_model(std::ostream&o,const Point&p){
 o<<std::setprecision(17)<<"MODEL Golden unchanged; float32/double64 O0 no-fast-math ffp-contract=off; axis_order=X_high,Y_low,Z_rot\n"
 <<"CONFIG R="<<config.R<<" r="<<config.r<<" L="<<config.L<<" l="<<config.l<<" teeth="<<config.main_teeth<<'/'<<config.motor_teeth<<" microsteps="<<config.microsteps<<" steps_per_rev="<<config.steps_per_rev<<" target_range="<<config.target_min<<','<<config.target_max<<" (reference, no mechanical calibration)\nXYZ";
 for(auto x:p.xyz){o<<' '<<x;}
 o<<"\nangles_rad";for(auto x:p.ik.angles){o<<' '<<x;}
 o<<"\ntarget_steps";for(auto x:p.steps.targets){o<<' '<<x;}
 o<<" M4=0 factor="<<p.steps.factor<<'\n';
}
static void not_cancelled(unsigned epoch){need(cancellation.load()==epoch,"independent STOP cancelled request; no automatic restart");}
static std::string execute(const std::vector<std::string>&v){
 need(!v.empty(),"empty request");std::ostringstream o;
 if(v[0]=="snapshot"){need(v.size()==1,"snapshot args");print_snapshot(o,"current",snapshot());return o.str();}
 if(v[0]=="stop"){
  need(v.size()==1,"stop args");cancellation.fetch_add(1);control(MOTION_STOP);auto s=snapshot();need(s.words[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_STOP_COMPLETE_MASK),"STOP not pulse-safe");print_snapshot(o,"STOP",s);o<<"STOP_PASS (EN retained until explicit DISABLE; next move requires fresh session)\n";return o.str();
 }
 if(v[0]=="shutdown"){
  need(v.size()==1,"shutdown args");cancellation.fetch_add(1);control(MOTION_STOP);
  std::lock_guard<std::mutex>lock(writer);command(PLI_CMD_DISABLE,7);control(MOTION_RELEASE);initialized=false;serving=false;shutdown(listener,SHUT_RDWR);o<<"SHUTDOWN_PASS pulse-safe DISABLE RELEASE buffer freed\n";return o.str();
 }
 need(v[0]=="init"||v[0]=="move","unknown command");
 // Validate XYZ before any recover/enable/MM2S side effect.
 Point p=parse_point(v,v[0]=="move");print_model(o,p);
 std::lock_guard<std::mutex>lock(writer);unsigned epoch=cancellation.load();
 if(v[0]=="init"){
  auto before=snapshot();stable(before);
  need(((before.words[P(SNAP_WORD_VALIDITY)]>>4)&7)==7,"scope config A0..A2 invalid");
  // Explicitly disable before the maintenance-only no-motor REBASE.
  touched=true;control(MOTION_STOP);command(PLI_CMD_DISABLE,7);control(MOTION_RECOVER);not_cancelled(epoch);
  auto disabled=snapshot();stable(disabled);need(((disabled.words[P(SNAP_WORD_SIGNALS)]>>8)&15)==0,"REBASE requires disabled EN");
  print_snapshot(o,"init-disabled",disabled);command(PLI_CMD_REBASE,7,&p.steps.targets);not_cancelled(epoch);command(PLI_CMD_ENABLE,7);not_cancelled(epoch);
  initialized=true;print_snapshot(o,"init-enabled",snapshot());o<<"INIT_PASS maintenance REBASE only; NOT HOME\n";return o.str();
 }
 need(initialized,"init required in explicit no-motor scope session");auto before=snapshot();stable(before);
 need(!before.words[P(SNAP_WORD_ERROR)]&&((before.words[P(SNAP_WORD_VALIDITY)]&7)==7),"fault/position invalid; explicit init/recovery required");
 std::array<uint64_t,3>counts{};uint64_t master=0;
 for(unsigned i=0;i<3;i++){
  int64_t pos=int64_t(pair(before.words+16+4*i));need(pos>=config.target_min&&pos<=config.target_max,"retained position outside reference range");
  int64_t delta=int64_t(p.steps.targets[i])-pos;counts[i]=uint64_t(delta<0?-delta:delta);master=std::max(master,counts[i]);
 }
 uint64_t cycles=uint64_t(p.ms)*100000;
 // Frozen planner: guard=Q+S+2=1002; tail=H+max(L,hold)=1000; ceil(100MHz/100kHz)=1000.
 need(master==0||(cycles>1002&&(cycles-1002)/master>=1000),"duration not executable under 5us/100kHz scope limits");
 print_snapshot(o,"before",before);touched=true;control(MOTION_RECOVER);not_cancelled(epoch);command(PLI_CMD_ENABLE,7);not_cancelled(epoch);
 auto opened=command(PLI_CMD_OPEN_SESSION,7);need(opened.session!=0,"zero session");not_cancelled(epoch);
 uint8_t b[P(RECORD_BYTES)];int64_t target[4]={p.steps.targets[0],p.steps.targets[1],p.steps.targets[2],0};
 encode_scope(b,opened.session,uint64_t(p.ms)*1000,target);
 auto pre=snapshot();need(pre.words[P(SNAP_WORD_BUFFERED)]<P(RAW_DEPTH)+P(PLAN_DEPTH)+1,"no prebuffer capacity");
 motion_packet packet{};packet.data=reinterpret_cast<uintptr_t>(b);packet.count=1;packet.timeout_ms=2000;
 control(MOTION_PACKET,&packet);not_cancelled(epoch);auto ready=snapshot();
 need(!ready.words[P(SNAP_WORD_ERROR)]&&ready.words[P(SNAP_WORD_BUFFERED)]==1&&ready.words[P(SNAP_WORD_ACCEPT_COUNT)]==pre.words[P(SNAP_WORD_ACCEPT_COUNT)]+1
 &&(ready.words[P(SNAP_WORD_VALIDITY)]&P(SNAP_VALIDITY_ACCEPT_VALID_MASK))&&ready.words[P(SNAP_WORD_ACCEPT_SEQ)]==0
 &&(ready.words[P(SNAP_WORD_STATUS)]&P(STATUS_BITS_START_READY_MASK)),"full prebuffer/accepted/START_READY missing");
 o<<"SUBMIT session="<<opened.session<<" seq=0 END=1 mask=7 count=1 BTT=72 ticks="<<p.ms*1000<<" IOC_ns="<<packet.ioc_ns<<" packet_closed_ns="<<packet.closed_ns<<" (not motion completion)\n";
 not_cancelled(epoch);command(PLI_CMD_START,7);
 auto deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(p.ms+2000);motion_snapshot after{};
 for(;;){not_cancelled(epoch);after=snapshot();need(!after.words[P(SNAP_WORD_ERROR)],"PL error; STOP and explicit recovery required");
  if(after.words[P(SNAP_WORD_END_COUNT)]==before.words[P(SNAP_WORD_END_COUNT)]+1)break;
  need(std::chrono::steady_clock::now()<deadline,"END timeout");std::this_thread::sleep_for(std::chrono::milliseconds(1));
 }
 stable(after);need(after.words[P(SNAP_WORD_DONE_SEQ)]==0&&(after.words[P(SNAP_WORD_VALIDITY)]&P(SNAP_VALIDITY_DONE_VALID_MASK)),"done seq/valid missing");
 for(unsigned i=0;i<3;i++){need(int64_t(pair(after.words+16+4*i))==target[i],"final position differs");uint64_t pulses=pair(after.words+18+4*i)-pair(before.words+18+4*i);need(pulses==counts[i],"pulse delta differs");o<<"AXIS A"<<i<<" STEP="<<pulses<<" DIR="<<(target[i]>=int64_t(pair(before.words+16+4*i))?"positive":"negative")<<'\n';}
 need(pair(after.words+28)==0&&pair(after.words+30)==pair(before.words+30),"M4 changed");print_snapshot(o,"after-END",after);o<<"MOVE_PASS\n";return o.str();
}
static std::vector<std::string>tokens(const std::string&s){std::istringstream in(s);std::vector<std::string>v;std::string x;while(in>>x)v.push_back(x);return v;}
static void worker(int fd){
 timeval timeout{5,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));std::string line;char c;
 while(line.size()<1024&&recv(fd,&c,1,0)==1&&c!='\n')line+=c;
 std::string result="REQUEST "+line+"\n";
 try{need(line.size()<1024,"request too long");result+=execute(tokens(line));}
 catch(const std::exception&e){result+="FAIL "+std::string(e.what())+"\n";
  // Rejected numeric input has no side effects. Runtime move errors must STOP.
  if(touched){try{control(MOTION_STOP);}catch(...){result+="STOP_FAILED quarantine: do not unload/free\n";}}
 }
 std::cout<<result<<std::flush;
 size_t sent=0;while(sent<result.size()){ssize_t n=send(fd,result.data()+sent,result.size()-sent,MSG_NOSIGNAL);if(n<=0)break;sent+=size_t(n);}close(fd);
}
int main(int argc,char**argv){
 try{
  need(argc>=2,"usage: delta-scope serve --no-motor-test | model --xyz x y z | init/move/stop/snapshot/shutdown");
  std::string action=argv[1];
  if(action=="serve"||action=="model"){
   const char*path=std::getenv("DELTA_SCOPE_CONFIG");config=golden::read_config(path?path:"/etc/delta-scope/firmware_reference.cfg");
   if(action=="model"){std::vector<std::string>v(argv+1,argv+argc);auto p=parse_point(v,false);print_model(std::cout,p);return 0;}
   need(argc==3&&std::string(argv[2])=="--no-motor-test"&&geteuid()==0,"explicit root/no-motor serve required");
   device=open("/dev/bsp-motion",O_RDWR|O_CLOEXEC);need(device>=0,"device unavailable");auto gate=snapshot();stable(gate);
   need(((gate.words[P(SNAP_WORD_VALIDITY)]>>4)&15)==7,"not fixed three-axis scope configuration");
   need(gate.words[P(SNAP_WORD_SIGNALS)]==0xf0,"startup requires STEP0 DIRpositive EN0");
   umask(077);listener=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);need(listener>=0,"socket");sockaddr_un addr{};addr.sun_family=AF_UNIX;std::strcpy(addr.sun_path,sockpath);
   need(bind(listener,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0,"socket already present; do not overwrite live owner");need(listen(listener,8)==0,"listen");
   std::cout<<"SCOPE_SERVER_READY no automatic REBASE/ENABLE/START; root-only socket\n"<<std::flush;
   std::vector<std::thread>threads;
   while(serving){int fd=accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);if(fd<0)break;ucred peer{};socklen_t len=sizeof(peer);if(getsockopt(fd,SOL_SOCKET,SO_PEERCRED,&peer,&len)||peer.uid!=0){close(fd);continue;}threads.emplace_back(worker,fd);}
   for(auto&t:threads){t.join();}
   close(listener);unlink(sockpath);close(device);return 0;
  }
  int fd=socket(AF_UNIX,SOCK_STREAM,0);need(fd>=0,"client socket");sockaddr_un addr{};addr.sun_family=AF_UNIX;std::strcpy(addr.sun_path,sockpath);need(connect(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0,"scope server not explicitly started");
  std::string line;for(int i=1;i<argc;i++){if(i>1)line+=' ';line+=argv[i];}line+='\n';need(send(fd,line.data(),line.size(),MSG_NOSIGNAL)==ssize_t(line.size()),"send");shutdown(fd,SHUT_WR);
  timeval timeout{30,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
  std::string response;char b[2048];ssize_t n;while((n=recv(fd,b,sizeof(b),0))>0)response.append(b,size_t(n));close(fd);need(n==0&&!response.empty(),"incomplete server response");std::cout<<response;return response.find("FAIL ")==std::string::npos?0:1;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
