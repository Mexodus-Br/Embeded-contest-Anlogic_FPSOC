// Independent executable compiled against byte-identical baseline sources.
// Never calls golden_model/src functions; avoids undefined integer casts.
#include "robotGeometry.h"
#include "RampsStepper.h"
#include "config.h"
#include <Arduino.h>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
static float input_float(const std::string& s) {
    double n=std::stod(s);
    if(std::isfinite(n)&&std::abs(n)>std::numeric_limits<float>::max())
        return std::copysign(std::numeric_limits<float>::infinity(),n);
    return static_cast<float>(n);
}
int main() {
    std::cout<<std::setprecision(17);
    std::string mode,sx,sy,sz;
    while(std::cin>>mode>>sx>>sy>>sz) {
        float x=input_float(sx),y=input_float(sy),z=input_float(sz);
        RobotGeometry g(END_EFFECTOR_OFFSET,LOW_SHANK_LENGTH,HIGH_SHANK_LENGTH);
        std::array<float,3> a{x,y,z};
        if(mode=="xyz") {g.set(x,y,z);a={g.getHighRad(),g.getLowRad(),g.getRotRad()};}
        std::cout<<"{\"angles_rad\":[";
        for(int i=0;i<3;++i){if(i)std::cout<<',';if(std::isfinite(a[i]))std::cout<<a[i];else std::cout<<"null";}
        std::cout<<"],\"absolute_steps\":[";
        for(int i=0;i<3;++i) {
            if(i)std::cout<<',';
            const float ratio=MAIN_GEAR_TEETH/MOTOR_GEAR_TEETH;
            const float factor=ratio*(MICROSTEPS*STEPS_PER_REV)/2/PI;
            float raw=a[i]*factor;
            if(!std::isfinite(raw)||std::trunc(static_cast<double>(raw))<-32768||std::trunc(static_cast<double>(raw))>32767)std::cout<<"null";
            else {RampsStepper stepper(0,0,0,true);stepper.setPositionRad(a[i]);std::cout<<stepper.getPosition();}
        }
        std::cout<<"]}\n";
    }
}
