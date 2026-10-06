#include "model.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

static float number(const std::string& s) {
    size_t used=0;
    // stod permits large inputs to reach the explicit float-overflow diagnostics.
    double n=std::stod(s,&used);
    if (used!=s.size()) throw std::runtime_error("invalid number");
    if (std::isfinite(n) && std::abs(n)>std::numeric_limits<float>::max())
        return std::copysign(std::numeric_limits<float>::infinity(),n);
    return static_cast<float>(n);
}
static void num(double n) { if(std::isfinite(n)) std::cout<<n; else std::cout<<"null"; }
template<class T> static void array(const T& a) {
    std::cout<<'['; for(int i=0;i<3;++i){if(i)std::cout<<',';num(a[i]);} std::cout<<']';
}
static void reasons(const std::array<std::string,3>& a) {
    std::cout<<'[';for(int i=0;i<3;++i){if(i)std::cout<<',';std::cout<<'"'<<a[i]<<'"';}std::cout<<']';
}
static bool run(const std::vector<std::string>& args,const golden::Config& c) {
    if(args.size()!=4 || (args[0]!="xyz" && args[0]!="angles")) throw std::runtime_error("expected xyz|angles and three numbers");
    std::array<float,3> input{number(args[1]),number(args[2]),number(args[3])};
    golden::IK ik;
    if(args[0]=="xyz") ik=golden::xyz_to_angles(input[0],input[1],input[2],c);
    else {ik.angles=input;for(int i=0;i<3;++i)if(!std::isfinite(input[i])){ik.valid=false;ik.reasons[i]="nonfinite_input";}}
    auto steps=golden::angles_to_steps(ik.angles,c);
    bool valid=ik.valid&&steps.valid;
    std::cout<<"{\"numeric_profile\":\"host_float32_double64\",\"axis_order\":[\"X_high\",\"Y_low\",\"Z_rot\"],\"angle_unit\":\"rad\",\"input\":";
    array(input);std::cout<<",\"angles_rad\":";array(ik.angles);
    std::cout<<",\"ik_valid\":"<<(ik.valid?"true":"false")<<",\"ik_reasons\":";reasons(ik.reasons);
    std::cout<<",\"K\":";array(ik.K);std::cout<<",\"discriminant\":";array(ik.discriminant);
    std::cout<<",\"steps_valid\":"<<(steps.valid?"true":"false")<<",\"step_reasons\":";reasons(steps.reasons);
    std::cout<<",\"absolute_steps\":";
    if(valid) array(steps.targets); else std::cout<<"null";
    std::cout<<",\"unrounded_steps\":";array(steps.unrounded);
    std::cout<<",\"rad_to_step_factor\":";num(steps.factor);
    std::cout<<",\"valid\":"<<(valid?"true":"false");
    if(args[0]=="xyz")std::cout<<",\"firmware_box_allowed\":"<<(golden::firmware_box_allowed(input[0],input[1],input[2],c)?"true":"false");
    std::cout<<"}\n";
    return valid;
}
int main(int argc,char** argv) {
    try {
        static_assert(sizeof(float)==4 && sizeof(double)==8,"unsupported numeric profile");
        std::cout<<std::setprecision(17);
        golden::Config c;std::vector<std::string> args;bool batch=false;
        for(int i=1;i<argc;++i) {
            std::string a=argv[i];
            if(a=="--config") {if(++i==argc)throw std::runtime_error("missing config");c=golden::read_config(argv[i]);}
            else if(a=="--batch")batch=true;
            else args.push_back(a);
        }
        if(batch) {
            if(!args.empty())throw std::runtime_error("batch takes records on stdin");
            std::string line;
            while(std::getline(std::cin,line)) {
                if(line.empty()||line[0]=='#')continue;
                std::istringstream in(line);std::vector<std::string> record;std::string token;
                while(in>>token)record.push_back(token);
                run(record,c);
            }
            return 0; // Record validity is carried in JSON; malformed syntax exits 2.
        }
        return run(args,c)?0:1;
    } catch(const std::exception& e) {std::cerr<<"error: "<<e.what()<<'\n';return 2;}
}
