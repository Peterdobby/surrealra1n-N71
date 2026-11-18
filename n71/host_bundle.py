"""Build and verify a deterministic N71 host evidence archive."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

SCHEMA = 'surrealra1n.n71.host-bundle/v1'
MEMBERS = {'receipt.json', 'SHA256SUMS'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(path):
    if path.stat().st_size > 256 * 1024:
        raise ValueError('bundle exceeds maximum size')
    try:
        with zipfile.ZipFile(path) as archive:
            files = archive.infolist()
            if len(files) != len(MEMBERS) or {row.filename for row in files} != MEMBERS:
                raise ValueError('bundle has unexpected or duplicate members')
            if any(row.file_size > 64 * 1024 for row in files):
                raise ValueError('bundle member exceeds maximum size')
            receipt = archive.read('receipt.json')
            if archive.read('SHA256SUMS') != f'{digest(receipt)}  receipt.json\n'.encode():
                raise ValueError('bundle receipt checksum mismatch')
            record = json.loads(receipt)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError('invalid host bundle') from exc
    if (not isinstance(record, dict) or record.get('schema') != SCHEMA
            or record.get('scope') != 'host_evidence_only'
            or not isinstance(record.get('checks'), dict)
            or record['checks'].get('profile') not in ('18U', '18W')):
        raise ValueError('invalid host bundle receipt')
    return {'schema': SCHEMA, 'profile': record['checks']['profile'],
            'status': 'checksum_verified', 'sha256': digest(path.read_bytes())}


def build(path, checks, sources):
    receipt = json.dumps({'schema': SCHEMA, 'scope': 'host_evidence_only',
                          'checks': checks, 'input_ipsws': sources},
                         indent=2, sort_keys=True).encode() + b'\n'
    with tempfile.TemporaryDirectory(prefix='.n71-evidence-', dir=path.parent) as temporary:
        staged = Path(temporary) / 'evidence.zip'
        with zipfile.ZipFile(staged, 'w') as archive:
            # ZipInfo supplies fixed timestamps so identical inputs yield identical bytes.
            archive.writestr(zipfile.ZipInfo('receipt.json'), receipt)
            archive.writestr(zipfile.ZipInfo('SHA256SUMS'), f'{digest(receipt)}  receipt.json\n')
        verified = verify(staged)
        os.link(staged, path)
    return {**verified, 'status': 'built_and_verified', 'output': str(path)}
