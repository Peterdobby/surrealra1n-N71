# N71 release status

| Stage or function | v0.1.0-alpha scope |
| --- | --- |
| Device selection | Matches iPhone8,1 / N71AP / CPID 0x8000 / BDID 0x04 from a read-only recovery query |
| IPSW inputs | Checks iPad6,11 20C65 and N71AP 19G71 metadata and component namespaces |
| Host build | Generates and verifies a deterministic evidence ZIP from user supplied inputs |
| iOS 16.2 candidate build | No firmware builder in this release |
| Stage 18U | Existing cache bytes can be verified; original port device booted the baseline |
| Stage 18W | Existing cache bytes can be verified; offline evidence only |
| Restore checks | Verifies Stage 18U local backup files; optional ECID check |
| Install, device restore, tethered boot | Unavailable in this release |
| SpringBoard | Historical evidence from the original port only |
| Diagnostics | Standard paired iOS USB collection; success and failure tested with fixtures |
| Baseband | Unavailable |

The public source release contains the N71 tools only. The local development
fork keeps the upstream surrealra1n history and other device workflows.
