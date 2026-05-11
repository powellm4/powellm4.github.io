#!/usr/bin/env python3
"""
Hourly Tesla charging-amps adjuster.

Reads the current time in America/Los_Angeles and sets the car's charging amps:
  00:00–09:00 -> 12 A
  09:00–24:00 ->  6 A

Sends the signed command through a tesla-http-proxy listening on localhost:4443.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN_URL = "https://auth.tesla.com/oauth2/v3/token"
PROXY_BASE = "https://localhost:4443"
TZ = ZoneInfo("America/Los_Angeles")


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "scope": "offline_access vehicle_device_data vehicle_charging_cmds",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())["access_token"]


def target_amps_for_hour(hour: int) -> int:
    return 12 if 0 <= hour < 9 else 6


def send_set_amps(access_token: str, vin: str, amps: int):
    url = f"{PROXY_BASE}/api/1/vehicles/{vin}/command/set_charging_amps"
    body = json.dumps({"charging_amps": amps}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read())
        except Exception:
            payload = {"error": "non-JSON response"}
        return e.code, payload


def main() -> int:
    client_id = os.environ["TESLA_CLIENT_ID"]
    client_secret = os.environ["TESLA_CLIENT_SECRET"]
    refresh_token = os.environ["TESLA_REFRESH_TOKEN"]
    vin = os.environ["TESLA_VIN"]

    now = datetime.now(TZ)
    amps = target_amps_for_hour(now.hour)
    print(f"Local time: {now.isoformat()}  target_amps: {amps}")

    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    status, payload = send_set_amps(access_token, vin, amps)
    print(f"Tesla response: {status} {payload}")

    if status >= 400:
        msg = json.dumps(payload).lower()
        # Car not awake / not plugged in -> expected, treat as no-op.
        if (
            status == 408
            or "vehicle_unavailable" in msg
            or "vehicle unavailable" in msg
            or "asleep" in msg
            or "offline" in msg
        ):
            print("Car unavailable (asleep/offline/unplugged). Skipping; not a failure.")
            return 0
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
