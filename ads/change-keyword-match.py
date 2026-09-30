#!/usr/bin/env python3
"""
Switch a keyword to a different match type, with its own bid.

Google won't edit a keyword's match type in place, so this adds the new
version to the same ad group and pauses the old one (paused, not removed,
so its history stays in reports). Both happen in one atomic request.

    python ads/change-keyword-match.py 24287062730 "therapist cincinnati" EXACT 6.00 --dry-run
    python ads/change-keyword-match.py 24287062730 "therapist cincinnati" EXACT 6.00

Requests the "Health in personalized advertising" exemption if Google flags
the new keyword, same as create-search-campaign.py, and fails on anything else.
Same auth as apply-pmax-assets.py.
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
_here = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("ads_client", _here / "apply-pmax-assets.py")
ads_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ads_client)
_spec2 = importlib.util.spec_from_file_location("create_campaign", _here / "create-search-campaign.py")
create_campaign = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(create_campaign)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_id")
    ap.add_argument("keyword")
    ap.add_argument("match", choices=["EXACT", "PHRASE", "BROAD"])
    ap.add_argument("bid", type=float)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    rows = [r for r in ads.search(
        "SELECT campaign.id, ad_group.resource_name, ad_group.name, ad_group_criterion.resource_name, "
        "ad_group_criterion.status, ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type "
        f"FROM ad_group_criterion WHERE campaign.id = {args.campaign_id} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED'")
        if r["adGroupCriterion"]["keyword"]["text"].lower() == args.keyword.lower()]
    if any(r["adGroupCriterion"]["keyword"]["matchType"] == args.match for r in rows):
        ads_client.die(f'"{args.keyword}" already exists as {args.match}. Nothing changed.')
    old = [r for r in rows if r["adGroupCriterion"]["status"] == "ENABLED"]
    if len(old) != 1:
        ads_client.die(f'Expected one enabled "{args.keyword}", found {len(old)}.')
    old = old[0]
    ag = old["adGroup"]
    print(f'{ag["name"]}: add "{args.keyword}" as {args.match} at ${args.bid:.2f}, '
          f'pause the {old["adGroupCriterion"]["keyword"]["matchType"]} version')

    ops = [
        {"adGroupCriterionOperation": {"create": {
            "adGroup": ag["resourceName"], "status": "ENABLED",
            "cpcBidMicros": str(int(round(args.bid * 1e6))),
            "keyword": {"text": args.keyword, "matchType": args.match}}}},
        {"adGroupCriterionOperation": {"update": {
            "resourceName": old["adGroupCriterion"]["resourceName"], "status": "PAUSED"},
            "updateMask": "status"}},
    ]

    def send():
        return ads._post(f"customers/{ads_client.CUSTOMER_ID}/googleAds:mutate",
                         {"mutateOperations": ops, "validateOnly": args.dry_run})

    try:
        send()
    except ads_client.ApiError as e:
        exempt = create_campaign.exemptible_health_keywords(e, ops)
        if exempt is None:
            raise
        for i, key in exempt:
            ops[i]["adGroupCriterionOperation"].setdefault("exemptPolicyViolationKeys", []).append(key)
            print(f"  requesting the health-personalization exemption for: {key['violatingText']}")
        send()
    print("Validated OK. Nothing changed." if args.dry_run else "Done.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
