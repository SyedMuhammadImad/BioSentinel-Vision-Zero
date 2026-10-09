# Security scope

BioSentinel is a local prototype for consenting participants. Its tested boundary is the application protocol and local CPU model integration. It is not an independently evaluated biometric system or an operating-system security boundary.

## Enforced boundaries

Access tokens must have valid typed claims, match stored digests and active sessions, and identify active accounts. Roles come from the database. Refresh rotates the token pair; consumed-refresh replay revokes its successor family. Logout and recovery persist revocation before success.

The server issues random short-lived challenges bound to purpose, account, peer network tag and, for re-verification, session. Consumption is atomic and precedes factor evaluation. Ambiguous faces, invalid embeddings, degenerate geometry and oversized uploads are rejected. Required provider failures deny authentication.

Passwords use bcrypt with a 72-byte input limit. Normalized 128-dimensional templates use authenticated encryption. Frames are held transiently in memory. Token hashes, user identifiers, timestamps and keyed network tags are retained in storage. Keyed tags are not anonymization. Backups need the encryption key to preserve usable templates.

## Known limits and unproven boundaries

- Pixels and timestamps are client-controlled. Nonces prevent reusing a protocol request but do not bind pixels to a trusted camera. Prepared sequences, virtual cameras, injected uploads, replay or deepfakes can satisfy visual checks. No hardware-backed camera attestation exists.
- A positive MiniFASNet label on a static picture is not proof of presence. Anti-spoof inference and temporal actions are additional heuristics. No measured physical attack-presentation acceptance rate is available.
- Similarity threshold 0.6, eye/head boundaries and risk thresholds are not calibrated on a qualified population. False accept/reject rates, demographic differences, lighting tolerance and cross-device performance are unmeasured. No positive physical enrollment/sign-in sequence was tested on the owner's camera.
- Landmark geometry is not an identity; FaceNet supplies the separate matching signal. Password-plus-face here is not certified multifactor authentication. Email ownership is not verified.
- Rate limits are per network tag. Distributed abuse is unsolved. Someone knowing a username can deliberately trigger its lockout; an operator must be available for recovery.
- A compromised local process, extension, browser, operating system, administrator or runtime key can defeat controls. Script injection would expose in-memory tokens. Safe DOM rendering and response policy reduce exposure without proving its absence.
- SQLite serialized writes and one CV worker suit a small local demonstration. There is no distributed store, resilient recovery service, retention scheduler or production monitoring. Remote deployment needs separate HTTPS and security review; the supplied launcher binds to loopback.
- Optional Gemma integration uses bounded simulated replies in tests. Actual model deployment and calibrated scoring data are unvalidated. Rules are the default verified mode.

Original biometric records are not imported or modified. Secrets, frames, private databases and model binaries stay outside the public snapshot. Independent biometric evaluation and deployment-specific review are required before stronger security claims.
