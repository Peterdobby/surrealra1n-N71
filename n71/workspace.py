"""Create verified local workspaces without communicating with a device."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import shutil
import stat
import zipfile

DONOR_SCHEMA = 'surrealra1n.n71.donor-workspace/v1'
RECOVERY_SCHEMA = 'n71-stage18w-recovery-export/v1'
DONOR_NAMES = {'donor': 'ipad-system.dmg', 'native': 'iphone-system.dmg'}
RECOVERY_NAMES = {'05': 'cache.05', '29': 'cache.29', 'source_trust': 'source-trust.backup'}
BLOCK_SIZE = 1024 * 1024


@contextmanager
def new_workspace(output, size):
    if not output.parent.is_dir():
        raise ValueError('output parent directory does not exist')
    if shutil.disk_usage(output.parent).free < size + 4 * BLOCK_SIZE:
        raise ValueError('insufficient host disk space for workspace')
    output.mkdir(mode=0o700)
    try:
        yield
    except BaseException:
        shutil.rmtree(output)
        raise


def transfer(source, destination, expected_size):
    digest = hashlib.sha256()
    size = 0
    with destination.open('xb') as output:
        for chunk in iter(lambda: source.read(BLOCK_SIZE), b''):
            size += len(chunk)
            if size > expected_size:
                raise ValueError(f'{destination.name}: input exceeds recorded size')
            output.write(chunk)
            digest.update(chunk)
        output.flush()
        os.fsync(output.fileno())
    if size != expected_size:
        raise ValueError(f'{destination.name}: input length differs')
    return {'local_name': destination.name, 'size': size, 'sha256': digest.hexdigest()}


def readback(path, row):
    expected = row['sha256']
    if (not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1
            or type(row['size']) is not int or path.stat().st_size != row['size']
            or not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)):
        raise ValueError(f'{path.name}: workspace file or receipt is invalid')
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(BLOCK_SIZE), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError(f'{path.name}: readback SHA-256 differs')


def save_receipt(output, receipt):
    with (output / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def prepare_donors(output, archives, records):
    """Extract only the pinned, unmodified OS partition files for host use."""
    size = sum(records[key]['os_image']['size'] for key in DONOR_NAMES)
    files = {}
    with new_workspace(output, size):
        for role, name in DONOR_NAMES.items():
            row = records[role]['os_image']
            member = row['member']
            with zipfile.ZipFile(archives[role]) as archive:
                entry = archive.getinfo(member)
                if (entry.file_size != row['size'] or entry.CRC != row['crc32']
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise ValueError(f'{role}: IPSW changed after validation')
                with archive.open(entry) as source:
                    files[role] = transfer(source, output / name, row['size'])
            readback(output / name, files[role])
            files[role].update({
                'original_member': PurePosixPath(member).name,
                'product': records[role]['product'], 'build': records[role]['build'],
            })
        save_receipt(output, {'schema': DONOR_SCHEMA, 'scope': 'unmodified_donor_system_images',
                              'files': files})
    return {'status': 'donor_images_prepared', 'files': files, 'device_modified': False}


def verify_donors(directory, receipt):
    if (receipt.get('schema') != DONOR_SCHEMA or receipt.get('scope') != 'unmodified_donor_system_images'
            or set(receipt.get('files', {})) != set(DONOR_NAMES)
            or {item.name for item in directory.iterdir()} != {'receipt.json', *DONOR_NAMES.values()}):
        raise ValueError('invalid donor workspace inventory')
    for role, name in DONOR_NAMES.items():
        row = receipt['files'][role]
        expected = ('iPad6,11', '20C65') if role == 'donor' else ('iPhone8,1', '19G71')
        if row['local_name'] != name or (row['product'], row['build']) != expected:
            raise ValueError(f'{role}: wrong role, product or build')
        readback(directory / name, row)
    return {'status': 'donor_images_verified', 'files': receipt['files'], 'device_modified': False}


def copy_recovery(source_dir, output, receipt):
    """Materialize a separate backup set and verify each written host file."""
    size = sum(receipt['files'][label]['size'] for label in RECOVERY_NAMES)
    records = {}
    with new_workspace(output, size):
        for label, name in RECOVERY_NAMES.items():
            row = receipt['files'][label]
            original = source_dir / row['local_name']
            if original.is_symlink():
                raise ValueError(f'{label}: recovery source is a symlink')
            with original.open('rb') as source:
                copied = transfer(source, output / name, row['size'])
            if copied['sha256'] != row['sha256']:
                raise ValueError(f'{label}: recovery source SHA-256 differs')
            readback(output / name, copied)
            records[label] = copied
        save_receipt(output, {'schema': RECOVERY_SCHEMA, 'baseline': '18U',
                              'device_identity': {key: receipt['device_identity'][key] for key in
                                                  ('board', 'product', 'chip', 'bdid', 'ecid')},
                              'files': records})
    return {'status': 'local_recovery_copy_verified', 'file_count': len(records),
            'device_ecid_matches': True, 'live_restore_verified': False}
