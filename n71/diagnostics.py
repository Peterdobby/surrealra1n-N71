"""Capture private diagnostics from one already paired N71 iOS device."""

import json
from pathlib import Path
import shutil
import subprocess


def query(tool, args):
    try:
        result = subprocess.run([tool, *args], capture_output=True, text=True, check=True, timeout=8)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        raise ValueError(f'{tool} could not read the paired iOS device') from exc
    return result.stdout.strip()


def capture_command(command, output, timeout, *, stream=False):
    with output.open('xb') as stdout, output.with_suffix('.stderr').open('xb') as stderr:
        try:
            status = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            if stream:
                return 'window_elapsed' if output.stat().st_size else 'no_log_data'
            return 'timed_out'
    if status:
        return f'failed_exit_{status}'
    return 'completed' if not stream or output.stat().st_size else 'no_log_data'


def capture(output, seconds, target):
    for name in ('idevice_id', 'ideviceinfo', 'idevicesyslog', 'idevicecrashreport'):
        if not shutil.which(name):
            raise ValueError(f'collect-logs requires {name} on PATH')
    ids = query('idevice_id', ['-l']).splitlines()
    if len(ids) != 1 or not ids[0]:
        raise ValueError('collect-logs requires exactly one USB device')
    selector = ['-u', ids[0]]
    device = {key: query('ideviceinfo', [*selector, '-k', field])
              for key, field in (('product', 'ProductType'), ('board', 'HardwareModel'),
                                 ('version', 'ProductVersion'), ('build', 'BuildVersion'))}
    if device['product'] != target['product'] or device['board'].lower() != target['board']:
        raise ValueError('collect-logs requires a paired iPhone8,1 / N71AP running iOS')
    if not device['version'] or not device['build']:
        raise ValueError('paired iOS device did not report its OS version and build')
    output.mkdir(mode=0o700)
    crashes = output / 'crashes'
    crashes.mkdir(mode=0o700)
    args = ['idevicesyslog', *selector, '--no-colors']
    steps = {
        'process_snapshot': capture_command([*args, 'pidlist'], output / 'processes.log', 12),
        'syslog': capture_command([*args, '--exit'], output / 'syslog.log', seconds, stream=True),
        'crash_copy': capture_command(
            ['idevicecrashreport', *selector, '--keep', '--filter', 'CommCenter', str(crashes)],
            output / 'crash-copy.log', 30),
    }
    captured = (steps['process_snapshot'] == steps['crash_copy'] == 'completed'
                and steps['syslog'] in {'window_elapsed', 'completed'})
    result = {
        'status': 'captured' if captured else 'partial_capture',
        'device': device, 'steps': steps,
        'crash_files': sum(path.is_file() and not path.is_symlink() for path in crashes.rglob('*')),
        'private_output': True, 'profile_observed': None,
    }
    with (output / 'receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result
