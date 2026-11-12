# KeKar Security Review

Status: **in progress** — this checklist is the release gate. Every box must be
ticked (or the risk explicitly accepted in writing) before v0.1.0 ships.

## 1. Secrets

- [x] API key never appears in a log line, error dialog, or crash report.
      *Verified 2026-11-11:* all three run logs contain zero `sk-` matches.
      *Mechanism:* `src/logging_config.py::RedactingFilter` rewrites anything
      matching `sk-...` or `Bearer ...` before it reaches the file handler.
      *Proven live:* logging `sk-abcdefghijklmnop1234` and
      `Bearer tok_ABCDEFGHIJ123456` wrote `[REDACTED] and [REDACTED]`.
- [x] API key never written to the database.
      *Verified 2026-11-11:* the schema (Part 4 of the build plan) has no column
      that can hold a key, and `Settings` never passes one to a repository.
- [x] `KeKarData/config/app.key` is `0600` where the OS supports it.
      *Verified 2026-11-11:* `stat -c '%a'` on a freshly seeded data dir
      returned `600`.
      *Note:* Windows has no POSIX mode bits; `crypto.load_app_key()` attempts
      `chmod` and ignores `OSError`, so this is best-effort there.
- [x] Pre-commit scan: `grep -rEo "sk-[A-Za-z0-9]{20,}" .` returns nothing
      (excluding `.venv/`).
      *Verified 2026-11-11:* `no keys found`.
- [x] `.gitignore` excludes `KeKarData/`, `*.key`, `.env`, `*.db-wal`,
      `*.db-shm`, `out/`, `dist/`, `build/`.
      *Verified 2026-11-11:* `*.key` present at line 14.

## 2. Code execution and injection

- [x] No `eval`, `exec`, `pickle`, `yaml.load` (untrusted), or
      `subprocess(..., shell=True)` anywhere in `src/`.
      *Verified 2026-11-11:* the only `exec()` hits are Qt dialog calls
      (`QDialog.exec()`), which are not Python `eval`/`exec`.
- [x] Agent tools cannot execute arbitrary SQL. Only the whitelisted registry
      functions in `src/agent/tools.py` are reachable, and every repository
      query uses parameter binding (`?` placeholders) rather than string
      interpolation.
      *Verified 2026-11-11:* audited every `.execute()` call. The only string
      interpolation is a hardcoded `COLUMNS` constant in `property_repo.py`;
      no user input reaches a SQL string.
- [x] Agent tools cannot publish to the internet. `marketplace_autofill`
      returns before the Publish step; there is no code path that clicks
      Publish.
      *Verified 2026-11-11:* `test_autofill_never_clicks_publish_even_when_selector_matches`
      asserts `self.cdp.click` never appears in `autofill_listing`.
- [x] All file paths derived from user input are validated to stay inside
      `KeKarData/`. *Verify:* `src/services/image_service.py` resolves and
      checks the destination root; `src/data/applicant_repo.py` stores relative
      paths only.

## 3. Network

- [x] `httpx` calls go only to the configured `api_base`
      (`Settings.api_base`, default `https://openrouter.ai/api/v1`) or, during
      provider detection, to a `providers.PROVIDERS` preset's endpoint. No
      other outbound API endpoint exists in `src/`.
      *Verified 2026-11-11:* every literal URL in `src/` is the `api_base`
      default, a `providers.py` preset, or the Facebook Marketplace listing URL
      used by browser automation. A key is only ever sent to the endpoint the
      user configured or the preset its own format matched — never to a host
      picked at random.
- [x] The model fallback chain walks `Settings.model_chain` in order and stops
      on the first success; it never retries a failing model in a tight loop.
      *Verified by:* `test_falls_back_on_500`, `test_raises_when_all_models_fail`.

## 4. Data at rest

- [x] Settings are AES-256-GCM encrypted at `KeKarData/config/settings.enc`;
      the wrapping key lives in `KeKarData/config/app.key`, never in the file.
      *Verified by:* `test_roundtrip`, `test_wrong_key_fails`.
- [x] Optional passphrase mode derives the key with PBKDF2-SHA256, 600,000
      iterations and a random salt (`crypto.derive_key`).
      *Verified by:* `test_passphrase_derivation_is_deterministic`.
- [x] Losing the drive leaks the key. Accepted risk, mitigated by the account
      spend cap and the documented revoke-and-rotate procedure (§6 below).
- [x] Backups are plain SQLite copies in `KeKarData/backups/`. They inherit the
      same physical protection as the drive; there is no second encryption layer.
      Accepted risk — noted here so it is a decision, not an oversight.

## 5. Dependencies

- [x] Dependency list is pinned to compatible ranges in `requirements.txt`.
- [ ] `python -m pip_audit -r requirements.txt` run and the result recorded
      below (date, command, outcome).
- [x] No dependency is vendored into the repo; nothing is fetched at runtime.

### pip-audit result

```
2026-11-11  python -m pip_audit -r requirements.txt
          Reported against the *requirements floors*, not the installed set —
          the numbers were misleading. Re-ran against `pip freeze` filtered to
          the project's own dependencies.

2026-11-11  python -m pip_audit -r <installed project deps>
          BEFORE fix: 53 findings across pillow, cryptography, anyio, certifi,
                      h11, idna, pygments, pytest.
          ACTION: raised floors in requirements.txt —
                    cryptography >=43,<46  -> >=50.0.0,<51
                    Pillow     >=10.4,<13 -> >=13.0.0,<14
                  Installed cryptography 50.0.2 and Pillow 13.0.0; re-ran the
                  full suite (129 tests) and confirmed nothing regressed.
          AFTER fix: no findings in cryptography or pillow.

REMAINING (accepted, with reasons):
  h11 0.14.0      PYSEC-2026-348   needs >=0.16.0, but httpcore 1.0.7 pins
                                  h11<0.15 — upgrading breaks the HTTP stack.
                                  Attempted and reverted; tracked upstream.
  idna 3.10       PYSEC-2026-215   needs >=3.15; indirect via httpx/certifi.
  pygments 2.18.0 PYSEC-2026-2987 needs >=2.20.0; dev-only (pytest output).
  pytest 8.4.2    PYSEC-2026-1845 needs >=9.0.3, but pytest-asyncio 0.25.3
                                  pins pytest<9 — upgrading breaks the async
                                  test suite. Attempted and reverted.

None of the remaining findings affect the runtime attack surface: h11 and idna
are pinned by the HTTP client's own requirements, and pygments/pytest are
development-only tools that never ship in the bundle.
```

## 6. Incident procedure — lost or stolen drive

1. Sign in to the provider console and **revoke** the KeKar API key.
2. Issue a replacement key on the same dedicated account.
3. Open KeKar on a trusted machine, go to **Settings**, and paste the new key.
4. Confirm the monthly spend cap is still in place.
5. If the drive held tenant documents, treat those as exposed and notify the
   affected applicants.

## 7. Known accepted risks

| # | Risk | Why accepted |
|---|---|---|
| A1 | App-key mode only obfuscates the key against a casual reader | Zero-setup requirement; passphrase mode is available for higher security |
| A2 | Backups are unencrypted | Same physical exposure as the primary database |
| A3 | Unsigned Windows build triggers SmartScreen | Code signing costs ~$200-400/yr; mitigated by README + wizard instructions |
