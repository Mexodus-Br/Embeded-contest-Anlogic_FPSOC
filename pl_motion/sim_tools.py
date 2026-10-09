"""Fail-fast Icarus invocation with a process-local Windows environment."""
import os
import shutil
import subprocess
from pathlib import Path


class Simulator:
    def __init__(self, build):
        self.build = Path(build).resolve()
        self.build.mkdir(parents=True, exist_ok=True)
        override = os.environ.get('PL_MOTION_IVERILOG_BIN')
        if override:
            local = Path(override)
            self.compiler = str(local / 'iverilog.exe')
            self.runtime = str(local / 'vvp.exe')
        else:
            self.compiler = shutil.which('iverilog')
            self.runtime = shutil.which('vvp')
        if not self.compiler or not self.runtime:
            raise RuntimeError('iverilog and vvp are required')
        self.env = os.environ.copy()
        if os.name == 'nt':
            system = Path(os.environ['SystemRoot'])
            self.env['PATH'] = os.pathsep.join([str(Path(self.compiler).parent),
                str(Path(self.runtime).parent), str(system / 'System32'), str(system)])
            self.env['TMP'] = self.env['TEMP'] = str(self.build)

    def run(self, args, cwd=None):
        p = subprocess.run(args, cwd=cwd, env=self.env, capture_output=True,
                           text=True, timeout=45)
        if p.returncode:
            hint = ''
            if os.name == 'nt' and p.returncode == 3221225477:
                hint = '\nWindows access violation: run this local simulation outside '
                hint += 'the Codex Windows sandbox (see pl_motion/VALIDATION.md). '
                hint += 'No automatic retry was performed.'
            raise RuntimeError(f'{args[0]} failed {p.returncode}:\n{p.stdout}{p.stderr}{hint}')
        return p.stdout + p.stderr

    def compile(self, sources, top, output, includes=(), extra=()):
        args = [self.compiler, '-g2005', '-Wall', '-s', top, '-o', str(output)]
        for inc in includes:
            args += ['-I', str(inc)]
        return self.run(args + list(extra) + [str(s) for s in sources])

    def simulate(self, output):
        return self.run([self.runtime, str(output)])
