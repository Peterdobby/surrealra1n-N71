# surrealra1n-N71

Experimental iPhone 6s tools for preparing iOS 16.2 donor files, verifying
recovery copies, and collecting paired iOS diagnostics. Based on
[surrealra1n by pwnerblu](https://github.com/pwnerblu/surrealra1n). This is an
unofficial source release of the N71 host tools. The full development fork
retains upstream history locally.

The underlying port requires tethered boot. Baseband does not work and the port
is unsuitable for daily use. Device restoration may fail and data loss is possible.
The N71 mode prepares files on the host and checks device identity. It does not
build a flashable port or install firmware.

## Current Hardware Status

| Feature | Status |
| --- | --- |
| Display and touch | Working in historical device tests |
| Wi-Fi | Working in historical device tests; association and IPv4 observed |
| Camera | Partially working — captured photos are not saved to Photos |
| Vibration / haptics | Not working |
| Cellular / baseband | Not working |
| Apple Services / App Store links | Not working (reported); other Apple services untested |
| Tethered boot | Required by the original port; unavailable in this release |

Stage 18U has historical boot evidence. Stage 18W is **Experimental / Not
device-verified**. For individual camera modes and other hardware, see the
[hardware status](docs/n71/STATUS.md#hardware-evidence).

[Installation and supported inputs (English)](docs/n71/INSTALL.md) ·
[中文 README](README.zh-CN.md) · [安装与支持范围（中文）](docs/n71/INSTALL.zh-CN.md) ·
[Feature status](docs/n71/STATUS.md) · [Known issues](docs/n71/KNOWN_ISSUES.md)

