// Extracted expressions from baseline/robotGeometry.cpp and RampsStepper.cpp.
// Supplied original files contain no copyright or license headers; see NOTICE.md.
#include "model.hpp"
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <stdexcept>
#include <type_traits>

namespace golden {
Config read_config(const std::string& path) {
    Config c;
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open config: "+path);
    std::map<std::string,double> values;
    std::string line;
    auto trim=[](std::string s) {
        auto a=s.find_first_not_of(" \t\r\n");
        return a==std::string::npos ? std::string() : s.substr(a,s.find_last_not_of(" \t\r\n")-a+1);
    };
    while (std::getline(in,line)) {
        line=trim(line.substr(0,line.find('#')));
        if (line.empty()) continue;
        auto eq=line.find('=');
        if (eq==std::string::npos) throw std::runtime_error("expected key=value");
        auto key=trim(line.substr(0,eq)), val=trim(line.substr(eq+1));
        size_t used=0;
        double n=std::stod(val,&used);
        if (used!=val.size() || !std::isfinite(n) || !values.emplace(key,n).second)
            throw std::runtime_error("invalid/duplicate config key: "+key);
    }
    auto real=[&](const char* key, auto& dest) {
        auto it=values.find(key);
        if (it!=values.end()) {
            using T=std::decay_t<decltype(dest)>;
            if (std::abs(it->second)>std::numeric_limits<T>::max()) throw std::runtime_error("config float overflow");
            dest=static_cast<T>(it->second); values.erase(it);
        }
        if (!std::isfinite(dest)) throw std::runtime_error("config float overflow");
    };
    auto integer=[&](const char* key, int& dest) {
        auto it=values.find(key);
        if (it==values.end()) return;
        double n=it->second;
        if (n!=std::trunc(n) || n<std::numeric_limits<int>::min() || n>std::numeric_limits<int>::max())
            throw std::runtime_error("config integer out of range");
        dest=static_cast<int>(n); values.erase(it);
    };
    real("base_radius_mm",c.R); real("effector_radius_mm",c.r);
    real("upper_length_mm",c.L); real("lower_length_mm",c.l);
    real("main_gear_teeth",c.main_teeth); real("motor_gear_teeth",c.motor_teeth);
    integer("microsteps",c.microsteps); integer("steps_per_rev",c.steps_per_rev);
    integer("target_min",c.target_min); integer("target_max",c.target_max);
    real("limit_x_mm",c.limit_x); real("limit_y_mm",c.limit_y); real("limit_z_min_mm",c.limit_z_min);
    const char* offsets[]={"angle_offset_x_rad","angle_offset_y_rad","angle_offset_z_rad"};
    const char* steps[]={"step_offset_x","step_offset_y","step_offset_z"};
    const char* inverses[]={"inverse_x","inverse_y","inverse_z"};
    for (int i=0;i<3;++i) {
        real(offsets[i],c.angle_offset[i]); integer(steps[i],c.step_offset[i]);
        int inv=c.inverse[i]; integer(inverses[i],inv);
        if (inv!=0 && inv!=1) throw std::runtime_error("inverse must be 0 or 1");
        c.inverse[i]=inv;
    }
    if (!values.empty()) throw std::runtime_error("unknown config key: "+values.begin()->first);
    if (c.R<0 || c.r<0 || c.L<=0 || c.l<=0 || c.main_teeth<=0 || c.motor_teeth<=0 ||
        c.microsteps<=0 || c.steps_per_rev<=0 || c.target_min>c.target_max || c.limit_x<0 || c.limit_y<0 ||
        static_cast<long long>(c.microsteps)*c.steps_per_rev>std::numeric_limits<int>::max())
        throw std::runtime_error("invalid parameter domain");
    return c;
}

IK xyz_to_angles(float xmm,float ymm,float zmm,const Config& c) {
    const float R=c.R, r=c.r, L=c.L, l=c.l;
    IK out;
    auto store=[&](int i,double K,double M,double N) {
        const double d=M*M-4*K*N;
        out.K[i]=K; out.discriminant[i]=d;
        // Preserve original branch and expression even for invalid values.
        out.angles[i]=(pi/2)-2*atan((-M-sqrt(d))/(2*K));
        if (!std::isfinite(xmm)||!std::isfinite(ymm)||!std::isfinite(zmm)) out.reasons[i]="nonfinite_input";
        else if (!std::isfinite(K)||!std::isfinite(M)||!std::isfinite(N)||!std::isfinite(d)) out.reasons[i]="nonfinite_intermediate";
        else if (d<0) out.reasons[i]="negative_discriminant";
        else if (K==0) out.reasons[i]="zero_denominator";
        else if (!std::isfinite(out.angles[i])) out.reasons[i]="nonfinite_angle";
        if (!out.reasons[i].empty()) out.valid=false;
    };
    // Keep original float subexpressions, double sqrt(3), expression order.
    double K,M,N;
    K=((-(xmm*xmm+ymm*ymm+zmm*zmm)+(ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L+2*zmm);
    M=-2*(2*(R-r)-ymm-sqrt(3)*xmm);
    N=((-(xmm*xmm+ymm*ymm+zmm*zmm)+(ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L-2*zmm);
    store(2,K,M,N);
    K=((-(xmm*xmm+ymm*ymm+zmm*zmm)-(-ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L+2*zmm);
    M=-2*(2*(R-r)-ymm+sqrt(3)*xmm);
    N=((-(xmm*xmm+ymm*ymm+zmm*zmm)-(-ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L-2*zmm);
    store(1,K,M,N);
    K=((-(xmm*xmm+ymm*ymm+zmm*zmm)-2*ymm*(R-r)-(R-r)*(R-r)-L*L+l*l)/(2*L)+zmm);
    M=-2*(R-r+ymm);
    N=((-(xmm*xmm+ymm*ymm+zmm*zmm)-2*ymm*(R-r)-(R-r)*(R-r)-L*L+l*l)/(2*L)-zmm);
    store(0,K,M,N);
    return out;
}

Steps angles_to_steps(const std::array<float,3>& angles,const Config& c) {
    Steps out;
    // Firmware: ratio passed as float; stepsPerRev is integer; division by PI then float assignment.
    const double raw_ratio=c.main_teeth/c.motor_teeth;
    const float ratio=std::isfinite(raw_ratio) && raw_ratio<=std::numeric_limits<float>::max()
        ? static_cast<float>(raw_ratio) : std::numeric_limits<float>::infinity();
    const int steps_per_rev=c.microsteps*c.steps_per_rev;
    out.factor=ratio*steps_per_rev/2/pi;
    for (int i=0;i<3;++i) {
        // Zero defaults preserve original multiply; extensions explicitly documented.
        const float a=c.angle_offset[i]==0 ? angles[i] : angles[i]+c.angle_offset[i];
        out.unrounded[i]=a*out.factor;
        if (!std::isfinite(angles[i]) || !std::isfinite(out.unrounded[i])) out.reasons[i]="nonfinite_step_input";
        else {
            const double t=std::trunc(static_cast<double>(out.unrounded[i]));
            // Check firmware cast domain before casting; original out-of-range cast is undefined.
            const double target=t+c.step_offset[i];
            if (t<std::numeric_limits<int>::min() || t>std::numeric_limits<int>::max() ||
                target<c.target_min || target>c.target_max) out.reasons[i]="step_range_exceeded";
            else out.targets[i]=static_cast<int>(target);
        }
        if (!out.reasons[i].empty()) out.valid=false;
    }
    return out;
}
bool firmware_box_allowed(float x,float y,float z,const Config& c) {
    return std::abs(x)<=c.limit_x && std::abs(y)<=c.limit_y && z>=c.limit_z_min;
}
}
