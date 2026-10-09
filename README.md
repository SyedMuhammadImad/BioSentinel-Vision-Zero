# BioSentinel

A working local authentication prototype combining a password, a face template and a fresh server-issued camera challenge. The browser supports enrollment, sign-in, face re-verification, session refresh, sign-out and administrator recovery. This release implements and tests the application flow; it does not certify biometric accuracy or physical attack resistance.

## Run locally

Use Python **3.12** in a dedicated environment. The tested platform is Windows with CPU inference. Installation and first model startup need internet access and several gigabytes of free disk space.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe setup_models.py
.venv\Scripts\python.exe run_local.py
```

For the exact tested Windows/Python 3.12 dependency set, install `requirements-lock.txt` instead of `requirements.txt`.

Open **http://127.0.0.1:8000**. Wait for models to become ready, choose **Start camera**, then create an account. Follow the displayed action during capture and finish facing forward with both eyes open. A challenge lasts 45 seconds and is consumed once. Failed attempts need a new challenge. Sign in separately after enrollment. Camera access requires localhost or HTTPS.

The launcher generates signing and encryption keys in `private/runtime.json` and uses a dedicated `private/biosentinel.db`. It keeps model caches under `private/` and binds only to loopback, with forwarded-header trust disabled. Protect this folder and back up the encryption key with the database: losing the key makes templates unreadable. Windows permissions are inherited; the launcher does not secure a compromised local account.

For another private directory or preinstalled weights:

```powershell
.venv\Scripts\python.exe run_local.py --private-dir D:\BioSentinelPrivate --weights-dir D:\BioSentinelWeights
```

`setup_models.py` downloads two versioned assets and checks their tested SHA-256 hashes. DeepFace downloads FaceNet, RetinaFace and MiniFASNet weights into the local cache on first startup. Read each provider's license before using its software or weights in another product. Model files, pictures, videos, secrets and databases are excluded from this repository.

## Administrator recovery

Every browser enrollment receives the user role. There is no default administrator, public role-grant endpoint or account-reset helper. Enroll an operator, stop the server, and run the explicit offline command using the **same private directory**:

```powershell
.venv\Scripts\python.exe run_local.py --grant-admin operator
```

Provisioning records an event and revokes existing sessions. Sign in again and unblock locked accounts from the recovery panel. Three failed factor checks in a UTC day lock an account and revoke its sessions. Recovery clears failures and keeps old sessions revoked. This lockout can be abused to deny another user access; use only with consenting local participants and an available operator.

## Implemented controls

- Typed expiring HS256 tokens with issuer/audience validation and a persisted session check. Refresh tokens cannot serve as access tokens.
- Digest-only token storage, rotating refresh families, replay detection, logout revocation and database-backed roles.
- Purpose/account/network/session-bound challenges; temporal open/action/return checks; one-face selection; bounded uploads; encrypted finite 128-dimensional FaceNet templates.
- Atomic lockout, revocation and event writes. Database/model/scoring failures deny authentication.
- Explicit camera activation and track shutdown, safe DOM rendering, response protections and tokens held only in page memory. Reloading clears the interface; sign out to revoke the server session.
- No retained frame files or raw tokens/templates in events. User identifiers, timestamps and keyed network tags remain; these records are not anonymous.

## Risk scoring and configuration

The default `BIOSENTINEL_RISK_MODE=rules` uses deterministic local rules. Face mismatch forces a critical score; borderline similarity, changed network, repeated failures and high activity raise it. A score of 70 requires full sign-in; 90 locks the account. These thresholds are heuristics, not calibrated probabilities.

Optional `BIOSENTINEL_RISK_MODE=gemma` requires a separately managed local OpenAI-compatible server. Set `BIOSENTINEL_LM_URL` to its loopback `/v1` endpoint and `BIOSENTINEL_LM_MODEL` to its installed model identifier. Only bounded scalar metadata is sent. Malformed, oversized or unavailable replies revoke the checked session and fail closed. The model cannot lower the rule floor. The adapter was tested with simulated responses; actual Gemma deployment is unvalidated and is not required for the default workflow.

Advanced overrides: `BIOSENTINEL_SECRET_KEY`, `BIOSENTINEL_ENCRYPTION_KEY`, `BIOSENTINEL_DATABASE_URL`, `BIOSENTINEL_WEIGHTS_DIR`. Keep supplied values outside source control. Importing the application without valid keys fails; the launcher generates keys without printing them. `TF_USE_LEGACY_KERAS=1` must be set before any TensorFlow import; the launcher/provider set it for the tested runtime.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
```

Tests generate keys and a disposable database without using existing enrollments or a real camera. Successful API/browser flows use an explicit synthetic vision provider confined to test fixtures. Real model loading, detection, landmarks, repeat embeddings, blank rejection and anti-spoof inference are checked separately. See [VALIDATION.md](VALIDATION.md), [THREAT_MODEL.md](THREAT_MODEL.md) and `VERIFICATION.json` for exact scope and limitations.

Version 2 uses separate database tables. It does not migrate plaintext templates, reuse legacy sessions, activate old accounts or modify the original database. Re-enrollment requires consent. The old reset helper and unrestricted demo path are absent.

Upstream team source: [Xavierfied/BioSentinel-Vision-Zero](https://github.com/Xavierfied/BioSentinel-Vision-Zero). This maintained snapshot includes subsequent remediation and preserves team attribution; it is not a sole-authorship claim. See [ATTRIBUTION.md](ATTRIBUTION.md).
