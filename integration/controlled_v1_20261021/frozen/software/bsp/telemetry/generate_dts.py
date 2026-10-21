"""BSP reviewed binding generated from canonical addresses/IRQs, disabled preview."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2];s=json.loads((R/'pl_interface/schema.json').read_text(encoding='utf-8'))
g=s['rs485_gp_profiles']['gp_rs485_v1'];t=s['rs485_telemetry']
# Freeze keys are checked explicitly rather than assuming a legacy copy.
d=t['dma'];D=R/'bsp/telemetry'
text=f'''/* Generated from the canonical schema. Disabled preview: no boot image.
 * Enable only after full hardware/HPF/FSBL/GIC and reset-drain qualification.
 */
&soc {{
    rs485_dma: dma@{d['base']:x} {{
        compatible = "anlogic,axi-dma";
        reg = <0 0x{d['base']:x} 0 0x{d['size']:x}>;
        #dma-cells = <1>; #address-cells = <1>; #size-cells = <0>;
        anlogic,addrwidth = <{d['parameters']['AL_M_AXI_S2MM_ADDR_WIDTH']}>;
        anlogic,sg-length-width = <{d['parameters']['AL_SG_LENGTH_WIDTH']}>;
        bsp,telemetry-exclusive-controller;
        clocks = <&dma_loop_clock>, <&dma_loop_clock>;
        clock-names = "s_axi_lite_aclk", "m_axi_s2mm_aclk";
        status = "disabled";
        dma-channel@30 {{
            compatible = "anlogic,axi-dma-s2mm-channel";
            reg = <0x30>; interrupt-parent = <&gic>;
            interrupts = <0 {d['irq_spi']} 4>;
            dma-channels = <1>;
            anlogic,datawidth = <{d['parameters']['AL_S_AXIS_S2MM_TDATA_WIDTH']}>;
            anlogic,include-dre;
        }};
    }};
    rs485_control: rs485-control@{g['base']:x} {{
        compatible = "bsp,rs485-telemetry-v1";
        reg = <0 0x{g['base']:x} 0 0x{g['size']:x}>, <0 0x{t['base']:x} 0 0x{t['size']:x}>;
        reg-names = "collector", "cache-transport";
        interrupt-parent = <&gic>;
        interrupts = <0 {g['irq_spi']} 4>, <0 {t['irq_spi']} 4>;
        interrupt-names = "collector", "cache-transport";
        dmas = <&rs485_dma 1>; dma-names = "telemetry";
        status = "disabled";
        /* Deliberately no bsp,validated-hp1-reset-drain yet. */
    }};
}};
'''
(D/'board.dtsi').write_bytes(text.encode())
print('Generated independent S2MM-only binding; disabled, no validated drain claim')
