#!/usr/bin/env python3
"""
Add the "Teens (for parents)" ad group to the round two Search campaign.

She sees teens 14 and up, one-on-one, in family sessions, and with parent
check-ins. Parents search for this directly ("therapist for my teenager"),
so the ad group targets those searches and lands on the homepage's #teens
section, which answers what a parent wants to know. Two ads, same A/B
split as the rest of the campaign (A plain, B her warm voice). Both name
her, since every ad call so far came from someone wanting a different
provider.

Also blocks program-type searches she doesn't offer (residential,
wilderness, boot camp, inpatient, boarding school) at the campaign level.

Created PAUSED by default; --enabled creates it running. One atomic
request. Refuses if the ad group already exists.
Same auth as apply-pmax-assets.py.

    python ads/add-teen-ad-group.py --dry-run
    python ads/add-teen-ad-group.py [--enabled]
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

CAMPAIGN_ID = "24287062730"
NAME = "Teens (for parents)"
BID = 7.00
FINAL_URL = "https://www.newquestcounseling.com/#teens"

KEYWORDS = ["therapist for teenager", "therapist for teens", "teen therapist ohio", "teen counseling",
            "counseling for teens", "adolescent therapist", "therapist for my son", "therapist for my daughter",
            "online therapy for teens", "teen anxiety therapist"]

DESC = {
    "price": "In-network with Anthem and UnitedHealthcare. Sliding-scale self-pay if you are not.",
    "ages": "Online therapy for teens 14 and up, anywhere in Ohio. Book a free 15-minute call.",
    "mix": "One-on-one sessions, family sessions, and parent check-ins. We find the right mix.",
    "warm": "A warm, judgment-free space where teens can open up. Geeks and gamers welcome.",
}
ADS = {
    "A": (["Therapy for Teens in Ohio", "Online Therapy for Teens", "Teen Therapist, Ages 14+",
           "Anthem & UnitedHealthcare", "Free 15-Minute Consultation", "Sessions From Home by Video",
           "Licensed Therapist in Ohio", "Parent Check-Ins Available", "Family Sessions Available",
           "Dorasae Rosario, LPCC", "Book a Free Consultation", "Help for Teen Anxiety"],
          [DESC["ages"], DESC["mix"], DESC["price"]]),
    # "A Therapist Who Gets It" marks the her-voice ad for the dashboard's A/B labels.
    "B": (["A Therapist Who Gets It", "A Therapist Teens Talk To", "Teens Feel Heard Here",
           "Geeks and Gamers Welcome", "Judgment-Free Teen Therapy", "Start Your New Quest",
           "Therapy for Teens in Ohio", "Anthem & UnitedHealthcare", "Free 15-Minute Consultation",
           "Parent Check-Ins Available", "Dorasae Rosario, LPCC"],
          [DESC["warm"], DESC["ages"], DESC["mix"], DESC["price"]]),
}
NEGATIVES = ["residential", "wilderness", "boot camp", "inpatient", "boarding school"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--enabled", action="store_true", help="create the ad group running instead of paused")
    args = ap.parse_args()

    for heads, descs in ADS.values():
        bad = [h for h in heads if len(h) > 30] + [d for d in descs if len(d) > 90]
        if bad or len(heads) > 15 or len(descs) > 4:
            ads_client.die(f"copy does not fit Google's limits: {bad}")

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    C = f"customers/{ads_client.CUSTOMER_ID}"
    camp = f"{C}/campaigns/{CAMPAIGN_ID}"
    if ads.search(f"SELECT ad_group.id FROM ad_group WHERE campaign.id = {CAMPAIGN_ID} "
                  f"AND ad_group.name = '{NAME}' AND ad_group.status != 'REMOVED'"):
        ads_client.die(f'"{NAME}" already exists. Nothing changed.')
    have = {r["campaignCriterion"]["keyword"]["text"].lower() for r in ads.search(
        "SELECT campaign.id, campaign_criterion.keyword.text FROM campaign_criterion "
        f"WHERE campaign.id = {CAMPAIGN_ID} AND campaign_criterion.negative = TRUE AND campaign_criterion.type = 'KEYWORD'")}

    ag = f"{C}/adGroups/-1"
    ops = [{"adGroupOperation": {"create": {
        "resourceName": ag, "campaign": camp, "name": NAME, "status": "ENABLED" if args.enabled else "PAUSED",
        "type": "SEARCH_STANDARD", "cpcBidMicros": str(int(BID * 1e6))}}}]
    for kw in KEYWORDS:
        ops.append({"adGroupCriterionOperation": {"create": {
            "adGroup": ag, "status": "ENABLED", "keyword": {"text": kw, "matchType": "PHRASE"}}}})
    for heads, descs in ADS.values():
        ops.append({"adGroupAdOperation": {"create": {"adGroup": ag, "status": "ENABLED", "ad": {
            "finalUrls": [FINAL_URL], "responsiveSearchAd": {
                "headlines": [{"text": h} for h in heads], "descriptions": [{"text": d} for d in descs],
                "path1": "teen-therapy", "path2": "ohio"}}}}})
    for t in NEGATIVES:
        if t not in have:
            ops.append({"campaignCriterionOperation": {"create": {
                "campaign": camp, "negative": True,
                "keyword": {"text": t, "matchType": "PHRASE" if " " in t else "BROAD"}}}})

    print(f'{"DRY RUN" if args.dry_run else "CREATING"}: "{NAME}" ({"enabled" if args.enabled else "paused"}), '
          f"${BID:.2f} bid, {len(KEYWORDS)} keywords, 2 ads, landing on {FINAL_URL}")

    def send():
        return ads._post(f"{C}/googleAds:mutate", {"mutateOperations": ops, "validateOnly": args.dry_run})

    try:
        send()
    except ads_client.ApiError as e:
        exempt = create_campaign.exemptible_health_keywords(e, ops)
        if exempt is None:
            raise
        print(f"Requesting the health-personalization exemption for {len(exempt)} keyword(s):")
        for i, key in exempt:
            ops[i]["adGroupCriterionOperation"].setdefault("exemptPolicyViolationKeys", []).append(key)
            print(f"    {key['violatingText']}")
        send()
    print("Validated OK. Nothing created." if args.dry_run else "Done.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
