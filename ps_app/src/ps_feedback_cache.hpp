#pragma once
#include "ps_core.hpp"
extern "C" {
#include "pl_rs485/software/rs485_telem.h"
}
namespace ps {
inline uint64_t cache_pair(const uint32_t *w){return uint64_t(w[1])<<32|w[0];}
inline Json cache_raw(const uint32_t *w,bool seen){
    if(!seen)return nullptr;
    rs485_decoded d{};require(rs485_decode(w,&d)==RS485_SW_OK,"FEEDBACK_FORMAT","Invalid cached raw32 record");
    Json value=nullptr;
    if(d.data_valid){
        if(d.query==RS_QUERY_ENCODER)value={{"carry",std::to_string(d.encoder_carry)},{"value",d.encoder_value}};
        else if(d.query==RS_QUERY_PULSES||d.query==RS_QUERY_ERROR)value=std::to_string(d.signed_value);
        else value={{"raw",d.enum_raw},{"known",bool(d.enum_known)}};
    }
    return {{"address",d.address},{"query",d.query},{"status",d.status},{"data_valid",bool(d.data_valid)},
        {"request_us",std::to_string(d.request_us)},{"event_us",std::to_string(d.event_us)},
        {"sequence",std::to_string(d.sequence)},{"attempt",d.attempt},{"value",value}};
}
inline Json feedback_cache(const uint32_t *w,uint32_t id,uint64_t observed){
    Json rows=Json::array();
    for(unsigned i=0;i<RT_ROWS;i++){
        const auto *r=w+RT_SNAPSHOT_WORDS+i*(RT_ROW_STRIDE/4);auto flags=r[RT_ROW_FLAGS/4];
        bool seen=flags&RT_FLAG_VALID_SEEN,result=flags&RT_FLAG_RESULT_SEEN;
        bool stale=flags&(RT_FLAG_STALE|RT_FLAG_DISABLED);
        bool identity=r[RT_ROW_VALID_GENERATION/4]==w[RT_SNAP_GENERATION]&&r[RT_ROW_VALID_REVISION/4]==w[RT_SNAP_REVISION];
        auto valid_raw=cache_raw(r+RT_ROW_VALID_RAW/4,seen);
        const uint32_t queries[5]={RS_QUERY_ENCODER,RS_QUERY_PULSES,RS_QUERY_ERROR,RS_QUERY_ENABLE,RS_QUERY_PROTECT};
        if(seen)require(valid_raw.at("address")==((RS_SLAVE_ADDRS>>(8*(i/5)))&255)&&valid_raw.at("query")==queries[i%5],"FEEDBACK_IDENTITY","Cached raw does not match axis/query slot");
        rows.push_back({{"axis",i/5},{"slot",i%5},{"flags",flags},{"valid",seen&&!stale&&identity},
            {"stale",stale||!identity||!seen},{"last_valid",valid_raw},
            {"last_result",cache_raw(r+RT_ROW_RESULT_RAW/4,result)},
            {"valid_generation",std::to_string(r[RT_ROW_VALID_GENERATION/4])},{"valid_revision",std::to_string(r[RT_ROW_VALID_REVISION/4])},
            {"result_generation",std::to_string(r[RT_ROW_RESULT_GENERATION/4])},{"result_revision",std::to_string(r[RT_ROW_RESULT_REVISION/4])},
            {"age_us",seen?Json(std::to_string(cache_pair(r+RT_ROW_AGE/4))):Json()},
            {"stale_limit_us",std::to_string(cache_pair(r+RT_ROW_STALE_LIMIT/4))},
            {"raw_valid_words",std::vector<uint32_t>(r+RT_ROW_VALID_RAW/4,r+RT_ROW_VALID_RAW/4+8)},
            {"raw_result_words",std::vector<uint32_t>(r+RT_ROW_RESULT_RAW/4,r+RT_ROW_RESULT_RAW/4+8)}});
    }
    return {{"source","bsp_rs485_cache_snapshot"},{"snapshot_id",id},{"source_time_us",std::to_string(cache_pair(w+RT_SNAP_TIME_LO))},
        {"observed_monotonic_us",std::to_string(observed)},{"collector_generation",std::to_string(w[RT_SNAP_GENERATION])},
        {"revision",std::to_string(w[RT_SNAP_REVISION])},{"transport_generation",std::to_string(w[RT_SNAP_TRANSPORT_GEN])},
        {"asynchronous",true},{"history_complete",false},{"rows",rows}};
}
}
