#!/usr/bin/env python3
"""
Turn a campaign on or off.

    python ads/set-campaign-status.py 24287062730 on --dry-run
    python ads/set-campaign-status.py 24287062730 on
    python ads/set-campaign-status.py 24287062730 off

Only touches campaign.status. Same auth as apply-pmax-assets.py.
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("ads_client", Path(__file__).with_name("apply-pmax-assets.py"))
ads_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ads_client)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_id")
    ap.add_argument("state", choices=["on", "off"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    want = "ENABLED" if args.state == "on" else "PAUSED"

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    rows = ads.search(f"SELECT campaign.name, campaign.status FROM campaign WHERE campaign.id = {args.campaign_id}")
    if not rows:
        ads_client.die(f"No campaign {args.campaign_id}.")
    c = rows[0]["campaign"]
    print(f'"{c["name"]}" is {c["status"]}')
    if c["status"] == want:
        print("Nothing to change.")
        return
    ads.mutate("campaigns", [{"update": {"resourceName": c["resourceName"], "status": want}, "updateMask": "status"}],
               args.dry_run)
    print("Validated OK. Nothing changed." if args.dry_run else f"Now {want}.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
