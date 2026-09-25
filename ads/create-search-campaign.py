#!/usr/bin/env python3
"""
Create the round two Search campaign, PAUSED, in one atomic request.

Round one (Performance Max) spent most of its budget on accidental taps inside
mobile apps, and allowed no control over networks or keywords. This builds the
plan's replacement: Google Search only, Ohio residents only, manual bids,
four ad groups of phrase and exact keywords, two responsive search ads per ad
group (A: plain, B: her warm, lightly geeky voice), a negative keyword list,
and sitelink, callout, snippet and call assets.

Everything goes in a single googleAds:mutate with temporary ids, so Google
validates the whole campaign at once and either all of it is created or none
of it is. The campaign starts PAUSED; turning it on is a separate, deliberate
step after reviewing it in the Google Ads website.

Refuses to run if a campaign with the same name already exists.
Same auth as apply-pmax-assets.py.

    python ads/create-search-campaign.py --dry-run   # validateOnly, creates nothing
    python ads/create-search-campaign.py
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

CID = ads_client.CUSTOMER_ID
C = f"customers/{CID}"

CAMPAIGN_NAME = "Round 2 - Search - Ohio"
DAILY_BUDGET = 15.00
OHIO = "geoTargetConstants/21168"
ENGLISH = "languageConstants/1000"
SITE = "https://www.newquestcounseling.com/"
PHONE = "5136229072"
CALL_DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
CALL_HOURS = (8, 19)  # account time zone

# ---------------------------------------------------------------------------
# Ad copy. Every line was checked against Google's limits (30 / 90 chars).
# ---------------------------------------------------------------------------
DESC_A = [
    "Video therapy anywhere in Ohio for anxiety, burnout, and life changes. Book a free call.",
    "In-network with Anthem and UnitedHealthcare. Sliding-scale self-pay if you are not.",
    "Start with a free 15-minute consultation. No pressure, no judgment, just a first step.",
    "Licensed across Ohio. Secure video sessions, so no commute and no waiting room.",
]
DESC_B = [
    "Light, positive, judgment-free video therapy anywhere in Ohio. Geeks and gamers welcome.",
    "Warm, welcoming video therapy anywhere in Ohio. Anthem and UnitedHealthcare accepted.",
    "Therapy that feels like a good conversation. Start with a free 15-minute call.",
]
COUPLES_DESC = "Online couples and family counseling across Ohio. Work through it together, from home."
GAMER_DESC = "A therapist who gets your world, from tabletop nights to ranked games. Free 15-min call."

AD_GROUPS = [
    {
        "name": "Insurance", "bid": 7.00, "status": "ENABLED",
        "keywords": [("therapist that takes anthem", "PHRASE"), ("anthem therapist ohio", "PHRASE"),
                     ("unitedhealthcare therapist", "PHRASE"), ("online therapy anthem", "PHRASE"),
                     ("therapist accepts united healthcare", "PHRASE"), ("counselor that takes anthem", "PHRASE"),
                     ("in network therapist ohio", "EXACT")],
        "ads": {
            "A": (["Therapist Who Takes Anthem", "UnitedHealthcare Therapist", "Use Your Insurance for Therapy",
                   "In-Network With Anthem", "Anthem & UnitedHealthcare", "Online Therapy in Ohio",
                   "Sessions Anywhere in Ohio", "Free 15-Minute Consultation", "Sliding-Scale Self-Pay",
                   "Licensed Therapist in Ohio", "Dorasae Rosario, LPCC", "Book a Free Consultation"], DESC_A),
            "B": (["Therapist Who Takes Anthem", "UnitedHealthcare Therapist", "Use Your Insurance for Therapy",
                   "A Therapist Who Gets It", "Gamers and Geeks Welcome", "Warm, Welcoming Online Therapy",
                   "Light, Positive, Judgment-Free", "Start Your New Quest", "Online Therapy in Ohio",
                   "Free 15-Minute Consultation"], DESC_B + [DESC_A[1]]),
        },
    },
    {
        "name": "Online therapy Ohio", "bid": 6.00, "status": "ENABLED",
        "keywords": [("online therapy ohio", "PHRASE"), ("virtual therapist ohio", "PHRASE"),
                     ("online therapist columbus", "PHRASE"), ("online counseling cleveland", "PHRASE"),
                     ("therapist cincinnati", "PHRASE"), ("anxiety therapist ohio", "PHRASE"),
                     ("online therapy for anxiety", "PHRASE"), ("burnout therapist", "PHRASE"),
                     ("telehealth counseling ohio", "PHRASE")],
        "ads": {
            "A": (["Online Therapy in Ohio", "Sessions Anywhere in Ohio", "Anthem & UnitedHealthcare",
                   "Free 15-Minute Consultation", "Sliding-Scale Self-Pay", "Therapy by Video, Statewide",
                   "Licensed Therapist in Ohio", "Anxiety and Burnout Therapy", "Dorasae Rosario, LPCC",
                   "Judgment-Free Therapy", "Serving All of Ohio", "Book a Free Consultation"], DESC_A),
            "B": (["A Therapist Who Gets It", "Gamers and Geeks Welcome", "Warm, Welcoming Online Therapy",
                   "Light, Positive, Judgment-Free", "Start Your New Quest", "Level Up Your Well-Being",
                   "Online Therapy in Ohio", "Anthem & UnitedHealthcare", "Free 15-Minute Consultation",
                   "Sessions Anywhere in Ohio", "Anxiety and Burnout Therapy"], DESC_B + [DESC_A[2]]),
        },
    },
    {
        # Starts paused: the plan turns it on in week 2 if the budget allows.
        "name": "Couples and family", "bid": 6.00, "status": "PAUSED",
        "keywords": [("online couples counseling ohio", "PHRASE"), ("couples therapist columbus", "PHRASE"),
                     ("marriage counseling online ohio", "PHRASE"), ("family therapy online ohio", "PHRASE"),
                     ("couples therapy cincinnati", "PHRASE")],
        "ads": {
            "A": (["Online Couples Counseling", "Couples Therapy in Ohio", "Family Therapy by Video",
                   "Online Therapy in Ohio", "Sessions Anywhere in Ohio", "Anthem & UnitedHealthcare",
                   "Free 15-Minute Consultation", "Sliding-Scale Self-Pay", "Licensed Therapist in Ohio",
                   "Book a Free Consultation"], [COUPLES_DESC] + DESC_A[1:]),
            "B": (["Online Couples Counseling", "Couples Therapy in Ohio", "Family Therapy by Video",
                   "A Therapist Who Gets It", "Warm, Welcoming Online Therapy", "Light, Positive, Judgment-Free",
                   "Start Your New Quest", "Anthem & UnitedHealthcare", "Free 15-Minute Consultation"],
                  [COUPLES_DESC] + DESC_B[1:]),
        },
    },
    {
        "name": "Geeks and gamers", "bid": 4.00, "status": "ENABLED",
        "keywords": [("therapist for gamers", "PHRASE"), ("gamer therapist", "PHRASE"), ("geek therapist", "PHRASE"),
                     ("nerd friendly therapist", "PHRASE"), ("geek friendly therapist", "PHRASE"),
                     ("online therapy for gamers", "PHRASE"), ("therapist who plays video games", "PHRASE")],
        "ads": {
            "A": (["Online Therapy for Gamers", "Therapy for Gamers and Geeks", "Geek-Friendly Therapy in Ohio",
                   "Nerd-Friendly Counseling", "Online Therapy in Ohio", "Anthem & UnitedHealthcare",
                   "Free 15-Minute Consultation", "Sessions Anywhere in Ohio", "Licensed Therapist in Ohio"],
                  [GAMER_DESC] + DESC_A[1:]),
            "B": (["A Therapist Who Gets It", "Gamers and Geeks Welcome", "Level Up Your Well-Being",
                   "Start Your New Quest", "Therapy for Gamers and Geeks", "Geek-Friendly Therapy in Ohio",
                   "Online Therapy in Ohio", "Free 15-Minute Consultation"], [GAMER_DESC] + DESC_B),
        },
    },
]

# Single words block any search containing them; phrases block that phrase.
NEGATIVES = ["jobs", "careers", "salary", "hiring", "degree", "license requirements", "ceu", "how to become",
             "free", "psychiatrist", "medication", "adhd testing", "hotline", "988", "betterhelp", "talkspace",
             "rehab", "detox", "addiction", "court ordered", "medicaid", "gaming disorder", "school counselor",
             "internship"]

SITELINKS = [
    ("Insurance and Rates", "Anthem and UnitedHealthcare", "Plus sliding-scale self-pay", SITE + "#insurance"),
    ("Meet Dorasae", "Licensed LPCC, based in Cincinnati", "Sees clients anywhere in Ohio", SITE + "about.html"),
    ("Couples and Family", "Online couples counseling", "Family therapy by video", SITE + "#services"),
    ("Common Questions", "How online sessions work", "Costs, insurance, and scheduling", SITE + "#wiki"),
]
CALLOUTS = ["Free 15-Min Consultation", "Secure Video Sessions", "Sliding-Scale Fees", "Licensed LPCC",
            "Anthem & UnitedHealthcare"]
SNIPPET = ("Services", ["Individual Counseling", "Couples Counseling", "Family Therapy"])


def check_lengths():
    problems = []
    for g in AD_GROUPS:
        for tone, (heads, descs) in g["ads"].items():
            if not 3 <= len(heads) <= 15 or not 2 <= len(descs) <= 4:
                problems.append(f"{g['name']} {tone}: {len(heads)} headlines, {len(descs)} descriptions")
            problems += [f"headline too long: {h}" for h in heads if len(h) > 30]
            problems += [f"description too long: {d}" for d in descs if len(d) > 90]
            problems += [f"em dash: {t}" for t in heads + descs if "—" in t]
    for text, d1, d2, _ in SITELINKS:
        problems += [f"sitelink too long: {t}" for t, n in ((text, 25), (d1, 35), (d2, 35)) if len(t) > n]
    problems += [f"callout too long: {c}" for c in CALLOUTS if len(c) > 25]
    if problems:
        ads_client.die("copy does not fit Google's limits:\n  " + "\n  ".join(problems))


def build_operations():
    ops = []
    next_id = [0]

    def tmp(kind):
        next_id[0] -= 1
        return f"{C}/{kind}/{next_id[0]}"

    budget = tmp("campaignBudgets")
    ops.append({"campaignBudgetOperation": {"create": {
        "resourceName": budget, "name": f"{CAMPAIGN_NAME} budget",
        "amountMicros": str(int(DAILY_BUDGET * 1e6)), "deliveryMethod": "STANDARD", "explicitlyShared": False}}})

    campaign = tmp("campaigns")
    ops.append({"campaignOperation": {"create": {
        "resourceName": campaign, "name": CAMPAIGN_NAME, "status": "PAUSED",
        "advertisingChannelType": "SEARCH", "campaignBudget": budget,
        "manualCpc": {"enhancedCpcEnabled": False},
        "networkSettings": {"targetGoogleSearch": True, "targetSearchNetwork": False,
                            "targetContentNetwork": False, "targetPartnerSearchNetwork": False},
        # Round one used PRESENCE_OR_INTEREST, which also reached people outside Ohio.
        "geoTargetTypeSetting": {"positiveGeoTargetType": "PRESENCE", "negativeGeoTargetType": "PRESENCE"},
        "containsEuPoliticalAdvertising": "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"}}})

    ops.append({"campaignCriterionOperation": {"create": {"campaign": campaign, "location": {"geoTargetConstant": OHIO}}}})
    ops.append({"campaignCriterionOperation": {"create": {"campaign": campaign, "language": {"languageConstant": ENGLISH}}}})
    for text in NEGATIVES:
        ops.append({"campaignCriterionOperation": {"create": {
            "campaign": campaign, "negative": True,
            "keyword": {"text": text, "matchType": "PHRASE" if " " in text else "BROAD"}}}})

    for g in AD_GROUPS:
        ag = tmp("adGroups")
        ops.append({"adGroupOperation": {"create": {
            "resourceName": ag, "campaign": campaign, "name": g["name"], "status": g["status"],
            "type": "SEARCH_STANDARD", "cpcBidMicros": str(int(g["bid"] * 1e6))}}})
        for text, match in g["keywords"]:
            ops.append({"adGroupCriterionOperation": {"create": {
                "adGroup": ag, "status": "ENABLED", "keyword": {"text": text, "matchType": match}}}})
        for tone, (heads, descs) in g["ads"].items():
            ops.append({"adGroupAdOperation": {"create": {
                "adGroup": ag, "status": "ENABLED",
                "ad": {"finalUrls": [SITE], "responsiveSearchAd": {
                    "headlines": [{"text": h} for h in heads],
                    "descriptions": [{"text": d} for d in descs],
                    "path1": "online-therapy", "path2": "ohio"}}}}})

    def asset(body, field):
        rn = tmp("assets")
        ops.append({"assetOperation": {"create": {"resourceName": rn, **body}}})
        ops.append({"campaignAssetOperation": {"create": {"campaign": campaign, "asset": rn, "fieldType": field}}})

    for text, d1, d2, url in SITELINKS:
        asset({"finalUrls": [url], "sitelinkAsset": {"linkText": text, "description1": d1, "description2": d2}}, "SITELINK")
    for text in CALLOUTS:
        asset({"calloutAsset": {"calloutText": text}}, "CALLOUT")
    asset({"structuredSnippetAsset": {"header": SNIPPET[0], "values": SNIPPET[1]}}, "STRUCTURED_SNIPPET")
    asset({"callAsset": {
        "countryCode": "US", "phoneNumber": PHONE,
        "callConversionReportingState": "USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION",
        "adScheduleTargets": [{"dayOfWeek": d, "startHour": CALL_HOURS[0], "startMinute": "ZERO",
                               "endHour": CALL_HOURS[1], "endMinute": "ZERO"} for d in CALL_DAYS]}}, "CALL")
    return ops


def exemptible_health_keywords(error, ops):
    """[(op index, policy key)] if every error is an exemptible
    HEALTH_IN_PERSONALIZED_ADS finding on a keyword; otherwise None."""
    import json
    try:
        errors = [x for f in json.loads(error.payload)["error"]["details"] for x in f.get("errors", [])]
    except (ValueError, KeyError):
        return None
    found = []
    for err in errors:
        pv = err.get("details", {}).get("policyViolationDetails")
        idx = [p.get("index") for p in err.get("location", {}).get("fieldPathElements", [])
               if p.get("fieldName") == "mutate_operations"]
        if not pv or not idx or not pv.get("isExemptible") or pv["key"]["policyName"] != "HEALTH_IN_PERSONALIZED_ADS":
            return None
        i = int(idx[0])
        if "adGroupCriterionOperation" not in ops[i]:
            return None
        found.append((i, pv["key"]))
    return found or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate everything with validateOnly and create nothing")
    args = ap.parse_args()
    check_lengths()

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()

    existing = ads.search(
        f"SELECT campaign.id, campaign.status FROM campaign WHERE campaign.name = '{CAMPAIGN_NAME}' "
        "AND campaign.status != 'REMOVED'")
    if existing:
        ads_client.die(f'"{CAMPAIGN_NAME}" already exists (id {existing[0]["campaign"]["id"]}). Nothing changed.')

    ops = build_operations()
    kinds = {}
    for op in ops:
        k = next(iter(op))
        kinds[k] = kinds.get(k, 0) + 1
    print(f"\n{'DRY RUN (validateOnly)' if args.dry_run else 'CREATING'}: {len(ops)} operations in one request")
    for k, n in kinds.items():
        print(f"  {n:>3}  {k.replace('Operation', '')}")

    def send():
        return ads._post(f"customers/{CID}/googleAds:mutate",
                         {"mutateOperations": ops, "validateOnly": args.dry_run})

    try:
        result = send()
    except ads_client.ApiError as e:
        # Google flags many therapy keywords under "Health in personalized
        # advertising". That policy bars targeting people by health data
        # (remarketing, audiences); plain keyword ads on Search are allowed,
        # and the keyword serves as "Eligible (limited)". The API wants an
        # explicit exemption request per keyword. Exempt ONLY that policy,
        # ONLY on keywords, and only when Google says it is exemptible;
        # anything else still fails the run.
        exempt = exemptible_health_keywords(e, ops)
        if exempt is None:
            raise
        print(f"\nRequesting the health-personalization exemption for {len(exempt)} keyword(s):")
        for i, key in exempt:
            ops[i]["adGroupCriterionOperation"].setdefault("exemptPolicyViolationKeys", []).append(key)
            print(f"    {key['violatingText']}")
        result = send()
    if args.dry_run:
        print("\nValidated OK. Nothing was created.")
        return
    responses = result.get("mutateOperationResponses", [])
    camp = next(r["campaignResult"]["resourceName"] for r in responses if "campaignResult" in r)
    print(f"\nCreated {camp}, PAUSED. Review it in Google Ads, then turn it on.")


if __name__ == "__main__":
    try:
        main()
    except ads_client.ApiError as e:
        ads_client.die(str(e))
