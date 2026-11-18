# N71 release status

| Stage or function | v0.2.0-alpha scope |
| --- | --- |
| Device selection | Matches iPhone8,1 / N71AP / CPID 0x8000 / BDID 0x04 from a read-only recovery query |
| IPSW inputs | Checks iPad6,11 20C65 and N71AP 19G71 metadata and component namespaces |
| Host build | Generates and verifies a deterministic evidence ZIP from user supplied inputs |
| Donor preparation | Extracts the two unmodified system images and verifies ZIP CRC, length, and SHA-256 readback |
| iOS 16.2 candidate build | No firmware builder in this release |
| Stage 18U | Existing cache bytes can be verified; original port device booted the baseline |
| Stage 18W | Experimental / Not device-verified; offline evidence only |
| Restore checks | Verifies Stage 18U local backup files; optional ECID check |
| Local recovery copy | Creates a separate three-file backup set on the host; requires matching ECID and verifies full readback |
| Install, device restore, tethered boot | Unavailable in this release |
| SpringBoard | Historical evidence from the original port only |
| Diagnostics | Standard paired iOS USB collection; success and failure tested with fixtures |
| Baseband | Unavailable |

## Hardware evidence

The current failures below are based on the project owner's device feedback.
Historical results come from the original N71 port, not from this release.

| Feature | Status | Evidence and limits |
| --- | --- | --- |
| Display | Historical verification only | Original port reached the lock screen and SpringBoard |
| Touch | Historical verification only | Earlier device sessions confirmed interaction and wake |
| Wi-Fi | Historical verification only | Association and IPv4 verified; current profile and internet access not established by this release |
| Bluetooth | Untested for accessories | Historical controller power and daemon recorded; accessory pairing, data and audio unverified |
| Speaker | Historical verification only | Stage 9 audible PCM test; later Stage 10 audio observed |
| Battery | Historical verification only | GasGauge and percentage read back in earlier stages |
| Charging | Historical verification only | Charge-state readings and increasing percentages observed in earlier wired tests; wider power conditions untested |
| Touch ID | Historical verification only | Stage 7 rollback baseline unlocked with Touch ID; not verified in this release |
| Wallpaper | Historical/partial evidence only | Earlier resource adaptation; selecting, applying to both screens and persistence need current retesting |
| Camera | Partially working | Captured photos are not saved to Photos in current testing |
| Front camera | Historical verification only | Stage 12 preview; one earlier V2 JPEG import does not establish current saving |
| Rear camera | Partially working | Historical preview and shutter callback; capture completion and saving failed |
| Normal video | Historical partial result | Rear recording started; a usable video in Photos was not established |
| Slow motion | Untested | No verified high frame rate capture or playback |
| Vibration / haptics | Not working | Current device feedback |
| Cellular / baseband | Not working | No mobile network, calls, or cellular data; Stage 18W Mav13 work is offline only |
| Apple Services / App Store links | Not working / Reported unavailable | App Store link failure reported; Apple ID, iCloud, iMessage and FaceTime are untested |

The public source release contains the N71 tools only. The local development
fork keeps the upstream surrealra1n history and other device workflows.
