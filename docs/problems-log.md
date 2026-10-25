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

## 2026-10-25 - Correction: live-feed rows vs recorded activations (observed, about 19:03 Dhaka time)
- My earlier entry said 3 activations. The Live feed tab listed 3 rows matching the condition (11:44:16, 12:15:17, 12:44:52 UTC), but the History tab shows 1 rule activation (12:44:52 UTC).
- Likely reason, not verified: the other two rows arrived before the condition was corrected from 'equal to' to 'less than'; docs say activations run on newly ingested data once a rule starts.
- The single activation was borderline: reported rate -21.46 m/s vs -16.7 m/s derived from altitude change.
- Claim for README: rule running, 1 recorded activation, 3 matching rows in the live feed, notification delivery not verified.

## 2026-10-25 - Dashboard export (observed, about 19:20 Dhaka time)
- Exported OpenSky_Live_Dashboard via Manage > Export to file. The raw file was moved outside the repo.
- The export contained identifiers (dashboard id, eTag, cluster URI, database artifact id, workspace id). Replaced with REDACTED- placeholders (6 occurrences) in fabric-export/OpenSky_Live_Dashboard.sanitized.json.
- First sanitising pass missed the eTag (escaped text); my own leak check had the same blind spot. Fixed with a regex on the eTag line and re-checked by counting occurrences, not lines.
- The sanitized file has no working data source, so it documents the tiles and queries but cannot be re-imported as-is.

## 2026-10-25 - Producer timeouts and recovery (observed in the producer window, Dhaka local time)
- 19:17:20 ReadTimeout and 19:17:51 ConnectTimeout calling OpenSky (my script uses a 30 s timeout). Sends at 19:18:37 and 19:19:31.
- Six consecutive ConnectTimeouts, once a minute, 19:20:51 to 19:25:51. Sends resumed at 19:26:46 and 19:27:31 without restarting the script (it logs the error and tries again at the next interval; no retry logic).
- Credits: 3332 (19:19:31) to 3328 (19:26:46) = 4, so the six connect timeouts were not charged. 3344 (19:15:31) to 3336 (19:18:37) = 8; the ReadTimeout call was probably charged (inference).
- Cause not determined (OpenSky side or my network). I did not run a connectivity test because polling had recovered.
- Failed polls were skipped, so the table has gaps; to be measured with a KQL query.

## 2026-10-25 - Gaps in the data since the 10:43 UTC restart (observed, query run at 13:32 UTC)
- Query lists gaps longer than 90 s between consecutive OpenSky snapshots in rows received since 10:43 UTC.
- Seven gaps (UTC): 12:13:18-12:15:18 (120 s), 12:23:19-12:29:19 (360 s), 12:29:19-12:32:25 (186 s), 12:32:25-12:38:49 (384 s), 12:38:49-12:43:41 (292 s), 13:15:35-13:18:39 (184 s), 13:19:34-13:26:45 (431 s).
- The last two match the producer timeouts (19:17-19:27 Dhaka = 13:17-13:27 UTC). The first five (12:13-12:43 UTC = 18:13-18:43 Dhaka) are unexplained; I did not see the producer window for that period.
- Gaps total 1,957 s between consecutive snapshots (each includes a normal ~60 s interval).
- Consequence: not a continuous 60 s series. The Q5 consistency check only used reading pairs 5-120 s apart, so gaps reduce that sample.

## 2026-10-25 - Final counts after stopping the producer (observed, query run at 13:37 UTC)
- raw_rows 54,587; first_event 2026-10-25 10:16:14 UTC; last_event 2026-10-25 13:34:39 UTC (span 3 h 18 min, with the gaps listed above).
- unique_positions 46,004 (aircraft_clean(): one row per icao24 + position_time); distinct_aircraft about 1,086 (dcount estimate).
- Rows removed by aircraft_clean(): 8,583 (about 15.7 percent of raw); mostly repeated positions, but rows with no position would also be removed (not separately counted for the full table).
- 'Rows' here means ingested events, not distinct readings or aircraft.
