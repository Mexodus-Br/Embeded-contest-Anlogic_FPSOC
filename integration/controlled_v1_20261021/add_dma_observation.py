"""Read-only observation on the existing RX owner, without opening/consuming it."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent
p=H/'frozen/software/bsp/telemetry/client/bsp_rs485.c'
s=p.read_text()
marker='static int probe(struct platform_device *p)'
assert s.count(marker)==1 and 'integration_state_show' not in s
code='''/* Read-only lifecycle observation; no open, cancel, consume or MMIO side effect. */
static ssize_t integration_state_show(struct device *dev,struct device_attribute *attr,char *buf)
{
 struct rs485_owner *m=dev_get_drvdata(dev);ssize_t n;
 mutex_lock(&m->life);
 n=sysfs_emit(buf,"{\\\"blocked\\\":%u,\\\"owned\\\":%u,\\\"quarantine\\\":%u,\\\"buffer_allocated\\\":%u,\\\"generation\\\":%u,\\\"packet_id\\\":%u,\\\"packet_bytes\\\":%u,\\\"actual\\\":%u,\\\"dma_status\\\":%u,\\\"dma_done\\\":%u,\\\"drain_validated\\\":%u}\\n",
 m->blocked,m->owned,m->quarantine,m->buffer!=NULL,m->generation,m->packet_id,m->bytes,m->actual,m->status,m->dma_done,m->drain_validated);
 mutex_unlock(&m->life);return n;
}
static DEVICE_ATTR_RO(integration_state);
static struct attribute *integration_attrs[]={&dev_attr_integration_state.attr,NULL};
static const struct attribute_group integration_group={.attrs=integration_attrs};
'''
s=s.replace(marker,code+marker)
old='platform_set_drvdata(p,m);return 0;'
assert s.count(old)==1
s=s.replace(old,'platform_set_drvdata(p,m);ret=devm_device_add_group(&p->dev,&integration_group);if(ret){misc_deregister(&m->misc);goto buffer;}return 0;')
p.write_bytes(s.encode())
metadata=H/'adaptations.json'
m=json.loads(metadata.read_text())
m['dma_observation']='Read-only lifecycle sysfs on existing RX owner; no open/consume/cancel/allocate or new controller entry'
metadata.write_text(json.dumps(m,indent=2)+'\n')
print('Added read-only RX lifecycle observation; no new control entry')
