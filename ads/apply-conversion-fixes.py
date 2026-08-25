#!/usr/bin/env python3
"""
Stop the New Quest Counseling account from bidding toward anything except
actual contact form submissions.

Two phases, because Google exposes two layers here:

  1. conversion_action.primary_for_goal, per action. Works only for actions
     you created. Google-defined ones (GOOGLE_HOSTED lead form actions,
     WEBPAGE_CODELESS auto-detected ones) reject all writes with "Mutates are
     not allowed for the requested resource".
  2. customer_conversion_goal.biddable, per category+origin. This is the layer
     Smart Bidding actually reads, and it IS writable for those same
     categories. So the actions that cannot be demoted individually get
     handled by demoting the goal category that carries them.

Also renames the button-click action so its report label matches what it
measures. Renaming does not change the conversion label, so the tag in
index.html keeps firing.

Stdlib only. Same auth path as ads/apply-pmax-assets.py.

Usage:
    python ads/apply-conversion-fixes.py --dry-run
    python ads/apply-conversion-fixes.py

IMPORTANT, read before running:

Create the new "Contact form submitted" action in the Google Ads UI FIRST.
A conversion goal must keep at least one Primary action, or the Performance
Max campaign has nothing to bid toward. This script therefore refuses to run
if demoting these three would leave the account with no enabled Primary
conversion action. Create the replacement, then run this.

Override with --allow-no-primary only if you know what you are doing.

Optionally also disables the codeless action entirely:
    python ads/apply-conversion-fixes.py --disable-codeless
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

CUSTOMER_ID = "1838861154"
LOGIN_CUSTOMER_ID = "1713871701"

API_VERSIONS = ["v22", "v21", "v20", "v19"]

# (id, new_name_or_None, why)
# new_name None means leave the name alone.
DEMOTE = [
    ("7732881582", "Contact form opened",
     "fires on button click, label gxwRCK7RqeccEIikg8hE; measures intent, not a lead"),
    ("7730138565", None,
     "WEBPAGE_CODELESS / PAGE_VIEW, many-per-click; auto-created, never should have been Primary"),
    ("7729952069", None,
     "Google-hosted lead form submit; only fires with lead form assets, which are not in use"),
]

CODELESS_ID = "7730138565"

# Account-level conversion goals to make non-biddable.
#
# This is the layer that actually controls what Smart Bidding chases, and it
# sits above conversion_action.primary_for_goal. The two immutable actions
# cannot be demoted directly, but their goal categories can, which gets the
# same result: PAGE_VIEW stops driving bids no matter what fires into it.
#
# The Performance Max campaign uses account-default goals, so changing them
# here propagates. Editing the campaign-level goals instead would flip that
# campaign to campaign-specific overrides, which is a config change nobody
# asked for.
GOALS_TO_DEMOTE = [
    ("PAGE_VIEW", "WEBSITE",
     f"carries the immutable codeless action {CODELESS_ID}; page views are not leads"),
    ("SUBMIT_LEAD_FORM", "GOOGLE_HOSTED",
     "carries the immutable Google-hosted lead form action; no lead form assets in use"),
]


def die(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def find_gcloud():
    override = os.environ.get("GCLOUD")
    if override:
        return override
    for name in ("gcloud", "gcloud.cmd", "gcloud.exe"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        r"C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        os.path.expanduser(
            r"~\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    die("gcloud not found. Set the GCLOUD env var to its full path.")


def access_token():
    exe = find_gcloud()
    try:
        out = subprocess.run(
            [exe, "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True,
        )
    except OSError as e:
        die(f"could not run {exe}: {e}")
    except subprocess.CalledProcessError as e:
        die(f"gcloud could not mint a token:\n{e.stderr.strip()}")
    token = out.stdout.strip()
    if not token:
        die("gcloud returned an empty token.")
    return token


class ApiError(Exception):
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload
        try:
            d = json.loads(payload)
            msgs = []
            for f in d.get("error", {}).get("details", []):
                for err in f.get("errors", []):
                    msgs.append(err.get("message", ""))
            detail = "; ".join(m for m in msgs if m) or d.get("error", {}).get("message", payload)
        except Exception:
            detail = payload
        super().__init__(f"HTTP {status}: {detail}")


class Ads:
    def __init__(self, token, dev_token):
        self.token = token
        self.dev_token = dev_token
        self.version = None

    def _post(self, path, body):
        req = urllib.request.Request(
            f"https://googleads.googleapis.com/{self.version}/{path}",
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "developer-token": self.dev_token,
                "login-customer-id": LOGIN_CUSTOMER_ID,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, e.read().decode(errors="replace")) from None

    def detect_version(self):
        probe = {"query": "SELECT customer.id FROM customer LIMIT 1"}
        last = None
        for v in API_VERSIONS:
            self.version = v
            try:
                self._post(f"customers/{CUSTOMER_ID}/googleAds:search", probe)
                print(f"Using Google Ads API {v}")
                return
            except ApiError as e:
                last = e
                if e.status == 404:
                    continue
                break
        hint = ""
        if last and last.status in (401, 403):
            hint = (
                "\n\nThis usually means ADC is missing the adwords scope. Re-run:\n"
                "  gcloud auth application-default login "
                "--scopes=https://www.googleapis.com/auth/adwords,"
                "https://www.googleapis.com/auth/cloud-platform"
            )
        die(f"no working API version.\n{last}{hint}")

    def search(self, query):
        rows, token = [], None
        while True:
            body = {"query": query}
            if token:
                body["pageToken"] = token
            page = self._post(f"customers/{CUSTOMER_ID}/googleAds:search", body)
            rows.extend(page.get("results", []))
            token = page.get("nextPageToken")
            if not token:
                return rows

    def mutate(self, resource, operations, validate_only):
        return self._post(
            f"customers/{CUSTOMER_ID}/{resource}:mutate",
            {"operations": operations, "validateOnly": validate_only},
        )


def load_actions(ads):
    rows = ads.search(
        "SELECT conversion_action.id, conversion_action.name, "
        "conversion_action.status, conversion_action.type, "
        "conversion_action.category, conversion_action.primary_for_goal "
        "FROM conversion_action"
    )
    out = {}
    for r in rows:
        ca = r["conversionAction"]
        out[str(ca["id"])] = {
            "name": ca.get("name", ""),
            "status": ca.get("status"),
            "type": ca.get("type"),
            "category": ca.get("category"),
            # primaryForGoal is omitted from the JSON when false
            "primary": bool(ca.get("primaryForGoal", False)),
        }
    return out


def load_customer_goals(ads):
    rows = ads.search(
        "SELECT customer_conversion_goal.category, "
        "customer_conversion_goal.origin, customer_conversion_goal.biddable "
        "FROM customer_conversion_goal"
    )
    return {
        (r["customerConversionGoal"]["category"],
         r["customerConversionGoal"]["origin"]): bool(
            r["customerConversionGoal"].get("biddable", False))
        for r in rows
    }


def fix_goals(ads, dry_run):
    """Make the goal categories that carry the immutable actions non-biddable."""
    goals = load_customer_goals(ads)

    print("\n--- Account conversion goals ---")
    for (cat, origin), biddable in sorted(goals.items()):
        print(f"  {'BIDDABLE ' if biddable else 'secondary'}  {cat} / {origin}")

    targets = {(c, o) for c, o, _ in GOALS_TO_DEMOTE}
    survivors = [k for k, v in goals.items() if v and k not in targets]
    if not survivors:
        print("\n  Skipping: demoting these would leave no biddable goal at all.")
        return
    print("\n  Biddable goal(s) that will remain:")
    for cat, origin in survivors:
        print(f"    {cat} / {origin}")

    todo = []
    for cat, origin, why in GOALS_TO_DEMOTE:
        if (cat, origin) not in goals:
            print(f"\n  no such goal, skipping: {cat} / {origin}")
            continue
        if not goals[(cat, origin)]:
            print(f"\n  already non-biddable, skipping: {cat} / {origin}")
            continue
        todo.append((cat, origin, why))

    if not todo:
        print("\n  Nothing to change.")
        return

    print()
    for cat, origin, why in todo:
        print(f"  {cat} / {origin}  biddable -> false")
        print(f"        reason: {why}")
        op = {
            "update": {
                "resourceName":
                    f"customers/{CUSTOMER_ID}/customerConversionGoals/{cat}~{origin}",
                "biddable": False,
            },
            "updateMask": "biddable",
        }
        try:
            ads.mutate("customerConversionGoals", [op], dry_run)
        except ApiError as e:
            print(f"        FAILED: {e}\n")
        else:
            print("        validated OK\n" if dry_run else "        applied\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="send with validateOnly=true and change nothing")
    ap.add_argument("--disable-codeless", action="store_true",
                    help=f"also set action {CODELESS_ID} to REMOVED, not just Secondary")
    ap.add_argument("--allow-no-primary", action="store_true",
                    help="proceed even if no enabled Primary action would remain")
    args = ap.parse_args()

    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not dev_token:
        die("GOOGLE_ADS_DEVELOPER_TOKEN is not set.")

    ads = Ads(access_token(), dev_token)
    ads.detect_version()

    mode = "DRY RUN (validateOnly, nothing is changed)" if args.dry_run else "APPLYING CHANGES"
    print(f"\n=== {mode} ===")
    print(f"Account {CUSTOMER_ID}\n")

    actions = load_actions(ads)

    print("Current conversion actions:")
    for aid, a in sorted(actions.items()):
        flag = "PRIMARY  " if a["primary"] else "secondary"
        print(f"  {aid}  {flag}  {a['status']:<8} {a['type']:<18} "
              f"{a['category']:<18} {a['name']}")

    # ---- safety check: something must stay Primary ------------------------
    targets = {aid for aid, _, _ in DEMOTE}
    survivors = [
        (aid, a["name"]) for aid, a in actions.items()
        if aid not in targets and a["primary"] and a["status"] == "ENABLED"
    ]
    print()
    if survivors:
        print("Primary action(s) that will remain:")
        for aid, name in survivors:
            print(f"  {aid}  {name}")
    else:
        msg = (
            "demoting these three would leave the account with NO enabled Primary\n"
            "conversion action, so the Performance Max campaign would have nothing to\n"
            "bid toward.\n\n"
            "Create the new \"Contact form submitted\" action in the Google Ads UI first\n"
            "(Website, category Submit lead form, count One, goal Primary), then re-run\n"
            "this script.\n\n"
            "To proceed anyway: --allow-no-primary"
        )
        if not args.allow_no_primary:
            die(msg)
        print("WARNING: no Primary action will remain. Proceeding because "
              "--allow-no-primary was passed.")

    # ---- build the operations --------------------------------------------
    ops = []
    for aid, new_name, why in DEMOTE:
        a = actions.get(aid)
        if not a:
            print(f"\n  action {aid} not found in this account, skipping")
            continue

        fields, changes = {}, []
        if a["primary"]:
            fields["primaryForGoal"] = False
            changes.append("Primary -> Secondary")
        if new_name and a["name"] != new_name:
            fields["name"] = new_name
            changes.append(f'name -> "{new_name}"')
        if args.disable_codeless and aid == CODELESS_ID and a["status"] != "REMOVED":
            fields["status"] = "REMOVED"
            changes.append("status -> REMOVED")

        if not fields:
            print(f"\n  already correct, skipping: {aid} {a['name']}")
            continue

        ops.append({
            "aid": aid,
            "name": a["name"],
            "changes": ", ".join(changes),
            "why": why,
            "op": {
                "update": dict(
                    resourceName=f"customers/{CUSTOMER_ID}/conversionActions/{aid}",
                    **fields,
                ),
                "updateMask": ",".join(fields),
            },
        })

    if not ops:
        print("\nNothing to change. Conversion actions already match the plan.")
        return

    # One mutate per action rather than one atomic batch. These three flips are
    # independent, and some conversion actions are not mutable at all: anything
    # Google defines for you (GOOGLE_HOSTED lead form actions, and sometimes
    # codeless ones) rejects writes with "Mutates are not allowed for the
    # requested resource". Batching meant one immutable action took the other
    # two down with it.
    print(f"\n{len(ops)} update operation(s), sent individually:\n")
    ok, blocked = [], []
    for item in ops:
        print(f"  {item['aid']}  {item['name']}")
        print(f"        {item['changes']}")
        print(f"        reason: {item['why']}")
        try:
            ads.mutate("conversionActions", [item["op"]], args.dry_run)
        except ApiError as e:
            blocked.append((item, e))
            print(f"        FAILED: {e}\n")
        else:
            ok.append(item)
            print("        validated OK\n" if args.dry_run else "        applied\n")

    print(f"{len(ok)} succeeded, {len(blocked)} rejected.")

    if blocked:
        print("\nRejected because Google owns those action definitions, so the API")
        print("will never write them:")
        for item, e in blocked:
            print(f"  - {item['name']} ({item['aid']})")
        print("\nHandled instead at the goal level below, which is the layer that")
        print("actually controls bidding. No UI work needed.")

    # ---- phase 2: the goal layer -----------------------------------------
    fix_goals(ads, args.dry_run)

    if not args.dry_run:
        print("\n=== Resulting state ===")
        print("Conversion actions:")
        for aid, a in sorted(load_actions(ads).items()):
            flag = "PRIMARY  " if a["primary"] else "secondary"
            print(f"  {aid}  {flag}  {a['category']:<18} {a['name']}")
        print("Account conversion goals:")
        for (cat, origin), biddable in sorted(load_customer_goals(ads).items()):
            print(f"  {'BIDDABLE ' if biddable else 'secondary'}  {cat} / {origin}")


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        die(str(e))
