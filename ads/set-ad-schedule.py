#!/usr/bin/env python3
"""
Run a campaign's ads only between two hours, every day (account time zone).

    python ads/set-ad-schedule.py 24287062730 4 24 --dry-run   # 4 AM to midnight
    python ads/set-ad-schedule.py 24287062730 4 24
    python ads/set-ad-schedule.py 24287062730 clear            # all hours again

Replaces any existing ad schedule on the campaign. Same auth as apply-pmax-assets.py.
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

DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_id")
    ap.add_argument("start", help="start hour 0-23, or 'clear'")
    ap.add_argument("end", nargs="?", type=int, default=24, help="end hour 1-24")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    clear = args.start == "clear"
    if not clear:
        start = int(args.start)
        if not (0 <= start < args.end <= 24):
            ads_client.die("Need 0 <= start < end <= 24.")

    ads = ads_client.Ads(ads_client.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"])
    ads.detect_version()
    cid = ads.search("SELECT customer.id, customer.time_zone FROM customer")[0]["customer"]
    print(f"Account time zone: {cid['timeZone']}")
    existing = ads.search(
        "SELECT campaign_criterion.resource_name, campaign_criterion.ad_schedule.day_of_week, "
        "campaign_criterion.ad_schedule.start_hour, campaign_criterion.ad_schedule.end_hour "
        f"FROM campaign_criterion WHERE campaign.id = {args.campaign_id} AND campaign_criterion.type = 'AD_SCHEDULE'")
    for r in existing:
        s = r["campaignCriterion"]["adSchedule"]
        print(f"  removing {s['dayOfWeek']} {s.get('startHour', 0)}-{s['endHour']}")
    ops = [{"remove": r["campaignCriterion"]["resourceName"]} for r in existing]
    if not clear:
        camp = f"customers/{ads_client.CUSTOMER_ID}/campaigns/{args.campaign_id}"
        for d in DAYS:
            ops.append({"create": {"campaign": camp, "adSchedule": {
                "dayOfWeek": d, "startHour": start, "startMinute": "ZERO", "endHour": args.end, "endMinute": "ZERO"}}})
        print(f"  adding every day {start}:00 to {args.end}:00")
    if not ops:
        print("Nothing to change.")
        return
    ads.mutate("campaignCriteria", ops, args.dry_run)
    print("Validated only. Nothing changed." if args.dry_run else "Done.")


if __name__ == "__main__":
    main()
