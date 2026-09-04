# -*- coding: utf-8 -*-
"""
Pull the 报名表 Google Sheet (public, read-only via the gviz CSV endpoint) and rewrite data.json.

Deterministic — no AI involved. Manual knowledge is preserved across runs:
  * per-entry `cat`, `poster`, `location` from the previous data.json are kept (keyed by title / name)
  * `overrides` in data.json always win (e.g. dates taken from a poster rather than the sheet)
  * `seen` records the first date each entry appeared; entries first seen within NEW_DAYS get the NEW badge

Usage: python3 sync_sheet.py [--offline act.csv ppl.csv]   (offline mode for tests)
Exit code 0 always; prints a one-line summary; writes data.json only if content changed.
"""
import csv, io, json, re, sys, os, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
SHEET_ID = "1gFd3Eae9j_l5CS6Ij2brwzEocD50e3SlBaAhMm13tN0"
NEW_DAYS = 28
TODAY = datetime.datetime.now(ZoneInfo("America/New_York")).date()


def fetch_csv(sheet):
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&headers=1&sheet="
           + urllib.parse.quote(sheet))
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


def rows(text):
    rd = csv.reader(io.StringIO(text))
    header = next(rd)
    out = []
    for r in rd:
        r = [c.strip() for c in r] + [""] * len(header)
        if not any(r[:7]): continue
        out.append(dict(zip(header, r)))
    return out


# ---------- helpers ----------
def clean(s): return re.sub(r"[ \t]+", " ", s.replace("\r", "")).strip()
def oneline(s): return " ".join(x.strip() for x in clean(s).split("\n") if x.strip())
def dotjoin(s): return " · ".join(x.strip() for x in clean(s).split("\n") if x.strip())

DATE = r"(\d{2,4})[/\.年](\d{1,2})[/\.月](\d{1,2})"
def to_date(y, m, d):
    y = int(y); y = y + 2000 if y < 100 else y
    return datetime.date(y, int(m), int(d))

def parse_dates(s):
    """Return (start, end) or (None, None). Handles 26/9/14-26/9/28, 26/9/19, 2026年11月7号晚, 26/09/20-27/1/20."""
    m = re.findall(DATE, s)
    if not m: return None, None
    try:
        start = to_date(*m[0]); end = to_date(*m[1]) if len(m) > 1 else start
        return start, end
    except ValueError:
        return None, None

def date_display(start, end, raw):
    if not start: return raw
    if start == end:
        suffix = " 晚" if "晚" in raw else ""
        return f"{start.isoformat()}{suffix}"
    if start.year == end.year:
        return f"{start.isoformat()} – {end:%m-%d}"
    return f"{start.isoformat()} – {end.isoformat()}"

EVENT_CAT_RULES = [
    ("offline", r"线下|聚会|Kyoto|京都"),
    ("book", r"读书|共读|book club"),
    ("workshop", r"工作坊|训练营|陪伴营|共学营|体验课|课程|认证|培训班"),
    ("media", r"公众号|播客|视频号|自媒体|YouTube|油管|系列"),
    ("good", r"公益|成长|心理|急救|正念|冥想|社群|教练|coach"),
    ("online", r"分享会"),
]
PROJECT_CAT_RULES = [
    ("book", r"读书|共读|book club"),
    ("workshop", r"工作坊|训练营|课程"),
    ("media", r"公众号|播客|视频号|自媒体|YouTube|油管|小红书|Linkedin|电台"),
    ("good", r"公益|成长|心理|coach|教练|正念|社区|急救|advocate"),
]
def classify(text, rules):
    for cat, pat in rules:
        if re.search(pat, text, re.I): return cat
    return "other"

def norm_name(s): return re.sub(r"\s+", "", s).lower()


