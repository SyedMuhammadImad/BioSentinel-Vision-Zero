# Validation receipt

Verified 9 October 2026 on Windows with Python 3.12 and CPU inference. Completion means the documented local prototype and rules workflow, not production biometric certification.

## Automated protocol checks

**54 tests passed.** Disposable SQLite storage and generated keys are used. Coverage includes access/refresh separation, claim tampering, persisted expiry/revocation, refresh reuse and concurrent rotation, single-use/expired/bound challenges, encrypted template corruption, role changes, offline provisioning, atomic failed-login lockout and recovery, identity changes, degenerate geometry, one-eye/static/no-return sequences, malformed uploads, byte/pixel bounds, streaming body caps, provider/scoring/storage outages, rule enforcement floors and invalid/oversized local-model replies.

Positive API flows use labeled synthetic observations to test the protocol contract. They do not prove physical liveness or identity accuracy.

## Browser acceptance

Edge was exercised against the real application routes with a simulated camera and synthetic vision provider: enrollment, sign-in, face re-verification, refresh, sign-out, administrator recovery, explicit camera activation/shutdown, mobile layout and absence of script exceptions. Tokens did not enter browser local/session storage. The user's camera was never accessed. Screenshots remain local and are excluded from this snapshot.

## Actual model execution

The real provider loaded YOLO, MediaPipe Face Landmarker, FaceNet, RetinaFace and MiniFASNet. Blank input was rejected. A public DeepFace test photograph produced a detected face, 478 landmarks, valid open-eye geometry and a finite 128-dimensional embedding. Repeated embedding cosine similarity was **1.0** on that same fixture. This repeatability result is not recognition accuracy.

**Negative evidence:** MiniFASNet labeled that still photograph as real, score **0.8961**, and the provider accepted its single-frame observation. Authentication still requires the separate temporal action sequence, for which static-sequence rejection is tested. This directly limits any claim of photograph/replay attack resistance. No physical presentation-attack benchmark, owner's-camera positive sequence, demographic evaluation or calibrated false accept/reject rate was performed.

Embedding-only smoke inference deliberately disabled anti-spoofing to isolate the embedding path; a separate inference checked the anti-spoof gate enabled. Production observation always enables anti-spoofing with actual face detection. Test fixtures are never selected through a production HTTP endpoint or environment mode.

An actual launcher instance using the real provider and a newly created dedicated database reported ready. Legacy records were not accessed or migrated. Versioned MediaPipe/YOLO downloads matched the retained local asset hashes. Model binaries and the public fixture stay outside GitHub.

## Compatibility and dependency checks

The first real-model setup failed because RetinaFace encountered Keras 3 symbolic tensors. Setting `TF_USE_LEGACY_KERAS=1` before TensorFlow import resolved that failure; the complete model checks then passed. OpenCV base/contrib distributions use the same tested 4.13.0.92 release.

The initial dependency scan reported advisories affecting the previous JWT, image and multipart stack and installer. The release uses PyJWT 2.15.1, Pillow 12.3.0, python-multipart 0.0.31 and the updated installer; the replaced JWT/EC dependency was removed. The subsequent installed-environment scan reported **no known vulnerabilities**. This is advisory-database evidence at verification time, not a guarantee of vulnerability absence. `requirements-lock.txt` pins the tested Windows/Python 3.12 runtime and test dependency closure.

Optional Gemma integration was tested with simulated bounded server replies, not an installed Gemma model. The default rules workflow needs no language-model server.

## Publication checks

Source and retained repository history are scanned for credentials. Public files exclude pictures, videos, private/runtime data, databases and model binaries. The final publication receipt records the pushed commit and the remote file audit. Team attribution and these limitations remain in the public documentation.
