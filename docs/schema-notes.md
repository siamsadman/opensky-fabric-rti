# Schema notes - OpenSky Real-Time Intelligence project
Observed on 2026-10-25.

## Data flow
OpenSky REST API /states/all (bounding box lat 5-35, lon 60-100, OAuth2 client credentials)
-> Python producer (producer/opensky_producer.py, polls every 60 s)
-> Eventstream es-opensky (custom endpoint source src_opensky, Event Hubs protocol)
-> destination dest_eh_opensky (Eventhouse, direct ingestion, JSON)
-> table aircraft_states in KQL database eh_opensky.

## Table aircraft_states (from getschema; created by the Eventhouse destination setup, not by hand)
| Ordinal | Column | Type | Added by |
|---|---|---|---|
| 0 | icao24 | string | producer |
| 1 | callsign | string | producer |
| 2 | origin_country | string | producer |
| 3 | time_position | long (epoch seconds) | producer |
| 4 | last_contact | long (epoch seconds) | producer |
| 5 | longitude | real | producer |
| 6 | latitude | real | producer |
| 7 | baro_altitude | real (m) | producer |
| 8 | on_ground | bool | producer |
| 9 | velocity | real (m/s) | producer |
| 10 | true_track | real | producer |
| 11 | vertical_rate | real (m/s) | producer |
| 12 | geo_altitude | real (m) | producer |
| 13 | squawk | string | producer |
| 14 | spi | bool | producer |
| 15 | position_source | long | producer |
| 16 | snapshot_utc | string | producer |
| 17 | EventProcessedUtcTime | datetime | Eventstream |
| 18 | PartitionId | long | Eventstream |
| 19 | EventEnqueuedUtcTime | datetime | Eventstream |

## Function aircraft_clean() (kql/01_functions.kql)
Converts epoch seconds to datetimes, drops rows with no position, keeps one row per icao24 + position_time (latest by EventEnqueuedUtcTime), adds speed_kmh, and renames altitude and vertical-rate columns with their units.

## Observed quirks
- snapshot_utc is stored as a string; time_position and last_contact are epoch seconds.
- Each poll resends aircraft: in one sample, 1,855 of 11,257 raw rows (about 16.5 percent) were repeated positions.
- origin_country comes from the transponder address per the OpenSky docs, so it is registration country, not where the aircraft is.
- Rapid-descent check: of 12 readings below -20 m/s, only 2 agreed with the altitude-derived rate (tolerance 5 m/s, my choice; about 85 minutes of data).