def main():
    old = json.load(open("data.json", encoding="utf-8")) if os.path.exists("data.json") else {}
    overrides = old.get("overrides", {})
    seen = dict(old.get("seen", {}))
    old_events = {e["title"]: e for e in old.get("events", [])}
    old_projects = {p["name"]: p for p in old.get("projects", [])}

    if len(sys.argv) > 2 and sys.argv[1] == "--offline":
        act_txt, ppl_txt = open(sys.argv[2], encoding="utf-8").read(), open(sys.argv[3], encoding="utf-8").read()
    else:
        act_txt, ppl_txt = fetch_csv("活动"), fetch_csv("个人信息")
    act, ppl = rows(act_txt), rows(ppl_txt)

    # ---- projects ----
    projects, contact_by_name = [], {}
    for r in ppl:
        name = clean(r.get("姓名", ""))
        if not name: continue
        desc = oneline(r.get("在做的事情", ""))
        contact = dotjoin(r.get("希望感兴趣的小伙伴怎么联系你", "")) or "—"
        contact_by_name[norm_name(name)] = contact
        prev = old_projects.get(name)
        cat = prev["cat"] if prev else classify(desc, PROJECT_CAT_RULES)
        projects.append({"cat": cat, "name": name, "city": clean(r.get("所在城市和州", "")) or "—",
                         "desc": desc, "contact": contact})
        seen.setdefault(name, TODAY.isoformat())

    # ---- events ----
    events = []
    for r in act:
        title = clean(r.get("活动名称", ""))
        org = clean(r.get("组织者", ""))
        if not title: continue
        desc = clean(r.get("活动简介", "")) or title
        form = clean(r.get("活动形式", ""))
        raw_date = clean(r.get("活动日期或频率", "")) or "时间待定"
        join = clean(r.get("如何参与", ""))
        prev = old_events.get(title)
        ov = overrides.get(title, {})

        start, end = parse_dates(raw_date)
        if "start" in ov: start = datetime.date.fromisoformat(ov["start"])
        if "end" in ov: end = datetime.date.fromisoformat(ov["end"])
        meta = [ov.get("date_display") or date_display(start, end, raw_date)]
        if form: meta.append(form)
        if start and ov.get("keep_raw_date") and raw_date not in meta: meta.append(raw_date)

        ev = {"cat": (prev["cat"] if prev else ov.get("cat") or classify(title + " " + desc, EVENT_CAT_RULES)),
              "title": title, "meta": meta, "desc": desc}
        # 如何参与: real URL -> button; 微信小店 deep link -> meta; contact-like text -> contact; other text -> meta
        contact = contact_by_name.get(norm_name(org))
        m = re.search(r"https?://\S+", join)
        if m:
            ev["joinLink"] = m.group(0)
            note = clean(join.replace(m.group(0), "")).strip("（）() ")
            ev["joinLabel"] = f"参与详情 · {note}" if note and len(note) <= 16 else "参与详情"
        elif join.startswith("#微信小店"):
            meta.append("微信小店：" + join.split("://", 1)[1].split("/")[0])
        elif join and re.search(r"微信|电邮|邮箱|email|@|电话", join, re.I):
            if not contact: contact = join
        elif join:
            meta.append(join)
        if not contact and prev:
            contact = prev["contact"].split(" · ", 1)[1] if " · " in prev["contact"] else None
        contact = (contact or "微信").rstrip("。 ")
        for extra in ov.get("meta_extra", []):
            if extra not in meta: meta.append(extra)
        ev["contact"] = f"组织者：{org} · {contact or '微信'}"
        if start: ev["start"], ev["end"] = start.isoformat(), end.isoformat()
        if prev and prev.get("location"): ev["location"] = prev["location"]
        if ov.get("location"): ev["location"] = ov["location"]
        poster = (prev or {}).get("poster") or ov.get("poster")
        if poster and os.path.exists(os.path.join("posters", poster)): ev["poster"] = poster
        events.append(ev)
        seen.setdefault(title, TODAY.isoformat())

    keys_now = {e["title"] for e in events} | {p["name"] for p in projects}
    seen = {k: v for k, v in seen.items() if k in keys_now}
    cutoff = TODAY - datetime.timedelta(days=NEW_DAYS)
    new_since = [k for k, v in seen.items() if datetime.date.fromisoformat(v) >= cutoff]

    data = {"updated_note": old.get("updated_note", "由每周自动任务从报名表重新生成；字段说明见 RUNBOOK.md"),
            "synced": TODAY.isoformat(), "overrides": overrides, "seen": seen,
            "new_since": new_since, "events": events, "projects": projects}

    missing = [e["title"] for e in events if not e.get("poster") and e["title"] not in old_events]
    old_cmp = {k: v for k, v in old.items() if k != "synced"}
    new_cmp = {k: v for k, v in data.items() if k != "synced"}
    if old_cmp == new_cmp:
        print(f"no change: {len(events)} events, {len(projects)} projects")
        return
    json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    added = [k for k in keys_now if k not in old_events and k not in old_projects]
    print(f"updated data.json: {len(events)} events, {len(projects)} projects; added {added}; new events without poster: {missing}")
    open("NEEDS_POSTER.md", "w", encoding="utf-8").write(
        "# 待补海报\n\n" + ("\n".join(f"- {t}" for t in missing) if missing else "（无）") + "\n")


if __name__ == "__main__":
    main()
