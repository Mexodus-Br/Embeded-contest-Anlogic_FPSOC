"""Read completed same-board route reports; compare both previous candidates."""
import argparse,hashlib,json,re
from pathlib import Path
E=Path(__file__).resolve().parent;O=E.parent;R=E.parents[2]
def paths(text):
 result=[]
 for p in re.split(r'(?=Slack\s*:\s*[-0-9.]+ns)',text):
  if not all(k in p for k in ['Begin Point','End Point','Data Path Delay']):continue
  one={}
  for key in ['Slack','Begin Point','End Point','Check Type','Process','Data Path Delay','Logic Level','Max Fanout']:
   m=re.search(r'^'+key+r'\s*:\s*([^\n]+)',p,re.M)
   if m:one[key]=m[1]
  result.append(one)
 return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();D=O/('top_'+a.tag)
 current=json.loads((D/'comparison.json').read_text(encoding='utf-8'));parent=json.loads((O/'top_r1/comparison.json').read_text(encoding='utf-8'))
 assert current['constraints_unchanged'] and current['wrapper_unchanged'] and current['timing_pass']
 summary={'tag':a.tag,'user_acceptance':'CANDIDATE_PENDING_REVIEW','baseline_7681c69':current['before'],'parent_49e8ac6':parent['after'],'round2':current['after'],
  'delta_vs_parent':{k:v['used']-parent['after'][k]['used'] for k,v in current['after'].items()},
  'delta_vs_baseline':current['delta_after_minus_before'],'stages':current['after_stages'],
  'timing_pass':current['timing_pass'],'signoff_pass':current['signoff_pass'],
  'parent_setup_hold_ns':[0.080,0.022],'check_timing':json.loads((D/'reports/review.json').read_text(encoding='utf-8'))['check_timing'],
  'critical_warnings':json.loads((D/'reports/review.json').read_text(encoding='utf-8'))['critical_warnings']}
 text=(D/'reports/gp_route.timing').read_text(encoding='utf-8');summary['reported_paths']=paths(text)
 log=(D/'reports/build_gp.log').read_text(encoding='utf-8')
 summary['congestion']=[x for x in log.splitlines() if any(s in x for s in ['most congested 1%','top1  =','peak congestion','Over-util','initial overflow','Path[overflow','congo greater'])]
 def routing_metrics(t):
  diagnostic=re.search(r'([^\n]*most congested 1% tile average routing util is ([0-9.]+))',t)
  detail=re.search(r'Iter\. 1:.*?rr_path\[\s*(\d+)\]; Path\[overflow =\s*(\d+)',t)
  return {'local_congestion_diagnostic':diagnostic[1].strip(),'most_congested_1pct_avg_util':float(diagnostic[2]),'detail_routes':int(detail[1]),'initial_detail_overflow':int(detail[2]),'final_wire_length':int(re.findall(r'\|\s*Wire length\s*\|\s*(\d+)',t)[-1])}
 summary['routing_comparison']={'parent':routing_metrics((O/'top_r1/reports/build_gp.log').read_text(encoding='utf-8')),'round2':routing_metrics(log)}
 probe=E/'timing_probe'
 summary['targeted_route_paths']={}
 for name in ['collector_missed','collector_prefetch_pins','collector_scheduled','gp_snapshot_decode','gp_snapshot_capture','gp_snapshot_capture_pins','replay']:
  ps=paths((probe/(name+'.timing')).read_text(encoding='utf-8'))
  setup_paths=sorted((p for p in ps if p.get('Check Type')=='setup'),key=lambda p:float(p['Slack'].removesuffix('ns')))
  assert setup_paths,name
  summary['targeted_route_paths'][name]=setup_paths[:3]
 assert summary['targeted_route_paths']['replay'][0]['Slack']=='0.305ns'
 area=(D/'reports/gp_route.area').read_text(encoding='utf-8')
 def fanouts(t):
  t=t.split('DataNet Average Fanout:')[1]
  bins=dict((k,int(v)) for k,v in re.findall(r'#\d+\s+(\S+)\s+(\d+)',t))
  bins.setdefault('>500',0)
  return {'bins':bins,'average':float(re.search(r'Average\s+([0-9.]+)',t)[1])}
 summary['data_net_fanout']={'parent':fanouts((O/'top_r1/reports/gp_route.area').read_text(encoding='utf-8')),'round2':fanouts(area)}
 summary['retained_storage']=[x for x in area.splitlines() if any('|'+n in x.replace(' ','') for n in ['rs485_latest_cache','rs485_telemetry','record_fifo'])]
 assert summary['delta_vs_parent']['slice']<0,'No further top-level Slice saving'
 assert not summary['signoff_pass'],'Independent release blockers must remain explicit'
 (E/'TOP_COMPARISON.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
 setup=sorted((p for p in summary['reported_paths'] if p.get('Check Type')=='setup'),key=lambda p:float(p['Slack'].removesuffix('ns')))
 print(json.dumps({**{k:summary[k] for k in ['round2','delta_vs_parent','stages']},'worst_setup_paths':setup[:2]},indent=2))
 # The detailed timing list is a bounded worst-path report, not an exhaustive
 # per-net fanout inventory. Do not call absence from it a measured fanout of 0.
 lines=['\n## 本轮完整实际顶层结果\n','|项目|原基线7681c69|上一轮候选49e8ac6|本轮|本轮相对上一轮|','|---|---:|---:|---:|---:|']
 for key,label in [('lut6','LUT6'),('slice','Slice'),('reg','Slice寄存器'),('eram','ERAM'),('dsp','DSP')]:
  lines.append(f"|{label}|{current['before'][key]['used']}|{parent['after'][key]['used']}|{current['after'][key]['used']}|{summary['delta_vs_parent'][key]:+d}|")
 saved=-summary['delta_vs_parent']['slice'];total_saved=-summary['delta_vs_baseline']['slice']
 timing=current['after_stages']['route']
 lines += [f"\n本轮再释放{saved} Slice（{saved*100/52480:.4f}个百分点）；相对原基线累计释放{total_saved}（{total_saved*100/52480:.4f}个百分点）。当前Slice占用{current['after']['slice']['percent']:.4f}%，剩余{current['after']['slice']['remaining']}。",
  f"最终100MHz route setup {timing['setup_wns_ns']:+.3f}ns、hold {timing['hold_wns_ns']:+.3f}ns，双corner，STA coverage {timing['coverage']}。所有阶段明细见TOP_COMPARISON.json。",
  '\n报告列出的最差setup路径（最多展示前十项，未列出不能解释为对应扇出已归零）：']
 for p in setup[:10]:lines.append(f"- {p['Slack']}：{p['Begin Point']} → {p['End Point']}；{p.get('Data Path Delay')}；最大fanout {p.get('Max Fanout')}。")
 lines += ['\n完整拥塞原文（各阶段不能混为一个指标）：']+['- '+x for x in summary['congestion']]
 lines += ['\n### 定点路径复核与剩余热点\n',
  '从同一gp_route.db只读恢复、重新载入原约束并执行final STA；replay最差setup仍为+0.305ns，未重新布局布线。定点集合及原始路径见timing_probe/targeted*.tcl与*.timing。']
 for name in ['collector_missed','collector_prefetch_pins','collector_scheduled','gp_snapshot_decode','gp_snapshot_capture','gp_snapshot_capture_pins']:
  p=summary['targeted_route_paths'][name][0]
  lines.append(f"- {name}最差setup {p['Slack']}：{p['Begin Point']} → {p['End Point']}；{p['Data Path Delay']}；该路径最大fanout {p['Max Fanout']}。")
 lines += ['\n原collector动态选择→饱和统计写回的单拍组合链已经拆分；当前按整个missed相关寄存器集合核对，不把综合重命名后的路径称作原物理路径一一对应。GP分别核对从aw_snapshot出发、逻辑快照选择集合、以及snapshot命名Slice的CE引脚集合。物理Slice会混合打包其他逻辑：prefetch命名Slice的输入查询终止于max_late，snapshot命名Slice的CE路径来自telemetry控制；这些是覆盖共用Slice的保守集合，不能把物理实例名当作逻辑功能或宣称精确的一一对应。各原始集合、实际起终点均保留，上列fanout也不代表整个设计的最大扇出。',
  '\n全局剩余最差路径为HP0 RVALID至a2_dir输出寄存器CE，data 8.910ns（net 6.503ns，73%），最大fanout40；board_100m域内最差为运动executor disabling至a2_en CE，setup+0.497ns，net 7.736ns。运动/HP0路径仍有较多布线延迟，本轮没有改动运动算法或DMA架构，+0.305ns不能证明后续安全/HOME一定放得下。',
  '\n同一布局阶段最拥塞1% tile平均利用率94.925676%→83.594595%，诊断由Local congestion issue exists变为No local congestion issue；最终wire length 17009600→11810720（下降30.56%），detail routes 198878→165985，最终overflow为0。不能将这些不同指标合并成“所有局部利用率低于100%”。',
  '\nroute.area的DataNet扇出分布：51–100负载网178→136，101–500负载网49→8，>500负载网1→0。平均扇出2.15→2.24，因低扇出网数量同时减少，不能宣称平均扇出也下降。这是工具DataNet分类，不能当作全网扇出上限：CE控制仍有3392负载，telemetry/regs/mux147_syn_2[1023]单段布线3.557ns；相关物理CE路径setup+2.472ns。复位网也仍有fanout1523，逻辑prefetch查询最差recovery+4.034ns，原始collector_prefetch.timing保留。高扇出尚未全部消除，后续可继续审查控制分发，但本轮不再未经验证地改变实现。',
  '\n最终顶层cache实际映射12ERAM/1DSP，独立组件映射14ERAM/1DSP；真实输入的已知常量位引起差异，收益只使用顶层总量。两个RAM各64×256bit、每行三槽，共保留15行good/last完整raw与冻结指针；FIFO256、原GP诊断FIFO及全部可观察字段由差分/真实IP测试和层级映射共同核对。',
  '\nround2_dsp.rpt复核新增cache物理DSP mult0_syn_58（[85,96]），其内部辅助单元mult0_syn_59不是第二个物理DSP；planner仍4个、collector仍1个，全顶层共6个。上一轮清除的五组period×3共10个DSP仍未恢复，本轮新增的是元数据变量索引相关乘法，故相对原基线净少9个DSP。原10个实例核对见../path_dsp_verify_20261015/VERIFICATION.md。dsp_packing.log还证明snapshot_reg[14841]的.oqa为GP snapshot[16][25]，.oqb为telemetry/cache/frozen[416]，.cea/.ceb控制不同；3392扇出属于后者，不能误称GP快照自身新增3392扇出。',
  '\n100MHz setup余量较上一轮增加0.225ns，hold余量减少0.002ns，均无违例；所有check_timing原问题保持，包括rs485_rx输入delay缺失和rs485_tx/de两个输出delay缺失、原有dummy node报告，未通过新增例外或放宽约束解决。用户验收状态保持CANDIDATE_PENDING_USER_REVIEW，独立发布门禁仍未通过。']
 doc=E/'ROUND2_HANDOFF.md';base=doc.read_text(encoding='utf-8').split('\n## 本轮完整实际顶层结果')[0]
 base=base.replace('## 待补完整顶层结果','## 完整报告原则').replace('须以完成的实际route报告补充','以下方完成的实际route报告为准')
 doc.write_text(base+'\n'+'\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__':main()
