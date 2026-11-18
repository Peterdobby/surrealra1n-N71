# v0.2.0-alpha

Experimental iPhone 6s iOS 16.2 port host tools, based on surrealra1n by pwnerblu.

- Extract and verify the unmodified system DMGs from user-supplied iPadOS
  `20C65` and native N71 `19G71` IPSWs.
- Create a separate local Stage 18U recovery copy after matching the device ECID.
  Verify full readback before recording success.
- Report App Store links, vibration, cellular and camera limitations, with
  distinct historical evidence for other functions.

Stage 18W remains **Experimental / Not device-verified**. Ported firmware
generation, device installation, device recovery, tethered boot and cellular
service are unavailable in this release. Camera is partially working and
captured photos are not saved to Photos.

The N71 contribution contains original validation code, tests, and
documentation. Its tests generate synthetic firmware metadata locally.
Firmware payloads, private device files and personal signing data are external.
The public repository contains the N71 source only. It retains pwnerblu's
attribution, Apache-2.0 LICENSE and NOTICE. The full development fork and
its upstream history are maintained locally.
