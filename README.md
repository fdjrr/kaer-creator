# Kaer API — account creator

Creates api.kaer.ai accounts over pure HTTP: email-OTP signup via emailqu temp mail,
reads the free-credit grant, mints the `kaer_live_...` API key, logs to JSONL.

## Usage

```bash
uv run python main.py -n 3 -w 3                # 3 accounts, 3 workers
uv run python main.py -n 1 --proxy-file proxies.txt
uv run python main.py -n 1 --smoke             # also fire a real chat call per key
```

Excel-style config via env (CLI wins): `KAER_BASE`, `KAER_OUTPUT`, `KAER_PROXY_FILE`.

## Output

`credentials.jsonl` — one record per account:

```json
{"email":"kaer12ab34cd@odynex.online","key":"kaer_live_...","key_id":"3196",
 "grant":"granted","grant_decision":"granted","free_credit_usd":10}
```

The key is the deliverable; `grant`/`grant_decision`/`free_credit_usd` come from the
portal account endpoint and tell you whether the account received the free $10 credit
(`grant_decision: granted` = yes, `denied:ip_claimed` = this egress already claimed one).

## Recon / endpoints

All reverse-engineered from the site bundle (2026-10-25):

| Endpoint | Purpose |
|---|---|
| `POST /api/apiplat/auth/code` `{email}` | send 6-digit OTP (10 min expiry, one active code per email — newest wins) |
| `POST /api/apiplat/auth/verify` `{email,code,agreed}` | verify, sets `kaer_api_portal` session cookie, returns `{created, grant, status}` |
| `GET /api/apiplat/auth/session` | signed-in oracle |
| `POST /api/apiplat/keys` `{name}` | mint key → `{ok, secret: "kaer_live_...", key}` |
| `GET /api/apiplat/keys` | list keys |
| `GET /api/apiplat/account` | balance, `grantDecision`, tier |
| `GET /api/apiplat/billing` | billing overview |
| `GET /api/apiplat/v1/models` | model list (portal) / `GET /v1/models` with the key |
| `POST /v1/chat/completions` | OpenAI-compatible (Authorization: Bearer <key>) |

Auth notes:
- `Origin: https://api.kaer.ai` is **required** on the auth endpoints (403 "origin
  required" without it; a foreign origin → "cross-origin request refused").
- No CSRF token on the OTP or key endpoints.
- One active OTP per email; requesting a new code invalidates the previous one
  (only the newest works). Poll index 0 of the emailqu inbox (newest first).
- Cooldowns: `429 "Too many codes requested"` per email, `verify` → `locked` after
  too many bad attempts (send a fresh code to clear).
- Free-credit grant is **per-IP, one claim per egress**: the first account from an IP
  gets `grant: "granted"` / `freeCreditUsd: 10`; a second account from the same IP gets
  `grantDecision: "denied:ip_claimed"` and zero free credit. Use a fresh proxy egress
  per grant-carrying account.

## Anti-bot

None on the signup/auth flow (no captcha, no Turnstile). Cloudflare in front is
plain pass-through. TLS impersonation not needed.

## Project layout

```
main.py                # asyncio orchestration + banner + config log (entry: uv run python main.py)
conftest.py            # sys.path[0] = repo root for pytest
extract_api_keys.py    # JSONL/JSON -> keys.txt
src/
  __init__.py
  cli.py               # parse_args() + _env() dual-mode (KAER_*)
  emailqu.py           # async EmailquClient
  kaer.py              # KaerClient (portal + v1)
  proxy.py             # ProxyPool (round-robin)
  storage.py           # JsonlStore
```

## Development

```bash
uv sync
uv run pytest
```
