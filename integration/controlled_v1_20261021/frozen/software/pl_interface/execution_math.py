"""Conservative draft point feasibility, using Python exact integers.

No pulse timing parameters here are driver specifications.
"""
U64=(1<<64)-1
I64_MIN=-(1<<63)
I64_MAX=(1<<63)-1

def feasibility(target,position,duration_tick,high,low,guard,max_rate):
    if not all(isinstance(x,int) for x in [target,position,duration_tick,high,low,guard,max_rate]):raise ValueError('integer units required')
    if not I64_MIN<=target<=I64_MAX or not I64_MIN<=position<=I64_MAX:raise ValueError('signed64 range')
    if not 0<duration_tick<=U64 or high<=0 or low<=0 or guard<0 or max_rate<=0:raise ValueError('unconfigured/range')
    cycles=duration_tick*100  # confirmed 1MHz timestamp / 100MHz execution domain
    if cycles>U64:raise ValueError('duration conversion overflow')
    delta=target-position; n=abs(delta)
    if n==0:return dict(delta=0,pulses=0,cycles=cycles,slot_min=None)
    budget=cycles-guard
    if budget<=0 or budget//n<high+low or n*100_000_000>max_rate*budget:raise ValueError('unexecutable')
    return dict(delta=delta,pulses=n,cycles=cycles,slot_min=budget//n)
