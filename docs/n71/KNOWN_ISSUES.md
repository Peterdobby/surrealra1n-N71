# Known issues

- The historical port is tethered. This release cannot install or boot it.
- iPhone8,1 models with a different board or CPID are outside the N71AP profile.
- Stage 18W is untested on a device; Stage 18U's boot evidence is specific to
  the original port hardware and setup. Baseband is unavailable on both.
- Cellular / baseband is **Not working**. SIM, calls and mobile data are unverified
  or unavailable. Stage 18W Mav13 changes have offline evidence only.
- Vibration / haptics is **Not working** in current device tests.
- Camera is **Partially working** — captured photos are not saved to Photos.
  Earlier front and rear preview evidence does not establish capture or saving.
  Normal video saving failed in historical tests and slow motion is untested.
- App Store links are **Not working / Reported unavailable**. Other Apple
  services, including Apple ID, iCloud, iMessage and FaceTime, are untested.
- IPSW structural checks and reference hashes do not establish authenticity,
  current signing status, or SEP/baseband compatibility.
- Recovery checks validate supplied files and can compare an ECID. They do not
  inspect a live target volume or make an installed system recoverable.
- Diagnostic capture requires an already paired, running iOS session. DFU,
  recovery, and a diagnostic RAM disk may not offer the required services.
- Device restoration may fail and lose data. The port is unsuitable for daily use.
