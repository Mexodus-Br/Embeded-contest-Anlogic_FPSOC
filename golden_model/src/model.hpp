#pragma once
#include <array>
#include <string>

namespace golden {
constexpr double pi = 3.1415926535897932384626433832795;
struct Config {
    float R=83.7f, r=30.4f, L=150.f, l=280.f;
    double main_teeth=4.5, motor_teeth=1;
    int microsteps=16, steps_per_rev=200;
    std::array<float,3> angle_offset{};
    std::array<int,3> step_offset{};
    std::array<bool,3> inverse{true,true,true};
    int target_min=-32768, target_max=32767;
    float limit_x=110, limit_y=110, limit_z_min=-300;
};
Config read_config(const std::string& path);
struct IK {
    // Motor order X(high), Y(low), Z(rot), radians.
    std::array<float,3> angles{};
    std::array<double,3> K{}, discriminant{};
    std::array<std::string,3> reasons{};
    bool valid=true;
};
struct Steps {
    std::array<int,3> targets{};
    std::array<float,3> unrounded{};
    std::array<std::string,3> reasons{};
    float factor=0;
    bool valid=true;
};
IK xyz_to_angles(float x, float y, float z, const Config& c);
Steps angles_to_steps(const std::array<float,3>& angles, const Config& c);
bool firmware_box_allowed(float x, float y, float z, const Config& c);
}
