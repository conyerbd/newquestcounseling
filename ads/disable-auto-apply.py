#!/usr/bin/env python3
"""
Turn off Google's auto-apply recommendations for the account.

Auto-apply was on from the account's setup (2026-08-25). On 2026-09-27 its
"Maximize conversions" opt-in silently switched round two off manual CPC,
after which clicks cost $10 to $30 against $6 to $7 bids. Other enabled
types can add keywords or edit ad text, which would also break the A/B test.

Pauses every enabled subscription the API can address. Some come back with
type UNKNOWN (newer than the API version); those are attempted one by one
and any the API refuses are listed, to be turned off in the Google Ads
website under Recommendations > Auto-apply.

    python ads/disable-auto-apply.py --dry-run
    python ads/disable-auto-apply.py

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
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    subs = [r["recommendationSubscription"] for r in ads.search(
        "SELECT recommendation_subscription.resource_name, recommendation_subscription.type, "
        "recommendation_subscription.status FROM recommendation_subscription")]
    enabled = [(s["resourceName"], s["type"]) for s in subs if s.get("status") == "ENABLED"]
    print(f"{len(subs)} subscription(s), {len(enabled)} enabled")

    # Types newer than this API version all come back as ".../UNKNOWN", which
    # the API can't address. Count them, try none.
    unknown = [rn for rn, typ in enabled if typ == "UNKNOWN"]
    enabled = [(rn, typ) for rn, typ in enabled if typ != "UNKNOWN"]
    refused = ["UNKNOWN"] * len(unknown)
    for rn, typ in enabled:
        try:
            ads._post(f"customers/{ads_client.CUSTOMER_ID}/recommendationSubscriptions:mutateRecommendationSubscription",
                      {"operations": [{"update": {"resourceName": rn, "status": "PAUSED"}, "updateMask": "status"}],
                       "validateOnly": args.dry_run})
            print(f"  {'would pause' if args.dry_run else 'paused'}: {typ}")
        except ads_client.ApiError as e:
            refused.append(typ)
            print(f"  could not pause {typ}: {str(e)[:160]}")
    if unknown:
        print(f"  {len(unknown)} enabled subscription(s) of a type this API version can't name or change")
    if refused:
        print(f"\n{len(refused)} could not be changed through the API. Turn them off in Google Ads: "
              "Recommendations > Auto-apply.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
