# TraceFusion System Limitations & Boundary Conditions

Forensic examiners must understand the technical boundaries and limitations of browser artifact analysis.

---

## 1. Protected & Encrypted Credentials
- **Operating System Security Mechanisms**: Modern Chromium browsers encrypt cookie values and saved passwords using Windows DPAPI (Data Protection API) or AES-256 keys bound to local user login tokens.
- **Forensic Principle**: TraceFusion strictly extracts cookie metadata (domain, name, path, creation time, expiration time, security flags) and explicitly records value status as `Encrypted/Protected`. TraceFusion does not attempt DPAPI credential extraction or unauthorized cryptographic cracking.

---

## 2. In-Memory Artifacts & Incognito / Private Browsing
- In Private / Incognito browsing modes, browser history and session data are held primarily in memory and are discarded when all private windows close.
- Disk-based browser forensics cannot recover private browsing history that was never committed to SQLite database storage on disk. Memory dump acquisition (RAM analysis) would be required for such investigations.

---

## 3. Anti-Forensic Tools & Secure Deletion
- If an anti-forensic tool (e.g. BleachBit, CCleaner) or secure overwrite (`shred`, `sdelete`) has sanitized browser profile files or issued SQLite `VACUUM` commands, deleted records will not be recoverable from database slack.
- Where SQLite Write-Ahead Log (`-wal`) files exist, TraceFusion inspects available uncommitted records.

---

## 4. Cache Payload Reconstruction
- TraceFusion parses cache directory blocks and metadata entries (identifying cached files, sizes, and timestamps).
- Full stream extraction of compressed or fragmented HTTP/2 body streams is dependent on cache block integrity on disk.

---

## 5. Correlated Associations vs. Causation
- TraceFusion correlation outputs identify observed spatial and temporal convergence (e.g. domain access across Chrome and Edge within a short delta).
- Correlated events must **never be presented as technical proof of causation**. Examiners must substantiate correlations with corroborating host, network, and registry evidence.
