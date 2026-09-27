#!/usr/bin/env python3
"""
Set a keyword's own max CPC bid (overrides its ad group's default bid).

    python ads/set-keyword-bid.py 24287062730 "therapist cincinnati" 4.00 --dry-run
    python ads/set-keyword-bid.py 24287062730 "therapist cincinnati" 4.00

Matches the keyword text exactly (case-insensitive) within the campaign and
refuses if that matches more than one keyword. Same auth as apply-pmax-assets.py.
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
    ap.add_argument("bid", type=float)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    rows = [r for r in ads.search(
        "SELECT campaign.id, ad_group.name, ad_group.cpc_bid_micros, ad_group_criterion.resource_name, "
        "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, "
        "ad_group_criterion.effective_cpc_bid_micros FROM ad_group_criterion "
        f"WHERE campaign.id = {args.campaign_id} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED'")
        if r["adGroupCriterion"]["keyword"]["text"].lower() == args.keyword.lower()]
    if len(rows) != 1:
        ads_client.die(f'Expected exactly one keyword "{args.keyword}", found {len(rows)}.')
    r = rows[0]
    crit = r["adGroupCriterion"]
    current = int(crit.get("effectiveCpcBidMicros", r["adGroup"].get("cpcBidMicros", 0))) / 1e6
    print(f'"{crit["keyword"]["text"]}" ({crit["keyword"]["matchType"]}) in {r["adGroup"]["name"]}: '
          f"${current:.2f} -> ${args.bid:.2f}")
    ads.mutate("adGroupCriteria", [{"update": {"resourceName": crit["resourceName"],
                                               "cpcBidMicros": str(int(round(args.bid * 1e6)))},
                                    "updateMask": "cpc_bid_micros"}], args.dry_run)
    print("Validated OK. Nothing changed." if args.dry_run else "Updated.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
