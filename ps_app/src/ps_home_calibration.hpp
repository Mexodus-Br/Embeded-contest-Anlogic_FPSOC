#pragma once
#include "../../pl_safety/generated/home_calibration_policy.h"
#include <cstdint>
namespace ps {
inline bool home_config_matches(const uint32_t *words,bool valid){
    const uint32_t expected[8]=HC_CONFIG_WORDS;
    if(!valid||!HC_APPROVED)return false;
    for(unsigned i=0;i<8;i++)if(words[i]!=expected[i])return false;
    return true;
}
}
