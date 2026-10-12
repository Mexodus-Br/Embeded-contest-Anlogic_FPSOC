"""Disabled integration candidate, derived from confirmed hardware profile."""
import argparse,json
from pathlib import Path
from prepare_ip import ROOT,profile
def render():
 p=profile();a=p['address'];i=p['irq']
 return f'''/* Generated DMA hardware candidate. BSP must review its compiled driver
 * binding, clock names, ranges and two IRQ mappings before enabling.
 * Simple mode: deliberately NO anlogic,include-sg (TD template adds it).
 */
/ {{
    dma_loop_clock: dma-loop-clock {{
        compatible = "fixed-clock";
        #clock-cells = <0>;
        clock-frequency = <{p['clock_hz']}>;
    }};
}};
&soc {{
    pl_dma_loop: dma@{a['base']:x} {{
        compatible = "anlogic,axi-dma";
        reg = <0x0 0x{a['base']:08x} 0x0 0x{a['size']:x}>;
        #dma-cells = <1>;
        #address-cells = <1>;
        #size-cells = <0>;
        anlogic,addrwidth = <{p['memory_address_width']}>;
        anlogic,sg-length-width = <{p['parameters']['AL_SG_LENGTH_WIDTH']}>;
        clocks = <&dma_loop_clock>, <&dma_loop_clock>, <&dma_loop_clock>, <&dma_loop_clock>;
        clock-names = "s_axi_lite_aclk", "m_axi_mm2s_aclk", "m_axi_s2mm_aclk", "m_axi_sg_aclk";
        status = "disabled";
        dma-channel@0 {{
            compatible = "anlogic,axi-dma-mm2s-channel";
            reg = <0>;
            interrupt-parent = <&gic>;
            interrupts = <0 {i['mm2s_spi']} 4>;
            dma-channels = <1>;
            anlogic,datawidth = <{p['stream_width']}>;
            anlogic,include-dre;
        }};
        dma-channel@30 {{
            compatible = "anlogic,axi-dma-s2mm-channel";
            reg = <0x30>;
            interrupt-parent = <&gic>;
            interrupts = <0 {i['s2mm_spi']} 4>;
            dma-channels = <1>;
            anlogic,datawidth = <{p['stream_width']}>;
            anlogic,include-dre;
        }};
    }};
}};
'''
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args();p=ROOT/'configs/dma-candidate.dtsi'
 if a.check:
  if p.read_text()!=render():raise SystemExit('stale DTS candidate')
 else:p.parent.mkdir(exist_ok=True);p.write_text(render())
