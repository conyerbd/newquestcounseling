#!/usr/bin/env python3
"""
Point every ad in one ad group at a landing page.

The site has two versions of the home page: /pro/ (calmer, more professional)
and /light/ (the original playful design, also served at /). Each ad group
lands on whichever fits who is searching, for example parents of teens on
/pro/#teens and gamers on /light/.

Changing an ad's final URL keeps its stats but sends it back through Google's
review, so it may pause briefly.

    python ads/set-ad-final-url.py 24287062730 "Teens (for parents)" https://www.newquestcounseling.com/pro/#teens --dry-run
    python ads/set-ad-final-url.py 24287062730 "Teens (for parents)" https://www.newquestcounseling.com/pro/#teens

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
    ap.add_argument("ad_group")
    ap.add_argument("url")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.url.startswith("https://www.newquestcounseling.com/"):
        ads_client.die(f"Expected a newquestcounseling.com URL, got {args.url}")

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()

    rows = ads.search(
        "SELECT ad_group.name, ad_group_ad.ad.resource_name, ad_group_ad.ad.id, ad_group_ad.ad.final_urls "
        f"FROM ad_group_ad WHERE campaign.id = {args.campaign_id} "
        f"AND ad_group.name = '{args.ad_group}' AND ad_group_ad.status != 'REMOVED'")
    if not rows:
        ads_client.die(f"No ads found in ad group: {args.ad_group}")

    ops = []
    for r in rows:
        ad = r["adGroupAd"]["ad"]
        old = ad.get("finalUrls", [])
        if old == [args.url]:
            print(f"  already set: ad {ad['id']}")
            continue
        ops.append({"update": {"resourceName": ad["resourceName"], "finalUrls": [args.url]}, "updateMask": "final_urls"})
        print(f"  ad {ad['id']}: {', '.join(old) or '(none)'} -> {args.url}")
    if not ops:
        print("Nothing to change.")
        return

    ads.mutate("ads", ops, args.dry_run)
    print("Validated OK. Nothing changed." if args.dry_run else "Done.")


if __name__ == "__main__":
    main()
