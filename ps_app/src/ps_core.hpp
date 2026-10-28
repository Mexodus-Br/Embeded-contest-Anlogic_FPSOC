#pragma once
#include "json.hpp"
#include <stdexcept>
#include <string>

namespace ps {
using Json = nlohmann::json;
struct Error : std::runtime_error {
    Json detail;
    Error(std::string code, std::string message, std::string field = "", Json context = Json::object());
};
void require(bool condition, const std::string &code, const std::string &message, const std::string &field = "");
uint64_t u64(const Json &value, const std::string &field);
int64_t i64(const Json &value, const std::string &field);
Json kinematics(const Json &request);
Json forward_kinematics(const Json &request);
Json plan(const Json &request);
Json motion_encode(const Json &request);
Json telemetry_decode(const Json &request);
Json dispatch(const Json &request);
}
