# Problems and fixes log

## 2026-10-25 - OpenSky API check (anonymous, no login)
- Bounding box: lat 5-35, lon 60-100. Called from my Windows 11 machine with PowerShell.
- First call: 364 aircraft, 7029 ms (slow, looks like a cold start).
- Next 4 calls, 15 s apart: 360, 359, 357, 358 aircraft, 873-1053 ms each.
- The api `time` field changed on every call, so the data is live.
- No HTTP 429 or 403 in these 5 calls. Long-run limits NOT yet tested.
- Decision: OpenSky is the primary source. Wikimedia fallback not needed.

## 2026-10-25 - OpenSky auth and credit limits (from official docs)
- Anonymous: 400 credits/day per IP. Standard account: 4,000/day. Basic auth is no longer accepted; OAuth2 client credentials only (token expires after 30 min).
- /states/all costs 4 credits for a box over 400 sq deg. My test box is 1,200 sq deg, so anonymous = about 100 calls/day.
- Decision: create a free account and API client; keep credentials.json outside the repo.
