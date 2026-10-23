"""Generate/check the versioned D1 host API schema. No third-party dependency."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'docs/ps-api.schema.json'
S={'type':'string'};N={'type':'number'};B={'type':'boolean'};I={'type':'integer','minimum':0}
def ref(name):return {'$ref':'#/$defs/'+name}
def nullable(value):return {'anyOf':[value,{'type':'null'}]}
def array(value,**kw):return {'type':'array','items':value,**kw}
def obj(properties,required=None,extra=False):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':extra}
def enum(*values):return {'enum':list(values)}
def const(value):return {'const':value}

def schema():
    d={}
    d['u64']={'type':'string','pattern':'^(0|[1-9][0-9]{0,19})$','description':'Canonical decimal uint64; service additionally checks <=18446744073709551615.'}
    d['i64']={'type':'string','pattern':'^(0|-?[1-9][0-9]{0,18})$','description':'Canonical decimal int64; service additionally checks signed bounds.'}
    d['id']={'type':'string','pattern':'^[A-Za-z0-9_-]{1,128}$'}
    d['xyz']=array(N,minItems=3,maxItems=3)
    d['steps']={'type':'array','prefixItems':[ref('i64'),ref('i64'),ref('i64'),const('0')],'items':False,'minItems':4,'maxItems':4}
    d['empty']=obj({})
    d['error']=obj({'code':S,'message':S,'field':nullable(S),'leg':nullable(I),'sample':nullable(I),'details':{'type':'object'}})
    d['failure']=obj({'ok':const(False),'error':ref('error')})
    d['point']=obj({'xyz_mm':ref('xyz'),'duration_us':nullable(ref('u64')),'dwell_us':ref('u64')},['xyz_mm'])
    d['repeat']={'oneOf':[obj({'mode':const('finite'),'count':ref('u64')}),obj({'mode':const('until_stopped')})]}
    d['task']=obj({'schema_version':const(1),'id':ref('id'),'parameter_version':ref('id'),'points':array(ref('point'),minItems=1,maxItems=1000),'repeat':ref('repeat')},['points'])
    d['box']=obj({'min':ref('xyz'),'max':ref('xyz')})
    fixture={'id':ref('id'),'speed_mm_s':N,'acceleration_mm_s2':N,'sample_us':ref('u64'),'max_sample_distance_mm':N,'max_samples':ref('u64'),'workspace':ref('box'),'forbidden_boxes':array(ref('box'),maxItems=128),'joint_min_deg':ref('xyz'),'joint_max_deg':ref('xyz'),'max_joint_step_deg':N,'pulse_interval_us':ref('u64'),'segment_guard_us':ref('u64'),'max_duration_us':ref('u64')}
    d['fixture']=obj(fixture)
    golden={k:N for k in ['base_radius_mm','effector_radius_mm','upper_length_mm','lower_length_mm','main_gear_teeth','motor_gear_teeth','microsteps','steps_per_rev']}
    golden.update(angle_offset_deg=ref('xyz'),step_offset=ref('xyz'),inverse=array(B,minItems=3,maxItems=3))
    d['golden']=obj(golden,[])
    d['parameters']=obj({'schema_version':const(1),'id':ref('id'),'fixture':ref('fixture'),'golden':ref('golden')})
    d['pose']=obj({'xyz_mm':ref('xyz'),'joint_deg':ref('xyz'),'steps':ref('steps'),'angles_rad':ref('xyz'),'raw_steps':ref('xyz'),'rad_to_step_factor':N,'axis_order':const(['high','low','rot','M4_disabled'])},['xyz_mm','joint_deg','steps'])
    d['position']=obj({'source':enum('simulation','unknown'),'model':const('sample_endpoint_simulation'),'valid':B,'stale':B,'position_id':ref('id'),'parameter_version':S,'xyz_mm':nullable(ref('xyz')),'joint_deg':nullable(ref('xyz')),'steps':nullable(ref('steps')),'updated_monotonic_us':ref('u64')})
    d['leg']=obj({'from_mm':ref('xyz'),'to_mm':ref('xyz'),'start_us':ref('u64'),'duration_us':ref('u64'),'acceleration_time_s':N,'peak_speed_mm_s':N,'profile':enum('trapezoid','triangle'),'specified_duration':B})
    d['preview_request']=obj({'schema_version':const(1),'parameter_version':ref('id'),'start_position_id':ref('id'),'task':ref('task')},['parameter_version','start_position_id','task'])
    d['preview']=obj({'executable':B,'target':ref('pose'),'fixture_id':ref('id'),'scope':const('host_fixture_only'),'start_position_id':ref('id'),'duration_us':ref('u64'),'legs':array(ref('leg')),'errors':array(ref('error')),'sample_count':I,'preview_id':ref('id'),'parameter_version':ref('id'),'state_version':ref('u64'),'expires_monotonic_us':ref('u64'),'repeat':ref('repeat'),'cycle_duration_us':nullable(ref('u64'))},['executable','target','errors','sample_count','preview_id','parameter_version','state_version','expires_monotonic_us','repeat','cycle_duration_us'])
    d['run_request']=obj({'boot_id':ref('id'),'client_command_id':ref('id'),'preview_id':ref('id'),'deadline_monotonic_us':ref('u64')})
    d['command']=obj({'boot_id':ref('id'),'command_id':ref('id'),'status':enum('received','validated','submitted','running','stopping','completed','cancelled','failed','unknown'),'request':ref('run_request'),'simulation':const(True),'task_id':S,'updated_monotonic_us':ref('u64'),'error':ref('error')},['boot_id','command_id','status','request','simulation','task_id'])
    d['backend']=obj({'kind':const('simulation'),'pulse_model':const('not_cycle_accurate'),'accepted_sequence':nullable(ref('u64')),'completed_sequence':nullable(ref('u64'))})
    d['log_stats']=obj({'last_event_id':ref('u64'),'queue_depth':I,'dropped':ref('u64'),'write_errors':ref('u64'),'last_flushed_event_id':ref('u64'),'retired':ref('u64'),'durability':S,'history_count':I})
    d['recovery']=obj({'boot_id':ref('id'),'command_id':ref('id'),'status':const('unknown'),'reason':S},['status','reason'])
    d['state']=obj({'simulation_injection_enabled':B,'schema_version':const(1),'boot_id':ref('id'),'simulation':const(True),'mode':enum('task','manual'),'phase':enum('idle','submitted','running','stopping','fault'),'state_version':ref('u64'),'monotonic_us':ref('u64'),'stop_epoch':ref('u64'),'handled_stop_epoch':ref('u64'),'parameter_version':ref('id'),'position':ref('position'),'target':nullable(ref('pose')),'active_command_id':nullable(ref('id')),'command':nullable(ref('command')),'recovery':nullable(ref('recovery')),'control_owned':B,'preview_id':nullable(ref('id')),'backend':ref('backend'),'logs':ref('log_stats'),'you_control':B},list({'schema_version','boot_id','simulation','mode','phase','state_version','monotonic_us','stop_epoch','handled_stop_epoch','parameter_version','position','target','active_command_id','command','recovery','control_owned','preview_id','backend','logs'}))
    d['auth_request']=obj({'token':S});d['auth']=obj({'csrf':S,'boot_id':ref('id')});d['logout']=obj({'logged_out':const(True)})
    d['control_request']=obj({'action':enum('acquire','release')});d['control']=obj({'you_control':B})
    d['mode']=obj({'mode':enum('task','manual')})
    d['stop']=obj({'status':const('received'),'stop_epoch':ref('u64'),'simulation':const(True)})
    d['cancel']=obj({'cancelled':const(True)})
    d['saved']=obj({'saved':const(True),'id':ref('id'),'executed':const(False)})
    d['ids']=obj({'ids':array(ref('id'))})
    d['boots']=obj({'boot_ids':array(ref('id')),'current_boot_id':ref('id'),'history_incomplete':const(True),'archive_errors':ref('u64'),'archive_retired':ref('u64')})
    d['teach']=obj({'point':ref('point'),'source':const('simulation'),'position_id':ref('id'),'parameter_version':ref('id')})
    d['jog_start']=obj({'boot_id':ref('id'),'jog_id':ref('id'),'axis':enum('x','y','z'),'sign':enum(-1,1),'speed_mm_s':N,'refresh_seq':const('0'),'stop_epoch':ref('u64'),'deadline_monotonic_us':ref('u64')})
    d['jog_refresh']=obj({'boot_id':ref('id'),'jog_id':ref('id'),'refresh_seq':ref('u64')})
    d['jog_started']=obj({'jog_id':ref('id'),'status':const('running'),'expires_in_us':const('350000')})
    d['jog_refreshed']=obj({'status':const('running')})
    d['inject']=obj({'kind':enum('reference_position','position_unknown','fault','stop_failure','clear_stop_failure','logs','log_burst'),'disk_failure':B,'pause_log_writer':B,'count':ref('u64')},['kind'])
    d['applied']=obj({'applied':const(True),'simulation':const(True)},['applied'])
    d['telem_record']=obj({**{k:ref('u64') for k in ['collector_generation','transport_generation','revision','completion_serial','sequence','request_us','event_us','payload']},**{k:I for k in ['address','query','status','attempt']},'data_valid':B,'kind':enum('encoder_carry_value','command_pulses','error_counts','enable','protect','unknown'),'value':{'anyOf':[{'type':'null'},ref('i64'),obj({'carry':ref('i64'),'value':I}),obj({'raw':I,'known':B})]},'raw_hex_le':{'type':'string','pattern':'^[0-9a-f]{128}$'}})
    d['telem_latest']=obj({'last_valid':nullable(ref('telem_record')),'last_result':ref('telem_record'),'observed_monotonic_us':ref('u64'),'stale':B,'source':const('frozen_fixture_replay'),'current_generation':B})
    d['telemetry']=obj({'simulation':const(True),'latest':{'type':'object','additionalProperties':ref('telem_latest')},'history':array(ref('telem_record')),'active_identity':nullable(obj({k:ref('u64') for k in ['collector_generation','transport_generation','revision']})),'stale':B,'missing_serials':ref('u64'),'xyz_feedback':{'type':'null'}})
    d['replayed']=obj({'frames':const(17),'simulation':const(True)})
    d['filter']=obj({'boot_id':ref('id'),'clock':const('monotonic'),'from_us':ref('u64'),'to_us':ref('u64'),'severity':enum('','info','warning','error'),'component':S,'command_id':S,'task_id':S},[])
    d['event']=obj({'schema_version':const(1),'boot_id':ref('id'),'event_id':ref('u64'),'monotonic_us':ref('u64'),'wall_time_valid':const(False),'wall_time':{'type':'null'},'severity':enum('info','warning','error'),'component':S,'command_id':nullable(ref('id')),'task_id':nullable(ref('id')),'event':S,'details':{'type':'object'},'simulation':const(True)})
    d['snapshot']=obj({'schema_version':const(1),'record_type':const('snapshot'),'snapshot_id':ref('id'),'boot_id':ref('id'),'filters':ref('filter'),'count':I,'upper_event_id':ref('u64'),'truncated':B,'gaps':B,'dropped':ref('u64'),'retired':ref('u64'),'write_errors':ref('u64'),'expires_monotonic_us':ref('u64'),'simulation':const(True),'durability':S})
    d['page']=obj({'metadata':ref('snapshot'),'events':array(ref('event')),'next_cursor':nullable(S)})
    d['snapshot']['properties']['lower_event_id']=nullable(ref('u64'));d['snapshot']['required'].append('lower_event_id')
    d['state']['required']=[k for k in d['state']['properties'] if k!='you_control']
    # Hardware mode keeps unavailable XYZ explicit and publishes measured counters separately.
    for name in ['state','command','stop','event','snapshot']:
        d[name]['properties']['simulation']=B
    d['position']['properties']['model']=enum('sample_endpoint_simulation','unknown')
    d['backend']={'oneOf':[d['backend'],obj({'kind':const('hardware'),'boot_id':ref('id'),'position_id':S,'command_id':S,'parameter_revision':S,'generation':ref('u64'),'phase':enum('unknown','idle','queued','running','stopping','stopped','fault','rejected','homing'),'error':S,'owner_id':ref('u64'),'cancel_epoch':ref('u64'),'observed_stop_epoch':ref('u64'),'accepted_sequence':nullable(ref('u64')),'completed_sequence':nullable(ref('u64')),'quarantine':B,'dma_owned':B})]}
    d['hardware_action']=obj({'action':enum('open','close','clear','home','recover'),'boot_id':ref('id')})
    d['hardware_queued']=obj({'status':const('queued'),'simulation':const(False)})
    d['hardware_telemetry']=obj({'simulation':const(False),'source':const('bsp_snapshot'),'observed_monotonic_us':ref('u64'),'source_time_us':ref('u64'),'transport_generation':ref('u64'),'command_position':obj({'source':const('pl_step_counter'),'position_id':S,'valid':B,'steps':array(ref('i64'),minItems=3,maxItems=3),'pulses':array(ref('u64'),minItems=3,maxItems=3)}),'xyz_estimate':{'type':'null'},'driver_feedback':{'type':'null'},'raw':{},'stale':B})
    d['telemetry']={'oneOf':[d['telemetry'],d['hardware_telemetry'],obj({'simulation':const(False),'source':const('unavailable'),'stale':const(True)})]}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:delta:ps:api:1','title':'PS shared simulation/hardware API v1','$comment':'Select a $defs entry using the endpoint mapping in ps-api.md. Numeric/geometry cross-field constraints remain authoritative in the C++ validator.','$defs':d}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    value=schema()
    if a.check:
        assert json.loads(PATH.read_text(encoding='utf-8'))==value,'Regenerate docs/ps-api.schema.json'
    else:PATH.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
