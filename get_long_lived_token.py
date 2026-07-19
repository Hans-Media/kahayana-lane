#!/usr/bin/env python3
"""
ONE-OFF: exchange an OAuth "code" (from the manual authorize-URL flow) for a
long-lived Threads access token that actually carries the scopes requested
in that authorize URL (e.g. threads_delete), unlike the dashboard's quick
"Generate Token" button which only seems to carry threads_basic +
threads_content_publish for existing testers.

Required environment variables:
  THREADS_APP_ID       Threads/Meta App ID
  THREADS_APP_SECRET   Threads/Meta App Secret
  THREADS_REDIRECT_URI Must exactly match the redirect URI used in the
                        authorize URL and registered in the app settings
  OAUTH_CODE            The "code" query param captured after approving
"""

import os
import sys
import requests

APP_ID = os.environ["THREADS_APP_ID"]
APP_SECRET = os.environ["THREADS_APP_SECRET"]
REDIRECT_URI = os.environ["THREADS_REDIRECT_URI"]
CODE = os.environ["OAUTH_CODE"]

THREADS_API = "https://graph.threads.net"


def main():
    # Step 1: exchange the authorization code for a short-lived token.
    resp = requests.post(
        f"{THREADS_API}/oauth/access_token",
        data={
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": CODE,
        },
        timeout=30,
    )
    print(f"Step 1 (short-lived) status: {resp.status_code}")
    print(resp.text)
    resp.raise_for_status()
    short_lived_token = resp.json()["access_token"]

    # Step 2: exchange the short-lived token for a long-lived token.
    resp = requests.get(
        f"{THREADS_API}/access_token",
        params={
            "grant_type": "th_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "access_token": short_lived_token,
        },
        timeout=30,
    )
    print(f"Step 2 (long-lived) status: {resp.status_code}")
    print(resp.text)
    resp.raise_for_status()
    long_lived_token = resp.json()["access_token"]

    print("\n=== COPY TOKEN INI KE SECRET THREADS_ACCESS_TOKEN ===")
    print(long_lived_token)
    print("=== SELESAI ===")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"GAGAL: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
