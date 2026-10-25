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

## 2026-10-25 - First producer run (observed)
- opensky_producer.py --once: authenticated, sent 321 events to the Eventstream custom endpoint.
- X-Rate-Limit-Remaining header after 1 call: 3996 (matches 4,000 daily standard allowance minus 4 credits for this box).
- Eventstream source src_opensky shows Active. No destination yet, so these events were not stored.

## 2026-10-25 - Eventhouse ingestion verified (observed)
- Destination dest_eh_opensky (direct ingestion, JSON) created table aircraft_states automatically. The Configure/Get data wizard did not appear in my UI; the panel had a table-name box instead (docs steps differ from my screen).
- Count query returned 2,447 rows while the producer ran at 60 s intervals.
- Schema: snapshot_utc is string; time_position/last_contact are long (epoch seconds). Extra columns added by Eventstream: PartitionId, EventProcessedUtcTime, EventEnqueuedUtcTime.
- To handle in KQL: convert types at query time; same aircraft state can repeat across polls.

## 2026-10-25 - Why a producer script instead of an Eventstream source
- Eventstream has an HTTP source (preview) for REST APIs. The Learn pages I read list Anonymous/Basic/API key auth and say OAuth is not supported (the newest page also lists organizational account and service principal; I did not check what that covers).
- OpenSky now requires OAuth2 client credentials (basic auth not accepted) with 30-minute tokens, so I used a Python producer sending to an Eventstream custom endpoint.
- I did NOT test the HTTP source. Anonymous OpenSky access would be limited to 400 credits/day.

## 2026-10-25 - aircraft_clean() and duplicate check (observed about 16:55 Dhaka time, producer running)
- Created function aircraft_clean(): epoch seconds to datetime, drop rows without a position, keep one row per icao24 + position_time.
- One-pass breakdown: 11,257 raw rows = 0 without position + 9,402 unique positions + 1,855 repeated rows (about 16.5 percent repeats).
- In this sample the whole raw-vs-clean gap is repeats; no rows lacked a position.
- An earlier two-step count (10,916 raw / 9,133 clean) was taken at different moments while data kept arriving, so I did not use it for the repeat rate.

## 2026-10-25 - Dashboard time range label did not match the data (observed)
- First tile showed 'Time range: Last 1 hour' while the chart covered about 10:00-11:15 UTC (more than an hour).
- Learn docs say the built-in time filter stays inactive unless the query uses _startTime/_endTime.
- Fix: added where position_time between (_startTime .. _endTime) to the tile query. Auto refresh enabled afterwards.

## 2026-10-25 - Simple rapid-descent rule was mostly noise (observed, about 17:48 Dhaka time)
- Q5: of 12 readings reported below -20 m/s, 2 matched the altitude change between consecutive readings (within 5 m/s), 10 did not. Small sample (about 85 minutes). Cause of the mismatches not investigated.
- Decision: dashboard tile 2 and the planned alert use the stricter rule (reported rate below -20 m/s AND within 5 m/s of the altitude-derived rate). Expected to fire rarely.

## 2026-10-25 - Activator rule and notification test (observed, about 18:48 Dhaka time)
- Rule rapid_descent_consistent created from dashboard tile 2: condition vertical_rate_ms less than -20, query runs every 5 minutes, action is a Teams message to my own account.
- Mistake: the rule first saved with the condition 'Is equal to -20'. Corrected to 'Is less than' (I had suggested the option without having seen the dropdown).
- Rule status: Running. Activations listed: 3 (position times 11:44:16, 12:15:17 and 12:44:52 UTC), all India-registered aircraft.
- Outlook and Teams on the web did not work for this account. Cause not verified.
- 'Send me a test action' failed with: 'The email test action could not be executed because the email address is not defined in your profile. To resolve a problem, add your email address to your Azure profile.'
- Result so far: rule defined and activations recorded. Notification delivery NOT verified.

## 2026-10-25 - Teams delivery error (observed, about 18:58 Dhaka time)
- A Fabric notification appeared: 'There was an error with the Teams subscription. Please get a Microsoft Office subscription.' I did not determine what triggered it (a real activation or something else).
- Together with the earlier email test failure (no email address in profile) and Outlook/Teams not opening for this account, notification delivery could not be verified.
- Decision: no extra work on delivery. README states: rule defined, activations recorded, delivery not verified.
