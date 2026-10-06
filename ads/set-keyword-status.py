#!/usr/bin/env python3
"""
Pause or re-enable one keyword in a campaign.

    python ads/set-keyword-status.py 24287062730 "therapist cincinnati" EXACT off --dry-run
    python ads/set-keyword-status.py 24287062730 "therapist cincinnati" EXACT off

Matches text (case-insensitive) and match type exactly, and refuses if that
isn't exactly one keyword. Same auth as apply-pmax-assets.py.
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
    ap.add_argument("keyword")
    ap.add_argument("match", choices=["EXACT", "PHRASE", "BROAD"])
    ap.add_argument("state", choices=["on", "off"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    want = "ENABLED" if args.state == "on" else "PAUSED"

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    rows = [r for r in ads.search(
        "SELECT campaign.id, ad_group.name, ad_group_criterion.resource_name, ad_group_criterion.status, "
        "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type FROM ad_group_criterion "
        f"WHERE campaign.id = {args.campaign_id} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED' "
        f"AND ad_group_criterion.keyword.match_type = '{args.match}'")
        if r["adGroupCriterion"]["keyword"]["text"].lower() == args.keyword.lower()]
    if len(rows) != 1:
        ads_client.die(f'Expected one {args.match} keyword "{args.keyword}", found {len(rows)}.')
    crit = rows[0]["adGroupCriterion"]
    print(f'"{args.keyword}" ({args.match}) in {rows[0]["adGroup"]["name"]}: {crit["status"]} -> {want}')
    if crit["status"] == want:
        print("Nothing to change.")
        return
    ads.mutate("adGroupCriteria", [{"update": {"resourceName": crit["resourceName"], "status": want},
                                    "updateMask": "status"}], args.dry_run)
    print("Validated OK. Nothing changed." if args.dry_run else "Done.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
