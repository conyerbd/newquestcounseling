#!/usr/bin/env python3
"""
Apply the planned asset fixes to the New Quest Counseling Performance Max
asset group.

Stdlib only. Auth comes from Application Default Credentials via the gcloud
CLI, which is how the google-ads-mcp server in .mcp.json is already set up.
ADC must carry the adwords scope:

    gcloud auth application-default login \
      --scopes=https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform

Usage:
    python ads/apply-pmax-assets.py --dry-run   # validateOnly, changes nothing
    python ads/apply-pmax-assets.py             # apply

What it does, in two phases:

  1. Uploads ads/ad1-vertical-4x5.png and ads/ad2-vertical-4x5.png as image
     assets, if not already present in the account.
  2. Sends one atomic assetGroupAssets:mutate containing every link and unlink
     below, so Google validates the final state rather than an intermediate
     one. Ordering matters here: removing the only description under 60
     characters before adding its replacement would be rejected.

The script reads current state first and skips anything already correct, so it
is safe to re-run.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

CUSTOMER_ID = "1838861154"        # New Quest Counseling, the serving account
LOGIN_CUSTOMER_ID = "1713871701"  # the manager account above it
ASSET_GROUP_ID = "6742123859"     # Asset Group 1

# Tried in order; the first that answers a read is used.
API_VERSIONS = ["v22", "v21", "v20", "v19"]

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# The plan. Asset ids are existing assets already in the account library.
# ---------------------------------------------------------------------------

# Orphaned text assets to link into the asset group.
LINK_TEXT = [
    ("411979665965", "HEADLINE", "Get therapy in Cincinnati, OH"),
    ("411979665974", "HEADLINE", "Therapy in Cincinnati, OH"),
    ("411979665983", "LONG_HEADLINE", "Therapy in Cincinnati, Ohio with Dorasae Rosario, LPCC"),
    ("411979665977", "LONG_HEADLINE", "Individual, couples, and family counseling"),
    ("411979665968", "LONG_HEADLINE", "New Quest Counseling | Therapy in Cincinnati, OH"),
    # This one is the under-60 description Performance Max requires. It has to
    # land in the same mutate that removes "New Quest Counseling".
    ("411979665971", "DESCRIPTION", "Anxiety, burnout, and life transitions"),
    ("411979665986", "DESCRIPTION", "Now accepting Anthem and UnitedHealthcare, plus sliding-scale self-pay"),
    ("411979691693", "DESCRIPTION", "Get therapy for anxiety, burnout, and life transitions"),
]

# Local files to upload, then link as 4:5 portrait.
UPLOAD_IMAGES = [
    ("ads/ad1-vertical-4x5.png", "PORTRAIT_MARKETING_IMAGE"),
    ("ads/ad2-vertical-4x5.png", "PORTRAIT_MARKETING_IMAGE"),
]

# (asset_id, field_type) pairs to unlink. Targeted by pair, not by asset,
# because several assets legitimately occupy more than one slot.
UNLINK = [
    ("411350575034", "HEADLINE", 'stale: "New Year, New Challenges"'),
    ("411350575034", "LONG_HEADLINE", "stale, and a 25-char string in a 90-char slot"),
    ("411350666189", "LONG_HEADLINE", "short headline padding a long headline slot"),
    ("411454875568", "LONG_HEADLINE", "short headline padding a long headline slot"),
    ("411346143850", "DESCRIPTION", "business name used as a description"),
    ("411456597385", "DESCRIPTION", "cut to make room; weakest of the five"),
    ("411350666192", "DESCRIPTION", "duplicate of asset 411527494665; keeps its LONG_HEADLINE row"),
    ("411350752160", "SQUARE_MARKETING_IMAGE", "logo tile in the square rotation; stays the campaign logo"),
]


def die(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def find_gcloud():
    """Locate the gcloud launcher. On Windows it is gcloud.cmd, which
    subprocess will not resolve from the bare name."""
    override = os.environ.get("GCLOUD")
    if override:
        return override
    for name in ("gcloud", "gcloud.cmd", "gcloud.exe"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        os.path.expanduser(
            r"~\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    die("gcloud not found. Set the GCLOUD env var to its full path.")


def access_token():
    """Mint an ADC access token via gcloud. Never printed or written to disk."""
    exe = find_gcloud()
    try:
        out = subprocess.run(
            [exe, "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True,
        )
    except OSError as e:
        die(f"could not run {exe}: {e}")
    except subprocess.CalledProcessError as e:
        die(f"gcloud could not mint a token:\n{e.stderr.strip()}")
    token = out.stdout.strip()
    if not token:
        die("gcloud returned an empty token.")
    return token


class Ads:
    def __init__(self, token, dev_token):
        self.token = token
        self.dev_token = dev_token
        self.version = None

    def _post(self, path, body):
        url = f"https://googleads.googleapis.com/{self.version}/{path}"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "developer-token": self.dev_token,
                "login-customer-id": LOGIN_CUSTOMER_ID,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, e.read().decode(errors="replace")) from None

    def detect_version(self):
        probe = {"query": "SELECT customer.id FROM customer LIMIT 1"}
        last = None
        for v in API_VERSIONS:
            self.version = v
            try:
                self._post(f"customers/{CUSTOMER_ID}/googleAds:search", probe)
                print(f"Using Google Ads API {v}")
                return
            except ApiError as e:
                last = e
                if e.status == 404:
                    continue  # wrong version, try the next
                break
        self.version = None
        hint = ""
        if last and last.status in (401, 403):
            hint = (
                "\n\nThis usually means ADC is missing the adwords scope. Re-run:\n"
                "  gcloud auth application-default login "
                "--scopes=https://www.googleapis.com/auth/adwords,"
                "https://www.googleapis.com/auth/cloud-platform"
            )
        die(f"no working API version.\n{last}{hint}")

    def search(self, query):
        rows, token = [], None
        while True:
            body = {"query": query}
            if token:
                body["pageToken"] = token
            page = self._post(f"customers/{CUSTOMER_ID}/googleAds:search", body)
            rows.extend(page.get("results", []))
            token = page.get("nextPageToken")
            if not token:
                return rows

    def mutate(self, resource, operations, validate_only):
        return self._post(
            f"customers/{CUSTOMER_ID}/{resource}:mutate",
            {"operations": operations, "validateOnly": validate_only},
        )


class ApiError(Exception):
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload
        try:
            d = json.loads(payload)
            msgs = []
            for f in d.get("error", {}).get("details", []):
                for err in f.get("errors", []):
                    msgs.append(err.get("message", ""))
            detail = "; ".join(m for m in msgs if m) or d.get("error", {}).get("message", payload)
        except Exception:
            detail = payload
        super().__init__(f"HTTP {status}: {detail}")


def current_state(ads):
    """Existing asset group links, keyed by (asset_id, field_type)."""
    rows = ads.search(
        "SELECT asset_group_asset.resource_name, asset_group_asset.field_type, "
        "asset_group_asset.status, asset.id "
        "FROM asset_group_asset "
        f"WHERE asset_group.id = {ASSET_GROUP_ID}"
    )
    state = {}
    for r in rows:
        aga = r["assetGroupAsset"]
        key = (str(r["asset"]["id"]), aga["fieldType"])
        state[key] = {"resource_name": aga["resourceName"], "status": aga["status"]}
    return state


def existing_image_ids(ads, names):
    """Map asset name -> resource name for images already uploaded."""
    if not names:
        return {}
    quoted = ", ".join(f"'{n}'" for n in names)
    rows = ads.search(
        "SELECT asset.resource_name, asset.name FROM asset "
        f"WHERE asset.type = IMAGE AND asset.name IN ({quoted})"
    )
    return {r["asset"]["name"]: r["asset"]["resourceName"] for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="send every mutate with validateOnly=true and change nothing")
    args = ap.parse_args()

    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not dev_token:
        die("GOOGLE_ADS_DEVELOPER_TOKEN is not set.")

    ads = Ads(access_token(), dev_token)
    ads.detect_version()

    mode = "DRY RUN (validateOnly, nothing is changed)" if args.dry_run else "APPLYING CHANGES"
    print(f"\n=== {mode} ===")
    print(f"Account {CUSTOMER_ID}, asset group {ASSET_GROUP_ID}\n")

    state = current_state(ads)

    # ---- Phase 1: upload the two missing 4:5 images -----------------------
    wanted = {}
    to_upload = []
    for rel, field in UPLOAD_IMAGES:
        path = REPO_ROOT / rel
        if not path.exists():
            die(f"{rel} not found.")
        wanted[path.name] = field
        to_upload.append((path, field))

    already = existing_image_ids(ads, list(wanted))
    for name, rn in already.items():
        print(f"  image already in account, reusing: {name}")

    image_ops, pending = [], []
    for path, field in to_upload:
        if path.name in already:
            continue
        data = path.read_bytes()
        image_ops.append({"create": {
            "name": path.name,
            "type": "IMAGE",
            "imageAsset": {"data": base64.b64encode(data).decode()},
        }})
        pending.append((path.name, field))

    uploaded = {}
    if image_ops:
        print(f"\nPhase 1: uploading {len(image_ops)} image asset(s)")
        for name, _ in pending:
            print(f"  + {name}")
        result = ads.mutate("assets", image_ops, args.dry_run)
        returned = [r.get("resourceName") for r in result.get("results", [])]
        if args.dry_run:
            print("  validated OK (no asset ids exist yet, so linking is skipped below)")
        else:
            for (name, _), rn in zip(pending, returned):
                uploaded[name] = rn
                print(f"    -> {rn}")
    else:
        print("\nPhase 1: nothing to upload")

    # ---- Phase 2: one atomic link/unlink mutate --------------------------
    ag = f"customers/{CUSTOMER_ID}/assetGroups/{ASSET_GROUP_ID}"
    ops, plan = [], []

    def link(asset_rn, field, label):
        ops.append({"create": {"assetGroup": ag, "asset": asset_rn, "fieldType": field}})
        plan.append(f"  LINK   {field:<30} {label}")

    for asset_id, field, text in LINK_TEXT:
        entry = state.get((asset_id, field))
        if entry and entry["status"] == "ENABLED":
            print(f"  already linked, skipping: {field} / {text[:50]}")
            continue
        link(f"customers/{CUSTOMER_ID}/assets/{asset_id}", field, f'"{text}"')

    for name, field in wanted.items():
        rn = uploaded.get(name) or already.get(name)
        if not rn:
            continue  # dry run, asset does not exist yet
        asset_id = rn.rsplit("/", 1)[-1]
        entry = state.get((asset_id, field))
        if entry and entry["status"] == "ENABLED":
            print(f"  already linked, skipping: {field} / {name}")
            continue
        link(rn, field, name)

    for asset_id, field, why in UNLINK:
        entry = state.get((asset_id, field))
        if not entry:
            print(f"  no such link, skipping: {field} / asset {asset_id}")
            continue
        if entry["status"] == "REMOVED":
            print(f"  already removed, skipping: {field} / asset {asset_id}")
            continue
        ops.append({"remove": entry["resource_name"]})
        plan.append(f"  UNLINK {field:<30} {why}")

    if not ops:
        print("\nPhase 2: nothing to change. Asset group already matches the plan.")
        return

    print(f"\nPhase 2: {len(ops)} operation(s) in one atomic mutate")
    for line in plan:
        print(line)

    ads.mutate("assetGroupAssets", ops, args.dry_run)
    print("\nValidated OK." if args.dry_run else "\nApplied.")

    if not args.dry_run:
        print("\nResulting slot counts:")
        rows = ads.search(
            "SELECT asset_group_asset.field_type FROM asset_group_asset "
            f"WHERE asset_group.id = {ASSET_GROUP_ID} "
            "AND asset_group_asset.status = ENABLED"
        )
        counts = {}
        for r in rows:
            ft = r["assetGroupAsset"]["fieldType"]
            counts[ft] = counts.get(ft, 0) + 1
        for ft in sorted(counts):
            print(f"  {ft:<32} {counts[ft]}")
        print("\nAd strength is recomputed by Google over the next several hours,")
        print("so do not expect POOR to change immediately.")


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        die(str(e))
