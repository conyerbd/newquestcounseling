#!/usr/bin/env python3
"""
Create the "Phone number tapped" website conversion action and print the
send_to value the site's tag needs.

Round one only counted calls placed from the ad itself ("Calls from ads").
Someone who reached the site and tapped the phone number was invisible to
Google Ads. This action is fired by tracking.js on any tel: link click.

Safe to re-run: if the action already exists it just prints its send_to.
Same auth as apply-pmax-assets.py.

    python ads/add-phone-tap-conversion.py --dry-run
    python ads/add-phone-tap-conversion.py
"""
import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("ads_client", Path(__file__).with_name("apply-pmax-assets.py"))
ads_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ads_client)

NAME = "Phone number tapped"


def send_to(ads, resource_name):
    rows = ads.search(
        "SELECT conversion_action.tag_snippets FROM conversion_action "
        f"WHERE conversion_action.resource_name = '{resource_name}'"
    )
    for snip in rows[0]["conversionAction"].get("tagSnippets", []):
        m = re.search(r"'send_to':\s*'([^']+)'", snip.get("eventSnippet", ""))
        if m:
            return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()

    existing = ads.search(
        "SELECT conversion_action.resource_name, conversion_action.status FROM conversion_action "
        f"WHERE conversion_action.name = '{NAME}'"
    )
    live = [r for r in existing if r["conversionAction"]["status"] != "REMOVED"]
    if live:
        rn = live[0]["conversionAction"]["resourceName"]
        print(f"Already exists: {rn}\nsend_to: {send_to(ads, rn)}")
        return

    op = {"create": {
        "name": NAME,
        "type": "WEBPAGE",
        "category": "PHONE_CALL_LEAD",
        "status": "ENABLED",
        "countingType": "ONE_PER_CLICK",
        "primaryForGoal": True,
        "valueSettings": {"defaultValue": 1.0, "alwaysUseDefaultValue": True},
        "clickThroughLookbackWindowDays": 30,
    }}
    result = ads.mutate("conversionActions", [op], args.dry_run)
    if args.dry_run:
        print("Validated OK. Nothing created.")
        return
    rn = result["results"][0]["resourceName"]
    print(f"Created: {rn}\nsend_to: {send_to(ads, rn)}")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
