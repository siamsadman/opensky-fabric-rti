"""OpenSky -> Fabric Eventstream producer.

Polls OpenSky /states/all for a bounding box and sends one JSON event per
aircraft to a Fabric Eventstream custom endpoint (Event Hubs protocol).
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from azure.eventhub import EventData, EventHubProducerClient
from dotenv import load_dotenv

SECRETS_DIR = Path(r"L:\Python_Env\_secrets\opensky")
CREDENTIALS_FILE = SECRETS_DIR / "credentials.json"
ENV_FILE = SECRETS_DIR / "eventstream.env"

TOKEN_URL = ("https://auth.opensky-network.org/auth/realms/"
             "opensky-network/protocol/openid-connect/token")
STATES_URL = "https://opensky-network.org/api/states/all"
BBOX = {"lamin": 5, "lomin": 60, "lamax": 35, "lomax": 100}

# (index in OpenSky state vector, field name in our event)
FIELDS = [
    (0, "icao24"), (1, "callsign"), (2, "origin_country"),
    (3, "time_position"), (4, "last_contact"),
    (5, "longitude"), (6, "latitude"), (7, "baro_altitude"),
    (8, "on_ground"), (9, "velocity"), (10, "true_track"),
    (11, "vertical_rate"), (13, "geo_altitude"), (14, "squawk"),
    (15, "spi"), (16, "position_source"),
]


def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def load_credentials():
    with open(CREDENTIALS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    norm = {k.lower().replace("_", ""): v for k, v in data.items()}
    cid, secret = norm.get("clientid"), norm.get("clientsecret")
    if not cid or not secret:
        sys.exit("credentials.json: client id/secret not found. Keys present: "
                 + ", ".join(data.keys()))
    return cid, secret


class TokenManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expires_at = 0.0

    def get(self, force=False):
        if force or self.token is None or time.time() >= self.expires_at:
            r = requests.post(TOKEN_URL, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }, timeout=30)
            r.raise_for_status()
            body = r.json()
            self.token = body["access_token"]
            self.expires_at = time.time() + body.get("expires_in", 1800) - 60
        return self.token


def fetch_states(tokens):
    def call(token):
        return requests.get(STATES_URL, params=BBOX, timeout=30,
                            headers={"Authorization": f"Bearer {token}"})
    r = call(tokens.get())
    if r.status_code == 401:  # token expired: get a new one and retry once
        r = call(tokens.get(force=True))
    return r


def to_events(payload):
    snap = payload["time"]
    snap_utc = datetime.fromtimestamp(snap, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    for s in payload.get("states") or []:
        row = {name: (s[i] if i < len(s) else None) for i, name in FIELDS}
        if row["callsign"]:
            row["callsign"] = row["callsign"].strip()
        row["snapshot_utc"] = snap_utc
        yield row


def send(producer, rows):
    batch = producer.create_batch()
    sent = 0
    for row in rows:
        data = EventData(json.dumps(row))
        try:
            batch.add(data)
        except ValueError:  # batch full: send it and start a new one
            producer.send_batch(batch)
            batch = producer.create_batch()
            batch.add(data)
        sent += 1
    if len(batch) > 0:
        producer.send_batch(batch)
    return sent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="poll one time and exit")
    ap.add_argument("--interval", type=int, default=60, help="seconds between polls")
    args = ap.parse_args()

    load_dotenv(ENV_FILE)
    conn = os.environ["EVENTHUB_CONNECTION_STRING"]
    if "EntityPath=" in conn:
        producer = EventHubProducerClient.from_connection_string(conn)
    else:
        producer = EventHubProducerClient.from_connection_string(
            conn, eventhub_name=os.environ["EVENTHUB_NAME"])

    tokens = TokenManager(*load_credentials())

    with producer:
        while True:
            started = time.time()
            wait = args.interval
            try:
                r = fetch_states(tokens)
                remaining = r.headers.get("X-Rate-Limit-Remaining")
                if r.status_code == 429:
                    wait = int(r.headers.get("X-Rate-Limit-Retry-After-Seconds", 60))
                    log(f"HTTP 429 (credits exhausted), waiting {wait}s")
                elif r.ok:
                    n = send(producer, to_events(r.json()))
                    log(f"sent {n} events | credits remaining: {remaining}")
                else:
                    log(f"HTTP {r.status_code} from OpenSky")
            except Exception as e:
                log(f"error: {type(e).__name__}: {e}")
                if args.once:
                    raise
            if args.once:
                break
            time.sleep(max(1, wait - (time.time() - started)))


if __name__ == "__main__":
    main()