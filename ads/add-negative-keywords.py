#!/usr/bin/env python3
"""
Add campaign-level negative keywords, skipping any that already exist.

Used during the week-one search term reviews. Single words go in as broad
negatives (blocks any search containing the word), phrases as phrase negatives.

    python ads/add-negative-keywords.py 24287062730 lifestance ostendorf --dry-run
    python ads/add-negative-keywords.py 24287062730 lifestance ostendorf

Same auth as apply-pmax-assets.py.
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
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    have = {r["campaignCriterion"]["keyword"]["text"].lower() for r in ads.search(
        "SELECT campaign.id, campaign_criterion.keyword.text FROM campaign_criterion "
        f"WHERE campaign.id = {args.campaign_id} AND campaign_criterion.negative = TRUE "
        "AND campaign_criterion.type = 'KEYWORD'")}
    new = [t.lower().strip() for t in args.terms if t.lower().strip() not in have]
    for t in args.terms:
        if t.lower().strip() in have:
            print(f"  already blocked: {t}")
    if not new:
        print("Nothing to add.")
        return
    camp = f"customers/{ads_client.CUSTOMER_ID}/campaigns/{args.campaign_id}"
    ops = [{"create": {"campaign": camp, "negative": True,
                       "keyword": {"text": t, "matchType": "PHRASE" if " " in t else "BROAD"}}} for t in new]
    ads.mutate("campaignCriteria", ops, args.dry_run)
    for t in new:
        print(f"  {'would block' if args.dry_run else 'blocked'}: {t}")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
