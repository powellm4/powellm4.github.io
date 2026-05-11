#!/usr/bin/env python3
"""
One-time helper: exchange a Tesla Fleet API authorization code for a refresh token.

Usage:
  TESLA_CLIENT_ID=... TESLA_CLIENT_SECRET=... \
  python3 scripts/oauth_helper.py

Prints an authorization URL. Open it, log in, approve. Tesla redirects to
https://powellm4.github.io/callback?code=...  (this page does not need to exist
— the redirect just delivers the `code` in the URL bar). Copy the FULL URL
from your browser and paste it back when prompted.
"""
import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
from urllib.parse import urlparse, parse_qs

AUTH_URL = "https://auth.tesla.com/oauth2/v3/authorize"
TOKEN_URL = "https://auth.tesla.com/oauth2/v3/token"
SCOPES = "openid offline_access vehicle_device_data vehicle_charging_cmds"
DEFAULT_REDIRECT = "https://powellm4.github.io/callback"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> int:
    client_id = os.environ["TESLA_CLIENT_ID"]
    client_secret = os.environ["TESLA_CLIENT_SECRET"]
    redirect_uri = os.environ.get("REDIRECT_URI", DEFAULT_REDIRECT)

    state = secrets.token_urlsafe(16)
    code_verifier = b64url(secrets.token_bytes(32))
    code_challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("\n=== Step 1: open this URL in your browser ===\n")
    print(auth_url)
    print()
    print("=== Step 2: after you approve, Tesla redirects to a page that won't")
    print("    load (your redirect URI doesn't actually exist). That's fine — copy")
    print("    the FULL URL from your address bar and paste it below. ===\n")

    redirected = input("Paste full redirected URL: ").strip()
    qs = parse_qs(urlparse(redirected).query)
    if qs.get("state", [None])[0] != state:
        print("ERROR: state mismatch — possible CSRF, or you pasted the wrong URL.",
              file=sys.stderr)
        return 1
    code = qs.get("code", [None])[0]
    if not code:
        print("ERROR: no `code` in the URL.", file=sys.stderr)
        return 1

    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "audience": "https://fleet-api.prd.na.vn.cloud.tesla.com",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())

    print("\n=== SUCCESS ===\n")
    print("Paste this into GitHub Actions secret TESLA_REFRESH_TOKEN:\n")
    print(data["refresh_token"])
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
