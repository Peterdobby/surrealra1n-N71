"""Exercise the shell entry point and N71 checks without private inputs."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'n71'))
spec = importlib.util.spec_from_file_location('n71_check', ROOT / 'n71/check.py')
n71 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n71)

QUERY = 'CPID: 0x8000\nBDID: 0x04\nPRODUCT: iPhone8,1\nMODEL: n71ap\nMODE: DFU\nECID: PRIVATE\n'


def firmware(path, identity, components, *, build=None, omit=None):
    version, real_build, product, board, bdid = identity
    common = {'ProductVersion': version, 'ProductBuildVersion': build or real_build,
              'SupportedProductTypes': [product]}
    members = {name: ('system.dmg' if name == 'OS' else name + '.fixture') for name in components}
    metadata = {**common, 'BuildIdentities': [
        {'ApChipID': '0x8000', 'ApBoardID': hex(bdid), 'Info': {'DeviceClass': board},
         'Manifest': {name: {'Info': {'Path': member}} for name, member in members.items()}}
    ]}
    restore = {**common, 'DeviceMap': [
        {'BoardConfig': board, 'Platform': 's8000', 'CPID': 0x8000, 'BDID': bdid}
    ]}
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('BuildManifest.plist', plistlib.dumps(metadata))
        archive.writestr('Restore.plist', plistlib.dumps(restore))
        for name, member in members.items():
            if name != omit:
                archive.writestr(member, (board + ':' + name).encode())


class ModeTests(unittest.TestCase):
    donor_members = ('OS', 'KernelCache', 'StaticTrustCache')
    native_members = ('DeviceTree', 'KernelCache', 'SEP', 'BasebandFirmware', 'iBSS', 'iBEC')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='n71 test ')
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.donor = self.folder / 'donor.ipsw'
        self.native = self.folder / 'native.ipsw'
        firmware(self.donor, n71.DONOR, self.donor_members)
        firmware(self.native, n71.NATIVE, self.native_members)

    def invoke(self, *extra, profile='18u', env=None):
        return subprocess.run(
            [str(ROOT / 'surrealra1n.sh'), '--n71-port', '--profile', profile,
             '--donor-ipsw', str(self.donor), '--native-ipsw', str(self.native), *map(str, extra)],
            cwd=self.folder, text=True, capture_output=True, env=env, timeout=20)

    def command(self, *args, env=None):
        return subprocess.run([str(ROOT / 'surrealra1n.sh'), '--n71-port', *map(str, args)],
                              cwd=self.folder, text=True, capture_output=True, env=env, timeout=20)

    def test_clean_entry_point_and_explicit_profile(self):
        result = self.invoke(profile='18w')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['target']['build'], '20C65')
        self.assertEqual(data['candidate']['status'], 'not_provided')
        self.assertIn('Untested on device', data['label'])
        self.assertFalse(data['flash_supported_by_this_mode'])

    def test_n71_identity_and_private_fields_omitted(self):
        query = self.folder / 'usb.txt'
        query.write_text(QUERY)
        result = self.invoke('--device-info', query)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['device']['board'], 'n71ap')
        self.assertNotIn('PRIVATE', result.stdout)

    def test_live_query_uses_read_only_action(self):
        irecovery = self.folder / 'irecovery'
        irecovery.write_text("#!/bin/sh\n[ \"$#\" = 1 ] && [ \"$1\" = -q ] || exit 2\ncat <<'END'\n"
                            + QUERY + "END\n")
        irecovery.chmod(0o700)
        result = self.invoke('--probe', env={**os.environ, 'PATH': f"{self.folder}:{os.environ['PATH']}"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['device']['source'], 'usb_query')

    def test_non_n71_and_variant_rejected(self):
        for changed in ('iPhone10,6', 'n71map', '0x8003', '0x05'):
            with self.subTest(changed=changed):
                replacements = {'iPhone10,6': 'iPhone8,1', 'n71map': 'n71ap',
                                '0x8003': '0x8000', '0x05': '0x04'}
                query = self.folder / 'usb.txt'
                query.write_text(QUERY.replace(replacements[changed], changed))
                result = self.invoke('--device-info', query)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('expected iPhone8,1 / N71AP', result.stderr)

    def test_bad_or_missing_ipsw(self):
        self.donor.unlink()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('donor.ipsw', result.stderr)
        self.donor.write_bytes(b'not a ZIP')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not a zip file', result.stderr.lower())

    def test_wrong_build_and_missing_component(self):
        firmware(self.donor, n71.DONOR, self.donor_members, build='WRONG')
        self.assertIn('expected 16.2 / 20C65', self.invoke().stderr)
        firmware(self.donor, n71.DONOR, self.donor_members, omit='OS')
        self.assertIn('missing OS archive member', self.invoke().stderr)

    def test_candidate_wrong_stage(self):
        (self.folder / 'receipt.json').write_text(json.dumps({'stage': '18U', 'build': '20C65'}))
        result = self.invoke('--candidate-dir', self.folder, profile='18w')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('expected 18W / 20C65 receipt', result.stderr)

    def test_candidate_and_recovery_integrity(self):
        expected = {}
        subcaches = {}
        files = {}
        for label in ('05', '29', 'source_trust'):
            data = label.encode()
            digest = hashlib.sha256(data).hexdigest()
            name = f'{n71.CACHE}.{label}.sealed' if label != 'source_trust' else 'trust.fixture'
            (self.folder / name).write_bytes(data)
            if label != 'source_trust':
                expected[label] = (digest, 'a' * 40)
                subcaches[label] = {'sealed_file': name, 'sealed_sha256': digest, 'new_cdhash': 'a' * 40}
            files[label] = {'local_name': name, 'sha256': digest, 'size': len(data)}
        receipt = self.folder / 'receipt.json'
        with patch.dict(n71.PROFILES, {'18u': ('test', expected)}):
            receipt.write_text(json.dumps({'stage': '18U', 'build': '20C65', 'subcaches': subcaches}))
            self.assertEqual(n71.check_candidate(self.folder, '18u')['status'], 'reference_bytes_verified')
            (self.folder / files['29']['local_name']).write_bytes(b'xx')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                n71.check_candidate(self.folder, '18u')
            (self.folder / files['29']['local_name']).write_bytes(b'29')
            receipt.write_text(json.dumps({
                'schema': 'n71-stage18w-recovery-export/v1', 'baseline': '18U',
                'device_identity': {'board': 'n71ap', 'product': 'iPhone8,1', 'chip': 0x8000, 'bdid': 4},
                'files': files,
            }))
            self.assertFalse(n71.check_recovery(self.folder)['live_restore_verified'])
            (self.folder / files['source_trust']['local_name']).write_bytes(b'X' * len('source_trust'))
            with self.assertRaisesRegex(ValueError, 'recovery source_trust: size or SHA-256 mismatch'):
                n71.check_recovery(self.folder)

    def test_build_bundle_is_reproducible_and_verified(self):
        inputs = ('build-bundle', '--profile', '18u', '--donor-ipsw', self.donor,
                  '--native-ipsw', self.native, '--output')
        one, two = self.folder / 'one.zip', self.folder / 'two.zip'
        for dest in (one, two):
            result = self.command(*inputs, dest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'built_and_verified')
        self.assertEqual(one.read_bytes(), two.read_bytes())
        self.assertNotEqual(self.command(*inputs, one).returncode, 0)
        result = self.command('verify-bundle', one)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['sha256'], hashlib.sha256(one.read_bytes()).hexdigest())
        with zipfile.ZipFile(one) as archive:
            checksums = archive.read('SHA256SUMS')
        with zipfile.ZipFile(one, 'w') as archive:
            archive.writestr('receipt.json', b'{}')
            archive.writestr('SHA256SUMS', checksums)
        result = self.command('verify-bundle', one)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('receipt checksum mismatch', result.stderr)

    def test_recovery_command_rejects_a_different_device_before_reading_backups(self):
        receipt = {'schema': 'n71-stage18w-recovery-export/v1', 'baseline': '18U',
                   'device_identity': {'board': 'n71ap', 'product': 'iPhone8,1',
                                       'chip': 0x8000, 'bdid': 4, 'ecid': 0x47}}
        (self.folder / 'receipt.json').write_text(json.dumps(receipt))
        query = self.folder / 'query.txt'
        query.write_text(QUERY.replace('PRIVATE', '0x48'))
        result = self.command('recovery-check', self.folder, '--device-info', query)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ECID differs', result.stderr)
        self.assertNotIn('0x48', result.stderr)
        query.write_text(QUERY.replace('PRIVATE', '0x47'))
        result = self.command('recovery-check', self.folder, '--device-info', query)
        self.assertIn('expected .05, .29 and source trust', result.stderr)

    def capture_tools(self, *, fail_crash=False):
        commands = {
            'idevice_id': 'echo fixture-udid',
            'ideviceinfo': ('case "$4" in ProductType) echo iPhone8,1;; HardwareModel) echo N71AP;; '
                            'ProductVersion) echo 16.2;; BuildVersion) echo 20C65;; *) exit 5;; esac'),
            'idevicesyslog': 'printf "fixture log\n"',
            'idevicecrashreport': ('exit 9' if fail_crash else
                                  '[ "$3" = --keep ] && [ "$4" = --filter ] && '
                                  '[ "$5" = CommCenter ] && printf "fixture" > "$6/CommCenter.ips"'),
        }
        for name, body in commands.items():
            path = self.folder / name
            path.write_text('#!/bin/sh\n' + body + '\n')
            path.chmod(0o700)
        return {**os.environ, 'PATH': f"{self.folder}:{os.environ['PATH']}"}

    def test_log_capture_keeps_crashes_and_records_results(self):
        dest = self.folder / 'captured'
        result = self.command('collect-logs', '--output', dest, '--seconds', '1',
                              env=self.capture_tools())
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = (dest / 'receipt.json').read_text()
        self.assertNotIn('fixture-udid', receipt)
        self.assertEqual(json.loads(receipt)['status'], 'captured')
        self.assertTrue((dest / 'crashes/CommCenter.ips').is_file())

    def test_log_failure_retains_partial_results(self):
        dest = self.folder / 'captured'
        result = self.command('collect-logs', '--output', dest, '--seconds', '1',
                              env=self.capture_tools(fail_crash=True))
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((dest / 'receipt.json').read_text())
        self.assertEqual(receipt['steps']['crash_copy'], 'failed_exit_9')
        self.assertEqual(receipt['status'], 'partial_capture')
        self.assertTrue((dest / 'syslog.log').stat().st_size)

    def test_extract_and_verify_stock_donors(self):
        firmware(self.native, n71.NATIVE, (*self.native_members, 'OS'))
        dest = self.folder / 'new donors'
        prepare = ('prepare-donors', '--donor-ipsw', self.donor, '--native-ipsw',
                   self.native, '--output', dest)
        result = self.command(*prepare)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((dest / 'ipad-system.dmg').read_bytes(), b'j71sap:OS')
        self.assertEqual((dest / 'iphone-system.dmg').read_bytes(), b'n71ap:OS')
        self.assertEqual(self.command('verify-donors', dest).returncode, 0)
        self.assertNotEqual(self.command(*prepare).returncode, 0)
        (dest / 'iphone-system.dmg').write_bytes(b'x71ap:OS')
        self.assertIn('readback SHA-256 differs', self.command('verify-donors', dest).stderr)

    def test_missing_donor_os_creates_no_output(self):
        dest = self.folder / 'new donors'
        result = self.command('prepare-donors', '--donor-ipsw', self.donor,
                              '--native-ipsw', self.native, '--output', dest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('native IPSW: invalid OS member path', result.stderr)
        self.assertFalse(dest.exists())

    def test_recovery_copy_reads_back_and_removes_partial_writes(self):
        files = {}
        for label in n71.workspace.RECOVERY_NAMES:
            data = label.encode()
            (self.folder / label).write_bytes(data)
            files[label] = {'local_name': label, 'size': len(data),
                            'sha256': hashlib.sha256(data).hexdigest()}
        receipt = {'device_identity': {'board': 'n71ap', 'product': 'iPhone8,1',
                                       'chip': 0x8000, 'bdid': 4, 'ecid': 0x47},
                   'files': files}
        target = self.folder / 'new backup'
        transfer = n71.workspace.transfer
        def interrupt(source, path, size):
            if path.name == 'cache.29':
                raise OSError('simulated local write failure')
            return transfer(source, path, size)
        with patch.object(n71.workspace, 'transfer', side_effect=interrupt):
            with self.assertRaisesRegex(OSError, 'simulated local write failure'):
                n71.workspace.copy_recovery(self.folder, target, receipt)
        self.assertFalse(target.exists())
        expected = {key: (files[key]['sha256'], '') for key in ('05', '29')}
        with patch.dict(n71.PROFILES, {'18u': ('test', expected)}):
            n71.workspace.copy_recovery(self.folder, target, receipt)
            self.assertTrue(n71.check_recovery(target, ecid=0x47)['device_ecid_matches'])
            for label, name in n71.workspace.RECOVERY_NAMES.items():
                self.assertEqual((target / name).read_bytes(), label.encode())


if __name__ == '__main__':
    unittest.main()
