# iOS 16.2 Port for iPhone 6s (Experimental)

This unofficial fork preserves the original surrealra1n project by pwnerblu
under Apache-2.0. See the upstream LICENSE and NOTICE. The reference profile
definitions come from the N71 iOS 16.2 port, including Astra's Stage 18W offline
validation. This checkout needs only Bash and Python 3.9 or later for N71 file
checks. Live identity queries additionally need an installed copy of
`irecovery` on PATH. The N71 branch starts before upstream initialization.

## Device and firmware support

| Role | Product / board | Version / build |
| --- | --- | --- |
| Target | iPhone 6s, iPhone8,1 / N71AP, A9 CPID 0x8000, BDID 0x04 | iOS 16.2 / 20C65 port |
| System donor | iPad (5th generation Wi-Fi), iPad6,11 / j71sap, A9 CPID 0x8000, BDID 0x10 | iPadOS 16.2 / 20C65 |
| Native hardware donor | iPhone8,1 / N71AP | iOS 15.6 / 19G71 |

The IPSWs are supplied by the user. The checker reads the ZIP inventory,
BuildManifest and Restore.plist, requires matching board identities and required
members, and checks that native SEP and baseband entries exist. This is a format
and component inventory check. It does not authenticate IPSWs, verify the data
of every archive member, or establish hardware compatibility at runtime.

## Run the checks

From a checkout, use the original shell entry point:

```sh
./surrealra1n.sh --n71-port --profile 18u \
  --donor-ipsw /your/files/ipad-16.2.ipsw \
  --native-ipsw /your/files/iphone6s-15.6.ipsw
```

Use `--probe` for a read-only USB query on a device already in DFU or recovery,
or `--device-info /your/files/device-query.txt` to validate saved query output.
Device identifiers unique to a handset are omitted from the JSON output.
The result is printed to stdout. Errors go to stderr and return a nonzero code.

### Build a host evidence archive

Add `build-bundle` before the input flags and pass an unused ZIP path with
`--output`. This creates a deterministic archive containing a JSON receipt
with SHA-256 and sizes for both full IPSWs, along with the selected profile and
validation results. It contains no firmware payloads. Verify archive integrity
with `./surrealra1n.sh --n71-port verify-bundle /your/files/n71-evidence.zip`.
This receipt is a record of the checks. It is not a signed attestation or
an installable firmware image.

### Check recovery inputs or collect device logs

```sh
./surrealra1n.sh --n71-port recovery-check /your/files/18u-backup --probe
./surrealra1n.sh --n71-port collect-logs --output /your/private/path/n71-logs --seconds 10
```

`recovery-check` also accepts `--device-info` for a saved query. With identity
evidence, it compares the ECID with the recovery receipt without printing it.
Omit device options for a file-only check. This does not mount or verify live
volumes or perform a restore.

Log capture needs `idevice_id`, `ideviceinfo`, `idevicesyslog` and
`idevicecrashreport` from libimobiledevice and exactly one already paired
N71AP running iOS on USB. It collects a process snapshot, a bounded syslog
capture and copies available CommCenter crash reports, preserving the device
originals. A capture failure returns nonzero. Successful earlier outputs and
individual command statuses remain in the private output directory, which must
be new. Do not commit or publish raw logs.

- `--candidate-dir` takes a reference profile's external `offline-candidate`
  directory. It checks the stage, build, two receipt CDHashes, and full file
  SHA-256 against the pinned reference fingerprints.
- `--recovery-dir` takes a local Stage 18U device recovery export with
  `receipt.json` in the `n71-stage18w-recovery-export/v1` format. Both caches
  are checked against Stage 18U, and the source trust file is checked against its
  supplied receipt. This checks backup integrity. It does not authenticate
  the source trust file or verify restoration on a connected handset.
- Select `--profile 18w` explicitly for Stage 18W. Its candidates are verified
  against a separate set of fingerprints. Stage 18U is the recovery baseline
  for both profiles. Keep exports, IPSWs and device logs outside the checkout.
- Run the self-contained regression suite with
  `python3 -B -m unittest discover -s tests -p 'test_n71_*.py' -v`.

## Status and known issues

| Feature | Status |
| --- | --- |
| Device identity and IPSW checks | Implemented |
| Stage 18U / Stage 18W reference candidate and local backup verification | Implemented |
| Stage 18U runtime | Booted in the original port; cellular service unavailable |
| Stage 18W runtime | Untested on device / Experimental |
| Host evidence bundle and verification | Implemented |
| Paired device log collection | Implemented; successful capture tested with fixtures |
| New iOS candidate generation, trust image packaging, APFS restore and tethered boot | Unavailable in this N71 mode |
| Clean device flashing, SEP interoperability and recovery | Unverified |

The experimental port depends on a tethered boot and the original experiment's
Surreal16 system volume. The checker does not inspect or change partitions.
Baseband does not work. The port is unsuitable for daily use and actual
restoration attempts may fail or cause data loss. No installation has been
performed by the N71 mode. Upstream workflows are maintained by their original
author.
