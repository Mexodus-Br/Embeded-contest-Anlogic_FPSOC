"""Run real Verilog benches; a compiler crash/assertion/timeout is fatal."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim_tools import Simulator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--environment-check', action='store_true')
    args = parser.parse_args()
    build = ROOT / 'build'
    sim = Simulator(build)
    if args.environment_check:
        # Include the existing interface bench in the same isolated environment.
        sys.path.insert(0, str(ROOT.parent / 'pl_interface/tests'))
        import check_verilog
        check_verilog.main()
        source = build / 'probe.v'
        source.write_text('module probe; initial begin $display("PROBE_OK"); '
                          '$finish; end endmodule\n', encoding='ascii')
        for i in range(50):
            out = build / 'probe.vvp'
            sim.compile([source], 'probe', out)
            if 'PROBE_OK' not in sim.simulate(out):
                raise RuntimeError('probe did not execute')
        print('PASS environment: 50 compile/simulate runs, no retries/skips')
        return
    profiles = [dict(H=3,L=2,S=4,Q=7,E=5,OFF=3,P=8,POL=1),
                dict(H=1,L=1,S=0,Q=0,E=0,OFF=0,P=2,POL=0),
                dict(H=5,L=3,S=8,Q=20,E=9,OFF=6,P=10,POL=1)]
    for i, profile in enumerate(profiles):
        out = build / f'axis_{i}.vvp'
        extra = [f'-Ptb_axis_motion.{k}={v}' for k,v in profile.items()]
        diagnostics = sim.compile([ROOT/'rtl/axis_motion.v',
            ROOT/'tests/tb_axis_motion.v'], 'tb_axis_motion', out, extra=extra)
        if diagnostics.strip():
            print(diagnostics)
        result = sim.simulate(out)
        print(f'profile {i}: {profile}\n{result}', end='')
        if 'PASS axis' not in result:
            raise RuntimeError('missing self-check completion')
    out = build / 'contract.vvp'
    # Unconnected ports belong to configuration-only instances in this bench.
    sim.compile([ROOT/'rtl/axis_motion.v', ROOT/'tests/tb_contract.v'],
                'tb_contract', out)
    result = sim.simulate(out)
    print(result, end='')
    if 'PASS contract' not in result:
        raise RuntimeError('missing contract-check completion')


if __name__ == '__main__':
    main()
