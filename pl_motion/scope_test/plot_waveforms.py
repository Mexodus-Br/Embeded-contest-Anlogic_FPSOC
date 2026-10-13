"""Plot actual RTL edge records for scope comparison (not a physical capture)."""
import csv,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'pl_motion/build/scope_plot')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def main():
 p=ROOT/'pl_motion/build/scope_dma/observed_edges.csv'
 if not p.exists():p=OUT/'evidence/observed_edges.csv'
 rows=list(csv.DictReader(p.open()))
 fig,axs=plt.subplots(3,1,figsize=(12,9),constrained_layout=True)
 for axis in range(3):
  a=[int(x['relative_cycle'])/100000 for x in rows if x['phase']=='1' and x['axis']==str(axis) and x['signal']=='step' and x['value']=='1']
  axs[0].plot(a,[axis]*len(a),'|',markersize=16,label=f'A{axis}: {len(a)} rising edges')
 axs[0].set(xlim=(0,500),ylim=(-.5,2.5),xlabel='Time from point_start (ms)',ylabel='Axis',title='Outgoing point: 500ms duration, common-slot edges')
 axs[0].set_yticks([0,1,2]);axs[0].legend(loc='lower right');axs[0].grid(alpha=.2)
 for ax,phase,title in [(axs[1],'1','Outgoing first slot: three corresponding rises at 10.02us'),(axs[2],'3','In-flight STOP: full 5us high; EN falls later on explicit DISABLE')]:
  labels=[]
  for axis in range(3):
   for si,signal in enumerate(['step','dir','en']):
    index=axis*3+si;labels.append(f'A{axis} {signal.upper()}')
    a=[x for x in rows if x['phase']==phase and x['axis']==str(axis) and x['signal']==signal]
    initial=0 if signal=='step' else (1 if signal=='en' or axis!=2 else 0)
    times=[0];values=[initial]
    for x in a:
     t=int(x['relative_cycle'])/100
     if 0<=t<=35:times.append(t);values.append(int(x['value']))
    times.append(35);values.append(values[-1]);ax.step(times,[index+v*.65 for v in values],where='post',linewidth=1)
  ax.set(xlim=(0,35),ylim=(-.2,9),xlabel='Time from point_start (us)',title=title)
  ax.set_yticks(range(9),labels);ax.grid(axis='x',alpha=.2)
 fig.suptitle('RTL simulation of real motion outputs / J12 scope-test\n100MHz; H=5us, L>=5us; EN active high; no driver/motor measurement')
 fig.savefig(OUT/'scope_waveforms.png',dpi=160);fig.savefig(OUT/'scope_waveforms.svg');plt.close(fig)
 print('Scope comparison plots written')
if __name__=='__main__':main()
