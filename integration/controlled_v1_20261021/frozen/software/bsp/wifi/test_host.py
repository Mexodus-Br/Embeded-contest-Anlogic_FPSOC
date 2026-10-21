"""Host-only credential and service lifecycle regression; no network/device access."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wifi_configure', str(HERE/'configure.py'))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class Credentials(unittest.TestCase):
    def test_standard_psk_vector_and_no_plaintext(self):
        text = config.render('IEEE', 'password', 'TW')
        self.assertIn('f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e', text)
        self.assertNotIn('password', text)
        self.assertIn('ssid=49454545', text)

    def test_injection_is_data_and_length_is_bytes(self):
        text = config.render('a"\nnetwork={', '0123456789', 'TW')
        self.assertEqual(text.count('network={'), 1)
        for ssid, password, country in [('', '01234567', 'TW'), ('界'*11, '01234567', 'TW'), ('ok','short','TW'), ('ok','01234567','TW\nfoo=1')]:
            with self.assertRaises(ValueError):
                config.render(ssid, password, country)

@unittest.skipUnless(os.name == 'posix', 'service harness needs POSIX shell')
class Service(unittest.TestCase):
    def test_dhcp_hook_requires_wireless_and_supplied_mask(self):
        with tempfile.TemporaryDirectory(prefix='wifi-dhcp-test-') as directory:
            root = Path(directory)
            for name, text in {
                'ip':'printf "%s\\n" "$*" >> "$MOCK_ROOT/ip.log"',
                'iw':'[ "$2" = wlan99 ] && echo "type managed"',
            }.items():
                target = root/name
                target.write_text('#!/bin/sh\n'+text+'\n')
                target.chmod(0o755)
            env = dict(os.environ, PATH=str(root)+':'+os.environ['PATH'], MOCK_ROOT=str(root), interface='wlan99',ip='192.0.2.42',subnet='255.255.255.0',router='192.0.2.1 192.0.2.254')
            hook = ['/bin/sh',str(HERE/'udhcpc.sh'),'bound']
            self.assertEqual(subprocess.call(hook,env=env), 0)
            output = (root/'ip.log').read_text()
            self.assertIn('addr add 192.0.2.42/255.255.255.0 dev wlan99',output)
            self.assertIn('default via 192.0.2.1 dev wlan99 metric 600',output)
            self.assertNotIn('192.0.2.254',output)
            (root/'ip.log').unlink()
            env['interface']='eth0'
            self.assertNotEqual(subprocess.call(hook,env=env),0)
            self.assertFalse((root/'ip.log').exists())
            env['interface']='wlan99'
            del env['subnet']
            self.assertNotEqual(subprocess.call(hook,env=env,stderr=subprocess.DEVNULL),0)

    def test_async_start_auth_gate_reconnect_and_scoped_stop(self):
        with tempfile.TemporaryDirectory(prefix='wifi-service-test-') as directory:
            root = Path(directory)
            (root/'etc/wifi').mkdir(parents=True)
            (root/'run').mkdir()
            binpath = root/'bin'
            binpath.mkdir()
            for name in ('sta.sh','udhcpc.sh'):
                text = (HERE/name).read_text().replace('/etc/wifi', str(root/'etc/wifi')).replace('/run/wifi-sta', str(root/'run/wifi-sta'))
                text = text.replace('s.st_uid==0', 's.st_uid==os.geteuid()')
                target = binpath/('wifi-sta' if name == 'sta.sh' else 'wifi-udhcpc')
                target.write_text(text)
                target.chmod(0o755)
            state = root/'state'
            state.write_text('DISCONNECTED')
            scripts = {
                'id':'echo 0',
                'iw':'echo "type managed"',
                'ip':'echo "$*" >> "$MOCK_ROOT/ip.log"; case "$*" in *"addr show"*) echo "inet 192.0.2.2/24";; esac',
                'wpa_cli':'printf "wpa_state="; cat "$MOCK_ROOT/state"; echo',
                'wpa_supplicant':'while [ $# -gt 0 ]; do if [ "$1" = -P ]; then shift; pidfile=$1; fi; shift; done; sleep 120 & echo $! > "$pidfile"',
                'udhcpc':'while [ $# -gt 0 ]; do if [ "$1" = -p ]; then shift; pidfile=$1; fi; shift; done; echo $$ > "$pidfile"; exec -a udhcpc sleep 120',
            }
            # Preserve a matching cmdline for terminate() ownership checks.
            scripts['wpa_supplicant'] = 'while [ $# -gt 0 ]; do if [ "$1" = -P ]; then shift; pidfile=$1; fi; shift; done; "$MOCK_ROOT/bin/wpa-daemon" & echo $! > "$pidfile"'
            scripts['wpa-daemon'] = 'exec -a wpa_supplicant sleep 120'
            # exec -a is bash-specific; the mock daemon does not represent the board shell.
            for name, text in scripts.items():
                path = binpath/name
                path.write_text(('#!/bin/bash\n' if name in ('wpa-daemon','udhcpc') else '#!/bin/sh\n')+text+'\n')
                path.chmod(0o755)
            (root/'etc/wifi/wpa_supplicant.conf').write_text(config.render('IEEE','password','TW'))
            (root/'etc/wifi/wpa_supplicant.conf').chmod(0o600)
            env = dict(os.environ, PATH=str(binpath)+':'+os.environ['PATH'], MOCK_ROOT=str(root), WIFI_INTERFACE='wlan99')
            def run(*args, **kwargs):
                return subprocess.run([str(binpath/'wifi-sta')]+list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=15, **kwargs)
            try:
                (root/'etc/wifi/wpa_supplicant.conf').chmod(0o644)
                self.assertNotEqual(run('start').returncode, 0)
                (root/'etc/wifi/wpa_supplicant.conf').chmod(0o600)
                started = time.monotonic()
                self.assertEqual(run('start').returncode, 0)
                self.assertLess(time.monotonic()-started, 2)
                time.sleep(.3)
                self.assertNotEqual(run('autostart-on').returncode, 0)
                self.assertFalse((root/'etc/wifi/autostart').exists())
                state.write_text('COMPLETED')
                self.assertEqual(run('autostart-on').returncode, 0)
                self.assertTrue((root/'etc/wifi/autostart').exists())
                self.assertEqual(run('reconnect').returncode, 0)
                time.sleep(.3)
                output = run('status').stdout
                self.assertNotIn('password', output)
                self.assertNotIn('IEEE', output)
                self.assertEqual(run('stop').returncode, 0)
                self.assertFalse((root/'run/wifi-sta/worker.pid').exists())
                self.assertNotIn('dev eth', (root/'ip.log').read_text())
            finally:
                run('stop')

if __name__ == '__main__':
    unittest.main()
