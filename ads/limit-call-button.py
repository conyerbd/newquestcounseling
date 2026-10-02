#!/usr/bin/env python3
"""
Show the call button only on chosen ad groups.

Every call from the ads in round two's first week came from someone wanting
a different provider: broad searches like "therapist cincinnati", where people
tap Call on the first ad without reading whose it is. The insurance and teen
searches are specific enough that a caller likely means to reach her.

One atomic request:
  - links the round two call asset (weekdays 8am to 7pm) to each named ad group
  - removes it from the campaign level
  - removes the old account-level call asset from round one, which would
    otherwise fill in for every ad group without one

    python ads/limit-call-button.py 24287062730 "Insurance" "Teens (for parents)" --dry-run
    python ads/limit-call-button.py 24287062730 "Insurance" "Teens (for parents)"

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
    ap.add_argument("ad_groups", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cid = args.campaign_id

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()

    camp_calls = ads.search(
        "SELECT campaign.id, campaign_asset.resource_name, asset.resource_name FROM campaign_asset "
        f"WHERE campaign.id = {cid} AND campaign_asset.field_type = 'CALL' AND campaign_asset.status != 'REMOVED'")
    if len(camp_calls) != 1:
        ads_client.die(f"Expected one campaign-level call asset, found {len(camp_calls)}.")
    call_asset = camp_calls[0]["asset"]["resourceName"]

    groups = {r["adGroup"]["name"]: r["adGroup"]["resourceName"] for r in ads.search(
        f"SELECT ad_group.name, ad_group.resource_name FROM ad_group WHERE campaign.id = {cid} "
        "AND ad_group.status != 'REMOVED'")}
    missing = [g for g in args.ad_groups if g not in groups]
    if missing:
        ads_client.die(f"No ad group named: {missing}. Have: {sorted(groups)}")
    linked = {r["adGroup"]["resourceName"] for r in ads.search(
        "SELECT campaign.id, ad_group.resource_name FROM ad_group_asset "
        f"WHERE campaign.id = {cid} AND ad_group_asset.field_type = 'CALL' AND ad_group_asset.status != 'REMOVED'")}

    acct_calls = [r["customerAsset"]["resourceName"] for r in ads.search(
        "SELECT customer_asset.resource_name FROM customer_asset "
        "WHERE customer_asset.field_type = 'CALL' AND customer_asset.status != 'REMOVED'")]

    ops = []
    for g in args.ad_groups:
        if groups[g] in linked:
            print(f"  already has the call button: {g}")
            continue
        ops.append({"adGroupAssetOperation": {"create": {"adGroup": groups[g], "asset": call_asset, "fieldType": "CALL"}}})
        print(f"  add call button to: {g}")
    ops.append({"campaignAssetOperation": {"remove": camp_calls[0]["campaignAsset"]["resourceName"]}})
    print("  remove call button from the campaign level")
    for rn in acct_calls:
        ops.append({"customerAssetOperation": {"remove": rn}})
        print(f"  remove the old account-level call button ({rn.rsplit('/', 1)[-1]})")

    ads._post(f"customers/{ads_client.CUSTOMER_ID}/googleAds:mutate",
              {"mutateOperations": ops, "validateOnly": args.dry_run})
    print("Validated OK. Nothing changed." if args.dry_run else "Done.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
