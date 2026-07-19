#!/usr/bin/env python3
"""
Publish scheduled content from a Notion database to Threads.

Reads rows with Status = "Terjadwal" from the Notion content-queue database,
posts them to Threads (grouping rows that share the same "Thread Group" into
a single reply-chain thread, ordered by "Urutan"), then writes the result
back to Notion (Status -> "Sudah Posting" / "Gagal", Post ID filled in).

Required environment variables:
  NOTION_TOKEN          Notion internal integration token (starts with "ntn_")
  NOTION_DATA_SOURCE_ID Data source ID of the "Threads Content Queue" database
  THREADS_ACCESS_TOKEN  Long-lived Threads access token (starts with "THAA")
"""

import os
import sys
import time
import datetime
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATA_SOURCE_ID = os.environ["NOTION_DATA_SOURCE_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]

NOTION_VERSION = "2025-09-03"
NOTION_API = "https://api.notion.com/v1"
THREADS_API = "https://graph.threads.net/v1.0"

notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def notion_query_scheduled():
    """Fetch all rows with Status = 'Terjadwal', oldest created first."""
    url = f"{NOTION_API}/data_sources/{NOTION_DATA_SOURCE_ID}/query"
    payload = {
        "filter": {"property": "Status", "select": {"equals": "Terjadwal"}},
        "sorts": [{"timestamp": "created_time", "direction": "ascending"}],
    }
    rows = []
    while True:
        resp = requests.post(url, headers=notion_headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return rows


def get_prop_text(row, name):
    prop = row["properties"].get(name, {})
    t = prop.get("type")
    if t == "title":
        parts = prop.get("title", [])
    elif t == "rich_text":
        parts = prop.get("rich_text", [])
    else:
        return None
    return "".join(p.get("plain_text", "") for p in parts) or None


def get_prop_select(row, name):
    prop = row["properties"].get(name, {})
    sel = prop.get("select")
    return sel["name"] if sel else None


def get_prop_number(row, name):
    prop = row["properties"].get(name, {})
    return prop.get("number")


def get_prop_url(row, name):
    prop = row["properties"].get(name, {})
    return prop.get("url")


def get_prop_date_start(row, name):
    prop = row["properties"].get(name, {})
    date = prop.get("date")
    return date["start"] if date else None


def notion_update_row(page_id, status, post_id=None):
    url = f"{NOTION_API}/pages/{page_id}"
    properties = {"Status": {"select": {"name": status}}}
    if post_id:
        properties["Post ID"] = {"rich_text": [{"text": {"content": post_id}}]}
    resp = requests.patch(url, headers=notion_headers, json={"properties": properties}, timeout=30)
    resp.raise_for_status()


def get_threads_user_id():
    resp = requests.get(
        f"{THREADS_API}/me",
        params={"fields": "id,username", "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"Posting sebagai @{data.get('username')} (id={data['id']})")
    return data["id"]


def post_to_threads(user_id, text, link=None, reply_to_id=None):
    """Create a Threads media container, then publish it. Returns the new post id."""
    create_params = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN,
    }
    if link:
        create_params["link_attachment"] = link
    if reply_to_id:
        create_params["reply_to_id"] = reply_to_id

    resp = requests.post(f"{THREADS_API}/{user_id}/threads", params=create_params, timeout=30)
    resp.raise_for_status()
    creation_id = resp.json()["id"]

    # Threads needs a moment to process the container before it can be published.
    time.sleep(5)

    resp = requests.post(
        f"{THREADS_API}/{user_id}/threads_publish",
        params={"creation_id": creation_id, "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def main():
    rows = notion_query_scheduled()
    if not rows:
        print("Gak ada konten berstatus 'Terjadwal'. Selesai.")
        return

    now = datetime.datetime.now(datetime.timezone.utc)

    # Group by Thread Group first ("" / None = each row is its own standalone
    # thread), THEN decide if the whole group is due. Only the first row
    # (lowest "Urutan") in a group needs a "Tanggal Jadwal" - reply rows are
    # gated by their group's date, not their own (most reply rows have no
    # date set at all, and must NOT be treated as "always due").
    raw_groups = {}
    for row in rows:
        group_key = get_prop_text(row, "Thread Group") or row["id"]
        raw_groups.setdefault(group_key, []).append(row)

    groups = {}
    for group_key, group_rows in raw_groups.items():
        group_rows.sort(key=lambda r: (get_prop_number(r, "Urutan") or 0))
        root = group_rows[0]
        scheduled_at = get_prop_date_start(root, "Tanggal Jadwal")
        if scheduled_at:
            when = datetime.datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            if when > now:
                continue  # whole group (root + replies) not due yet
        groups[group_key] = group_rows

    if not groups:
        print("Ada konten 'Terjadwal' tapi belum jatuh tempo (Tanggal Jadwal di masa depan).")
        return

    user_id = get_threads_user_id()

    for group_key, group_rows in groups.items():
        group_rows.sort(key=lambda r: (get_prop_number(r, "Urutan") or 0))
        print(f"\n=== Thread group: {group_key} ({len(group_rows)} post) ===")
        prev_post_id = None
        for row in group_rows:
            text = get_prop_text(row, "Isi Post") or get_prop_text(row, "Hook / Judul") or ""
            link = get_prop_url(row, "Link")
            try:
                post_id = post_to_threads(user_id, text, link=link, reply_to_id=prev_post_id)
                notion_update_row(row["id"], "Sudah Posting", post_id=post_id)
                print(f"  -> posted OK, id={post_id}")
                prev_post_id = post_id
                time.sleep(3)  # be gentle with the API between posts
            except requests.HTTPError as e:
                print(f"  -> GAGAL: {e.response.status_code} {e.response.text}", file=sys.stderr)
                notion_update_row(row["id"], "Gagal")
                # Stop this group's chain on failure so later replies don't
                # attach to a post that never got published.
                break


if __name__ == "__main__":
    main()
