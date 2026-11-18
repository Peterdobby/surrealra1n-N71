# v0.1.0-alpha

Experimental iPhone 6s iOS 16.2 port input validation for surrealra1n-N71,
based on surrealra1n by pwnerblu. This alpha can identify N71AP, validate
user-supplied IPSW metadata, and verify existing Stage 18U and Stage 18W
reference exports and Stage 18U recovery files. It builds a reproducible host
evidence ZIP with firmware input hashes and supports bounded diagnostic collection
from paired iOS. Stage 18W remains untested on device. Firmware generation,
installation, boot and cellular service are unavailable in this release.

The N71 contribution contains original validation code, tests, and
documentation. Its tests generate synthetic firmware metadata locally.
Firmware payloads, private device files and personal signing data are external.
The public repository contains the N71 source only. It retains pwnerblu's
attribution, Apache-2.0 LICENSE and NOTICE. The full development fork and
its upstream history are maintained locally.
