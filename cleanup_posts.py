#!/usr/bin/env python3
"""
ONE-OFF CLEANUP: delete specific Threads posts by ID.

These posts went live by mistake because of a bug in publish_threads.py
(reply rows without their own "Tanggal Jadwal" were treated as always-due).
The bug is fixed now; this script removes the orphaned fragments it created.

Ordered so replies are deleted before the post they reply to.

Required environment variable:
  THREADS_ACCESS_TOKEN  Long-lived Threads access token
"""

import os
import sys
import time
import requests

THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
THREADS_API = "https://graph.threads.net/v1.0"

POST_IDS_TO_DELETE = [
    # d1-sore (reply then the fragment it replied to)
    "18103254143241690",
    "18073421381657413",
    # d2-siang
    "17885964993437724",
    # d3-siang
    "18112935665312622",
    "17860957911660766",
    # d3-sore
    "17880927912477375",
    # d4-sore
    "17945875218215285",
    "18252921805307656",
    # d5-siang
    "18110165164955959",
    # d6-siang
    "18107710630820262",
    "18098943893242127",
    # d6-sore
    "18612890092051629",
    # d7-sore
    "17971022190107849",
    "18461790844118987",
]


def main():
    for post_id in POST_IDS_TO_DELETE:
        resp = requests.delete(
            f"{THREADS_API}/{post_id}",
            params={"access_token": THREADS_ACCESS_TOKEN},
            timeout=30,
        )
        if resp.status_code == 200 and resp.json().get("success"):
            print(f"deleted {post_id}")
        else:
            print(f"GAGAL hapus {post_id}: {resp.status_code} {resp.text}", file=sys.stderr)
        time.sleep(2)


if __name__ == "__main__":
    main()
