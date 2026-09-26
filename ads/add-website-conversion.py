#!/usr/bin/env python3
"""
Create one of the site's website conversion actions and print the send_to
value the site's tag needs. Both are fired from tracking.js.

  phone-tap      "Phone number tapped", primary. Round one only counted calls
                 placed from the ad itself; anyone who reached the site and
                 tapped the number was invisible to Google Ads.
  engaged-visit  "Engaged visit", SECONDARY (reported under All conversions,
                 never counted as a lead). An ad visitor who stayed 30 visible
                 seconds or scrolled halfway, so the dashboard can tell "wrong
                 people clicked" apart from "right people, page didn't land".

Safe to re-run: if the action already exists it just prints its send_to.
Same auth as apply-pmax-assets.py.

    python ads/add-website-conversion.py engaged-visit --dry-run
    python ads/add-website-conversion.py engaged-visit
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

PRESETS = {
    "phone-tap": {"name": "Phone number tapped", "category": "PHONE_CALL_LEAD", "primary": True},
    "engaged-visit": {"name": "Engaged visit", "category": "ENGAGEMENT", "primary": False},
}


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
    ap.add_argument("action", choices=sorted(PRESETS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    preset = PRESETS[args.action]
    NAME = preset["name"]

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
        "category": preset["category"],
        "status": "ENABLED",
        "countingType": "ONE_PER_CLICK",
        "primaryForGoal": preset["primary"],
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
