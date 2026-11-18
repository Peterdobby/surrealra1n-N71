# Known issues

- The historical port is tethered. This release cannot install or boot it.
- iPhone8,1 models with a different board or CPID are outside the N71AP profile.
- Stage 18W is untested on a device; Stage 18U's boot evidence is specific to
  the original port hardware and setup. Baseband is unavailable on both.
- IPSW structural checks and reference hashes do not establish authenticity,
  current signing status, or SEP/baseband compatibility.
- Recovery checks validate supplied files and can compare an ECID. They do not
  inspect a live target volume or make an installed system recoverable.
- Diagnostic capture requires an already paired, running iOS session. DFU,
  recovery, and a diagnostic RAM disk may not offer the required services.
- Device restoration may fail and lose data. The port is unsuitable for daily use.
