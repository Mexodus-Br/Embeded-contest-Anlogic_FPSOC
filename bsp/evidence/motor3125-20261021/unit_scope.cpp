// Exercise the exact input/codec functions without opening the motion device.
#define main scope_application_main
#include "delta_scope.cpp"
#undef main
int main(){
 try{
  const char*cfg=std::getenv("DELTA_SCOPE_CONFIG");
  config=golden::read_config(cfg?cfg:"golden_model/configs/firmware_reference.cfg");
  auto start=parse_point(tokens("init --xyz 0 0 -140"),false);
  auto end=parse_point(tokens("move --xyz 5 0 -140 --duration-ms 500"),true);
  need(start.steps.targets==std::array<int,3>{-1090,-1090,-1090},"origin differs");
  need(end.steps.targets==std::array<int,3>{-1089,-966,-1213},"endpoint differs");
  for(const char*s:{"move --xyz nan 0 -140 --duration-ms 500","move --xyz inf 0 -140 --duration-ms 500","move --xyz 0 0 0 --duration-ms 500","move --xyz 1e100 0 -140 --duration-ms 500","move --xyz 5 0 -140 --duration-ms 0","move --xyz 5 0 -140 --duration-ms -1","move --xyz 5 0 -140 --duration-ms 0.5"}){
   bool rejected=false;try{parse_point(tokens(s),true);}catch(const std::exception&){rejected=true;}need(rejected,std::string("accepted invalid: ")+s);
  }
  need(bench_feasible(28200,4)&&!bench_feasible(28100,4),"new H/L duration boundary");
  need(!bench_feasible(3127,1)&&bench_feasible(9377,1)&&!bench_feasible(9376,1),"guard and exact period");
  need(bench_feasible(50000000,2398)&&!bench_feasible(50000000,8000)&&bench_feasible(50000000,7999),"500ms rate boundary");
  int64_t target[4]={end.steps.targets[0],end.steps.targets[1],end.steps.targets[2],0};uint8_t b[72];encode_scope(b,4242,500000,target);
  std::cout<<"SCOPE_CODEC_HEX ";for(auto x:b)std::cout<<std::hex<<std::setfill('0')<<std::setw(2)<<unsigned(x);
  std::cout<<"\nSCOPE_PURE_UNIT_PASS fixed targets and seven invalid inputs; no device open\n";return 0;
 }catch(const std::exception&e){std::cerr<<"SCOPE_PURE_UNIT_FAIL "<<e.what()<<'\n';return 1;}
}
