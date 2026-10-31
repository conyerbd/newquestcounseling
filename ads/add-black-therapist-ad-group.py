#!/usr/bin/env python3
"""
Add the "Black therapist" ad group to the round two Search campaign.

Dorasae is Black, and many people look specifically for a therapist who shares
that experience. The keywords reach those searches and the ad text describes
her, never the person searching. The site itself says nothing about it, at her
request: the ad and her photo do that work, so it lands on the top of /pro/.

Created PAUSED by default; --enabled creates it running. One atomic request.
Refuses if the ad group already exists. Unlike add-teen-ad-group.py this does
not request policy exemptions: if Google flags a keyword, it stops so a person
can decide.
Same auth as apply-pmax-assets.py.

    python ads/add-black-therapist-ad-group.py --dry-run
    python ads/add-black-therapist-ad-group.py [--enabled]
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

CAMPAIGN_ID = "24287062730"
NAME = "Black therapist"
BID = 7.00
FINAL_URL = "https://www.newquestcounseling.com/pro/"

KEYWORDS = ["black therapist", "black therapist ohio", "black therapist online", "black therapist cincinnati",
            "black therapist columbus", "black therapist cleveland", "black counselor", "black female therapist",
            "african american therapist", "african american counselor"]

HEADLINES = ["Black Therapist in Ohio", "Black Therapist, Online", "Black Counselor in Ohio",
             "Online Therapy in Ohio", "Dorasae Rosario, LPCC", "Licensed Therapist in Ohio",
             "Anthem & UnitedHealthcare", "Sliding-Scale Self-Pay", "Free 15-Minute Consultation",
             "Sessions From Home by Video", "Culturally Sensitive Care", "Your Player 2 in Therapy",
             "Adults, Couples, Teens 14+", "Geeks and Gamers Welcome", "Call or Message Anytime"]
DESCRIPTIONS = ["Online therapy with a Black therapist, anywhere in Ohio. Free 15-minute consultation.",
                "In-network with Anthem and UnitedHealthcare. Sliding-scale self-pay if you are not.",
                "Help with anxiety, self-esteem, relationships and life changes, by secure video.",
                "Send a message or call to schedule your free 15-minute consultation. No pressure."]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--enabled", action="store_true", help="create the ad group running instead of paused")
    args = ap.parse_args()

    bad = [h for h in HEADLINES if len(h) > 30] + [d for d in DESCRIPTIONS if len(d) > 90]
    if bad or len(HEADLINES) > 15 or len(DESCRIPTIONS) > 4:
        ads_client.die(f"copy does not fit Google's limits: {bad}")

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    C = f"customers/{ads_client.CUSTOMER_ID}"
    camp = f"{C}/campaigns/{CAMPAIGN_ID}"
    if ads.search(f"SELECT ad_group.id FROM ad_group WHERE campaign.id = {CAMPAIGN_ID} "
                  f"AND ad_group.name = '{NAME}' AND ad_group.status != 'REMOVED'"):
        ads_client.die(f'"{NAME}" already exists. Nothing changed.')

    ag = f"{C}/adGroups/-1"
    ops = [{"adGroupOperation": {"create": {
        "resourceName": ag, "campaign": camp, "name": NAME, "status": "ENABLED" if args.enabled else "PAUSED",
        "type": "SEARCH_STANDARD", "cpcBidMicros": str(int(BID * 1e6))}}}]
    for kw in KEYWORDS:
        ops.append({"adGroupCriterionOperation": {"create": {
            "adGroup": ag, "status": "ENABLED", "keyword": {"text": kw, "matchType": "PHRASE"}}}})
    ops.append({"adGroupAdOperation": {"create": {"adGroup": ag, "status": "ENABLED", "ad": {
        "finalUrls": [FINAL_URL], "responsiveSearchAd": {
            "headlines": [{"text": h} for h in HEADLINES], "descriptions": [{"text": d} for d in DESCRIPTIONS],
            "path1": "black-therapist", "path2": "ohio"}}}}})

    print(f'{"DRY RUN" if args.dry_run else "CREATING"}: "{NAME}" ({"enabled" if args.enabled else "paused"}), '
          f"${BID:.2f} bid, {len(KEYWORDS)} keywords, 1 ad, landing on {FINAL_URL}")
    ads._post(f"{C}/googleAds:mutate", {"mutateOperations": ops, "validateOnly": args.dry_run})
    print("Validated OK. Nothing created." if args.dry_run else "Done.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
