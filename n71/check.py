"""Read-only N71 support for the surrealra1n shell entry point."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import subprocess
import sys
import zipfile

import host_bundle
from diagnostics import capture
import workspace

TARGET = {'product': 'iPhone8,1', 'board': 'n71ap', 'cpid': 0x8000, 'bdid': 4}
PROFILES = {
    '18u': (
        'Stage 18U experimental baseline (booted on original port device)',
        {'05': ('6eed7021eacc7a88afbfc7a99205507a513ccd5a251810ec99b45674543f770a',
                'b9d2c7507b4e4e85a1607140233ecf92bb51d8ca'),
         '29': ('a28d6bd739bcb5a1b73ed92e19f5858bc05e9aac3c3cf1093c6038983cf060ca',
                '7e128f33559bc10517f27f070b2557e5945cc586')},
    ),
    '18w': (
        'Stage 18W / Untested on device / Experimental',
        {'05': ('1c86259271631a78d41a3daa3c53e3b43e4717a6f4b43826bc0086af5fb17ba0',
                '9eb110d984cb7b7b927a6f75633cd6d2ac3b13b9'),
         '29': ('8f1b4a2c0ddfbf624e41cb93612ec2ce956fe9d8bcca6b961e4670c4a291dd84',
                '00500c6f2c4249af28f0f444c3a6ae05b729d3a1')},
    ),
}
DONOR = ('16.2', '20C65', 'iPad6,11', 'j71sap', 0x10)
NATIVE = ('15.6', '19G71', 'iPhone8,1', 'n71ap', 0x04)
CACHE = 'dyld_shared_cache_arm64'
MAX_METADATA = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    if type(value) is int:
        return value
    require(isinstance(value, str), 'invalid numeric identity field')
    return int(value, 16 if value.lower().startswith('0x') else 10)


def read_identity(info):
    fields = {}
    for line in info.splitlines():
        key, _, value = line.partition(':')
        if key in {'PRODUCT', 'MODEL', 'CPID', 'BDID', 'MODE'}:
            require(key not in fields, f'duplicate device field {key}')
            fields[key] = value.strip()
    for name in ('PRODUCT', 'MODEL', 'CPID', 'BDID', 'MODE'):
        require(bool(fields.get(name)), f'device query missing {name}')
    actual = (fields['PRODUCT'], fields['MODEL'].lower(), number(fields['CPID']), number(fields['BDID']))
    require(actual == tuple(TARGET.values()), 'expected iPhone8,1 / N71AP / CPID 0x8000 / BDID 0x04')
    mode = fields['MODE'].upper()
    require(mode in ('DFU', 'RECOVERY'), 'expected DFU or recovery query output')
    return {**TARGET, 'mode': mode}


def local_file(path, label):
    require(not path.is_symlink() and path.is_file(), f'{label}: expected regular file ({path.name})')
    return path


def metadata_json(directory, label):
    path = local_file(directory / 'receipt.json', label)
    require(path.stat().st_size <= MAX_METADATA, f'{label}: receipt too large')
    record = json.loads(path.read_bytes())
    require(isinstance(record, dict), f'{label}: expected JSON object')
    return record


def archive_plist(archive, name):
    try:
        entry = archive.getinfo(name)
    except KeyError as exc:
        raise ValueError(f'missing {name}') from exc
    require(0 < entry.file_size <= MAX_METADATA, f'invalid {name} size')
    result = plistlib.loads(archive.read(entry))
    require(isinstance(result, dict), f'invalid {name}')
    return result


def check_ipsw(path, role, expected, components, *, select_os=False):
    version, build, product, board, bdid = expected
    try:
        with zipfile.ZipFile(local_file(path, role)) as archive:
            names = archive.namelist()
            require(len(set(names)) == len(names), 'duplicate IPSW archive entries')
            manifest = archive_plist(archive, 'BuildManifest.plist')
            restore = archive_plist(archive, 'Restore.plist')
            for record in (manifest, restore):
                require((record.get('ProductVersion'), record.get('ProductBuildVersion')) ==
                        (version, build), f'expected {version} / {build}')
                require(product in record.get('SupportedProductTypes', []), f'expected product {product}')
            require(any(row.get('BoardConfig', '').lower() == board and row.get('Platform') == 's8000'
                        and number(row.get('CPID')) == TARGET['cpid']
                        and number(row.get('BDID')) == bdid for row in restore['DeviceMap']),
                    f'Restore.plist lacks {board} A9 identity')
            identities = [row for row in manifest['BuildIdentities']
                          if row.get('Info', {}).get('DeviceClass', '').lower() == board
                          and number(row.get('ApChipID')) == TARGET['cpid']
                          and number(row.get('ApBoardID')) == bdid]
            require(identities, f'BuildManifest lacks {board} A9 identity')
            images = set()
            for identity in identities:
                for component in components:
                    member = identity.get('Manifest', {}).get(component, {}).get('Info', {}).get('Path')
                    require(isinstance(member, str) and not PurePosixPath(member).is_absolute()
                            and '..' not in PurePosixPath(member).parts and chr(92) not in member,
                            f'invalid {component} member path')
                    try:
                        entry = archive.getinfo(member)
                    except KeyError as exc:
                        raise ValueError(f'missing {component} archive member') from exc
                    require(entry.file_size > 0 and not entry.is_dir()
                            and not stat.S_ISLNK(entry.external_attr >> 16),
                            f'invalid {component} archive member')
                    if select_os and component == 'OS':
                        require(PurePosixPath(member).suffix == '.dmg', 'OS member must be a DMG')
                        images.add((member, entry.file_size, entry.CRC))
            if select_os:
                require(len(images) == 1, 'expected the same OS member across matching identities')
                member, size, crc = images.pop()
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError,
            zipfile.BadZipFile, plistlib.InvalidFileException) as exc:
        raise ValueError(f'{role} IPSW: {exc}') from exc
    record = {'product': product, 'board': board, 'version': version, 'build': build,
              'matching_identities': len(identities), 'components_present': list(components)}
    if select_os:
        record['os_image'] = {'member': member, 'size': size, 'crc32': crc}
    return record


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check_candidate(directory, profile):
    receipt = metadata_json(directory, 'candidate')
    require(receipt.get('stage') == profile.upper() and receipt.get('build') == DONOR[1],
            f'candidate: expected {profile.upper()} / {DONOR[1]} receipt')
    expected = PROFILES[profile][1]
    rows = receipt.get('subcaches', {})
    require(set(rows) == set(expected), 'candidate: expected .05 and .29 receipts')
    for suffix, (digest, cdhash) in expected.items():
        name = f'{CACHE}.{suffix}.sealed'
        row = rows[suffix]
        require((row.get('sealed_file'), row.get('sealed_sha256'), row.get('new_cdhash')) ==
                (name, digest, cdhash), f'candidate .{suffix}: receipt does not match profile')
        require(sha256(local_file(directory / name, 'candidate')) == digest,
                f'candidate .{suffix}: SHA-256 mismatch')
    return {'status': 'reference_bytes_verified', 'profile': profile.upper(),
            'files': {key: {'sha256': pair[0], 'cdhash': pair[1]} for key, pair in expected.items()}}


def check_recovery(directory, *, ecid=None, receipt=None):
    if receipt is None:
        receipt = metadata_json(directory, 'recovery')
    identity = receipt.get('device_identity', {})
    require(receipt.get('schema') == 'n71-stage18w-recovery-export/v1'
            and receipt.get('baseline') == '18U'
            and all(identity.get(key) == TARGET[key] for key in ('board', 'product', 'bdid'))
            and identity.get('chip') == TARGET['cpid'],
            'recovery: expected an N71AP Stage 18U export receipt')
    if ecid is not None:
        require(type(identity.get('ecid')) is int and identity['ecid'] == ecid,
                'recovery: device ECID differs from the backup receipt')
    rows = receipt.get('files', {})
    require(set(rows) == {'05', '29', 'source_trust'}, 'recovery: expected .05, .29 and source trust')
    verified, names = {}, set()
    for label, row in rows.items():
        name = row.get('local_name', '')
        require(isinstance(name, str) and name and Path(name).name == name
                and name not in {'.', '..', 'receipt.json'} and name not in names,
                f'recovery {label}: invalid or duplicate file name')
        names.add(name)
        expected = row.get('sha256', '')
        require(isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected),
                f'recovery {label}: invalid SHA-256')
        if label != 'source_trust':
            require(expected == PROFILES['18u'][1][label][0], f'recovery .{label}: expected Stage 18U hash')
        path = local_file(directory / name, 'recovery')
        size = path.stat().st_size
        require(path.stat().st_nlink == 1 and type(row.get('size')) is int
                and size == row['size'] and size > 0 and sha256(path) == expected,
                f'recovery {label}: size or SHA-256 mismatch')
        verified[label] = {'size': size, 'checksum_matches': True}
    return {'status': 'local_export_files_verified', 'baseline': '18U', 'files': verified,
            'device_ecid_matches': True if ecid is not None else None,
            'source_trust_reference': 'supplied_receipt', 'live_restore_verified': False}


def device_info(args, *, bind_recovery=False):
    if args.probe:
        try:
            query = subprocess.run(['irecovery', '-q'], capture_output=True, text=True,
                                   check=True, timeout=10).stdout
        except FileNotFoundError as exc:
            raise ValueError('device probe requires irecovery on PATH') from exc
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValueError('device query failed; check the USB connection and mode') from exc
        source = 'usb_query'
    elif args.device_info:
        path = local_file(args.device_info, 'device query')
        require(path.stat().st_size <= MAX_METADATA, 'device query file too large')
        query, source = path.read_text(), 'saved_query'
    else:
        return None, None
    observed = {'source': source, **read_identity(query)}
    if not bind_recovery:
        return observed, None
    values = re.findall(r'^ECID:\s*(0x[0-9a-fA-F]+)\s*$', query, re.MULTILINE)
    require(len(values) == 1 and 0 < int(values[0], 16) < (1 << 64),
            'device query must include one valid ECID to check recovery identity')
    return observed, int(values[0], 16)


def add_device_options(parser):
    device = parser.add_mutually_exclusive_group()
    device.add_argument('--probe', action='store_true', help='read connected device identity using irecovery -q')
    device.add_argument('--device-info', type=Path, help='check saved irecovery -q text')


def port_report(args):
    observed, ecid = device_info(args, bind_recovery=bool(args.recovery_dir))
    donor = check_ipsw(args.donor_ipsw, 'donor', DONOR, ('OS', 'KernelCache', 'StaticTrustCache'))
    native = check_ipsw(args.native_ipsw, 'native', NATIVE,
                        ('DeviceTree', 'KernelCache', 'SEP', 'BasebandFirmware', 'iBSS', 'iBEC'))
    return {
        'mode': 'n71_port_validation', 'target': {**TARGET, 'build': DONOR[1]},
        'device': observed, 'profile': args.profile.upper(), 'label': PROFILES[args.profile][0],
        'donor': donor, 'native': native,
        'candidate': (check_candidate(args.candidate_dir, args.profile)
                      if args.candidate_dir else {'status': 'not_provided'}),
        'recovery': (check_recovery(args.recovery_dir, ecid=ecid)
                     if args.recovery_dir else {'status': 'not_provided'}),
        'system_volume_reference': 'Surreal16', 'boot_requirement': 'tethered',
        'flash_supported_by_this_mode': False,
    }


def input_options(parser):
    parser.add_argument('--profile', choices=PROFILES, required=True)
    parser.add_argument('--donor-ipsw', type=Path, required=True)
    parser.add_argument('--native-ipsw', type=Path, required=True)
    parser.add_argument('--candidate-dir', type=Path, help='optional local reference cache export')
    parser.add_argument('--recovery-dir', type=Path, help='optional local Stage 18U recovery export')
    add_device_options(parser)


def main():
    parser = argparse.ArgumentParser(prog='surrealra1n.sh --n71-port',
                                     description='iPhone 6s — iOS 16.2 Port (Experimental)',
                                     epilog='Commands: prepare-donors, verify-donors, copy-recovery, '
                                     'build-bundle, verify-bundle, recovery-check, collect-logs. '
                                     'The original options continue to run input validation.')
    argv = sys.argv[1:]
    action = argv[0] if argv and argv[0] in (
        'build-bundle', 'verify-bundle', 'recovery-check', 'collect-logs',
        'prepare-donors', 'verify-donors', 'copy-recovery') else None
    if action:
        parser.prog += ' ' + action
        argv = argv[1:]
    if action == 'verify-bundle':
        parser.add_argument('bundle', type=Path)
    elif action == 'prepare-donors':
        parser.add_argument('--donor-ipsw', type=Path, required=True)
        parser.add_argument('--native-ipsw', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
    elif action == 'verify-donors':
        parser.add_argument('directory', type=Path)
    elif action in ('recovery-check', 'copy-recovery'):
        parser.add_argument('recovery_dir', type=Path)
        add_device_options(parser)
        if action == 'copy-recovery':
            parser.add_argument('--output', type=Path, required=True)
    elif action == 'collect-logs':
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--seconds', type=int, default=10, choices=range(1, 61), metavar='1..60')
    else:
        input_options(parser)
        if action == 'build-bundle':
            parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if action == 'verify-bundle':
            result = host_bundle.verify(local_file(args.bundle, 'bundle'))
        elif action == 'prepare-donors':
            archives = {'donor': args.donor_ipsw, 'native': args.native_ipsw}
            records = {role: check_ipsw(archives[role], role, expected, ('OS',), select_os=True)
                       for role, expected in (('donor', DONOR), ('native', NATIVE))}
            result = workspace.prepare_donors(args.output, archives, records)
        elif action == 'verify-donors':
            result = workspace.verify_donors(args.directory, metadata_json(args.directory, 'donors'))
        elif action == 'copy-recovery':
            _, ecid = device_info(args, bind_recovery=True)
            require(ecid is not None, 'copy-recovery requires --probe or --device-info')
            receipt = metadata_json(args.recovery_dir, 'recovery')
            check_recovery(args.recovery_dir, ecid=ecid, receipt=receipt)
            result = workspace.copy_recovery(args.recovery_dir, args.output, receipt)
        elif action == 'recovery-check':
            device, ecid = device_info(args, bind_recovery=True)
            result = {'device': device, **check_recovery(args.recovery_dir, ecid=ecid)}
        elif action == 'collect-logs':
            result = capture(args.output, args.seconds, TARGET)
        else:
            result = port_report(args)
            if action == 'build-bundle':
                require(not args.output.exists() and not args.output.is_symlink(),
                        'bundle output already exists')
                require(args.output.parent.is_dir(), 'bundle output parent directory does not exist')
                sources = {role: {'sha256': sha256(path), 'size': path.stat().st_size}
                           for role, path in (('donor', args.donor_ipsw), ('native', args.native_ipsw))}
                result = host_bundle.build(args.output, result, sources)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'N71 port check: {exc}\n')
    print(json.dumps(result, indent=2))
    if action == 'collect-logs' and result['status'] != 'captured':
        return 1
    return 0


if __name__ == '__main__':
    if sys.version_info < (3, 9):
        raise SystemExit('N71 port check requires Python 3.9 or newer.')
    raise SystemExit(main())
