"""Round two ad copy: drop "14+", pin an online headline to H1 and insurance to H2.
Usage: python update_ads.py [--apply]   (default validates only)"""
import importlib.util, os, sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("ads_client", r"C:\working\newquestcounseling\ads\apply-pmax-assets.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
apply = "--apply" in sys.argv
ads = m.Ads(m.access_token(), os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]); ads.detect_version()

CAMPAIGN = 24287062730
PRO = "https://www.newquestcounseling.com/pro/"
INS = "Anthem & UnitedHealthcare"
INS_D = "In-network with Anthem and UnitedHealthcare. Sliding-scale self-pay if you are not."

# per ad id: text swaps (old -> new), headlines pinned to H1, whether to pin INS to H2, new final URL
PLAN = {
    # Teens (for parents)
    826741487177: dict(swap={"Teen Therapist, Ages 14+": "Sliding-Scale Self-Pay",
                             "Online therapy for teens 14 and up, anywhere in Ohio. Free 15-minute consultation.":
                             "Online therapy for teens anywhere in Ohio, by secure video. Free 15-minute call."},
                       h1=["Online Therapy for Teens", "Teen Counseling Online"], h2=True),
    826741487180: dict(swap={"Start Your New Quest": "Online Therapy for Teens",
                             "Online therapy for teens 14 and up, anywhere in Ohio. Free 15-minute consultation.":
                             "Online therapy for teens anywhere in Ohio, by secure video. Free 15-minute call."},
                       h1=["Online Therapy for Teens", "Teen Counseling Online"], h2=True),
    # Online therapy Ohio: also move from / to /pro/
    826012667987: dict(h1=["Online Therapy in Ohio", "Online Counseling in Ohio", "Virtual Therapist in Ohio"], h2=True, url=PRO),
    826012667990: dict(h1=["Online Therapy in Ohio", "Online Counseling in Ohio", "Virtual Therapist in Ohio"], h2=True, url=PRO),
    # Couples and family (ad group paused): just the landing page
    825888944832: dict(url=PRO),
    825888944835: dict(url=PRO),
    # Black therapist
    830219555519: dict(swap={"Adults, Couples, Teens 14+": "Adults, Couples and Teens"},
                       h1=["Black Therapist, Online"], h2=True),
    # Insurance: topic headlines already filter; pin online to H1 alongside them? keep topic first, online second
    825888981114: dict(h2pins=["Online Therapy in Ohio"], h1=["Therapist Who Takes Anthem", "UnitedHealthcare Therapist", "In-Network With Anthem"]),
    825888981117: dict(h2pins=["Online Therapy in Ohio"], h1=["Therapist Who Takes Anthem", "UnitedHealthcare Therapist"]),
}

rows = ads.search(
    "SELECT ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad.resource_name, ad_group_ad.ad.final_urls, "
    "ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions "
    f"FROM ad_group_ad WHERE campaign.id = {CAMPAIGN} AND ad_group_ad.status != 'REMOVED'")
ops = []
for r in rows:
    ad = r["adGroupAd"]["ad"]; aid = int(ad["id"]); p = PLAN.get(aid)
    if not p:
        continue
    rsa = ad["responsiveSearchAd"]
    sw = p.get("swap", {})
    h1 = set(p.get("h1", [])); h2 = set(p.get("h2pins", [])) | ({INS} if p.get("h2") else set())
    heads = []
    for h in rsa["headlines"]:
        t = sw.get(h["text"], h["text"])
        assert len(t) <= 30, t
        item = {"text": t}
        if t in h1: item["pinnedField"] = "HEADLINE_1"
        elif t in h2: item["pinnedField"] = "HEADLINE_2"
        heads.append(item)
    descs = []
    for d in rsa["descriptions"]:
        t = sw.get(d["text"], d["text"])
        assert len(t) <= 90, t
        item = {"text": t}
        if t == INS_D and (p.get("h2") or p.get("h2pins")): item["pinnedField"] = "DESCRIPTION_2"
        descs.append(item)
    missing = (h1 | h2) - {h["text"] for h in heads}
    assert not missing, (aid, missing)
    upd = {"resourceName": ad["resourceName"]}; mask = []
    if p.get("h1") or sw:
        upd["responsiveSearchAd"] = {"headlines": heads, "descriptions": descs}
        mask += ["responsive_search_ad.headlines", "responsive_search_ad.descriptions"]
    if p.get("url") and ad.get("finalUrls") != [p["url"]]:
        upd["finalUrls"] = [p["url"]]; mask.append("final_urls")
    if not mask:
        continue
    print(f"\n{r['adGroup']['name']} / ad {aid}: {', '.join(mask)}")
    for h in heads:
        if h.get("pinnedField") or h["text"] in sw.values(): print(f"   H {h['text']}  {h.get('pinnedField','')}")
    for d in descs:
        if d.get("pinnedField") or d["text"] in sw.values(): print(f"   D {d['text']}  {d.get('pinnedField','')}")
    if "final_urls" in mask: print(f"   URL {ad.get('finalUrls')} -> {p['url']}")
    ops.append({"update": upd, "updateMask": ",".join(mask)})

ads.mutate("ads", ops, not apply)
print("\nApplied." if apply else "\nValidated OK. Nothing changed.")
