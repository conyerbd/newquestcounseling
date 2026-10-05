#!/usr/bin/env python3
"""
Put a campaign back on manual CPC bidding (Enhanced CPC off).

Google's auto-apply moved round two to Maximize Conversions on 2026-09-27,
which ignores the ad group and keyword bids. With a conversion or so a month
it has nothing to learn from and paid $10 to $30 per click. The ad group and
keyword bids are still stored, so they take effect again as soon as the
campaign is back on manual CPC.

    python ads/set-manual-cpc.py 24287062730 --dry-run
    python ads/set-manual-cpc.py 24287062730

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
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    rows = ads.search("SELECT campaign.name, campaign.bidding_strategy_type FROM campaign "
                      f"WHERE campaign.id = {args.campaign_id}")
    if not rows:
        ads_client.die(f"No campaign {args.campaign_id}.")
    c = rows[0]["campaign"]
    print(f'"{c["name"]}" bidding: {c["biddingStrategyType"]} -> MANUAL_CPC')
    if c["biddingStrategyType"] == "MANUAL_CPC":
        print("Nothing to change.")
        return
    ads.mutate("campaigns", [{"update": {"resourceName": c["resourceName"],
                                         "manualCpc": {"enhancedCpcEnabled": False}},
                              "updateMask": "manual_cpc.enhanced_cpc_enabled"}], args.dry_run)
    print("Validated OK. Nothing changed." if args.dry_run else "Done.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
