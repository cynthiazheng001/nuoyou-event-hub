# -*- coding: utf-8 -*-
"""
北美诺友活动中心 — page generator.

Reads data.json (+ posters/*.jpg), writes site/index.html (single self-contained file).
Run:  python3 build.py            (uses today's date, America/New_York)
      python3 build.py 2026-09-03 (pin a date, for reproducible builds)
"""
import json, base64, datetime, sys, os, urllib.parse
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

TODAY = (datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
         else datetime.datetime.now(ZoneInfo("America/New_York")).date())

data = json.load(open("data.json", encoding="utf-8"))
NEW_SINCE = data.get("new_since", [])


def poster_uri(fname):
    p = os.path.join("posters", fname)
    if not os.path.exists(p):
        print(f"WARNING: poster missing: {fname}", file=sys.stderr)
        return None
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()


def cal(title, start, end_incl, details, location):
    e = end_incl + datetime.timedelta(days=1)
    q = urllib.parse.urlencode({"action": "TEMPLATE", "text": title,
                                "dates": f"{start:%Y%m%d}/{e:%Y%m%d}",
                                "details": details, "location": location})
    return "https://calendar.google.com/calendar/render?" + q


EVENTS = []
for e in data["events"]:
    ev = {k: v for k, v in e.items() if k not in ("start", "end", "location", "poster")}
    if e.get("poster"):
        u = poster_uri(e["poster"])
        if u: ev["thumb"] = u
    if e.get("start"):
        start = datetime.date.fromisoformat(e["start"])
        end = datetime.date.fromisoformat(e.get("end") or e["start"])
        if end < TODAY:
            ev["status"] = "past"
        elif start <= TODAY:
            ev["status"] = "ongoing"; ev["meta"] = ev["meta"] + ["进行中"]
        else:
            ev["status"] = "upcoming"
        if ev["status"] != "past":
            ev["calLink"] = cal(e["title"], start, end, e["desc"], e.get("location", "线上"))
        ev["_sort"] = start.toordinal()
    else:
        until = data.get("overrides", {}).get(e["title"], {}).get("upcoming_until"); ev["status"] = "upcoming" if until and TODAY <= datetime.date.fromisoformat(until) else "ongoing"; ev["_sort"] = 0
    EVENTS.append(ev)

ongoing = [e for e in EVENTS if e["status"] == "ongoing"]
upcoming = sorted([e for e in EVENTS if e["status"] == "upcoming"], key=lambda e: e["_sort"])
past = sorted([e for e in EVENTS if e["status"] == "past"], key=lambda e: -e["_sort"])
for e in EVENTS: e.pop("_sort")
PROJECTS = data["projects"]

CSS = open("style.css", encoding="utf-8").read()
JS = open("app.js", encoding="utf-8").read()
js = lambda o: json.dumps(o, ensure_ascii=False, indent=2)

page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>北美诺友活动中心</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <div class="eyebrow">北美诺友 · NUOYOU NORTH AMERICA</div>
    <h1>活动中心 &amp; 搞事情档案</h1>
    <p>分享行动，连接同频，让每一个想搞事情的人找到组织。这里汇总了近期活动日程，以及社区伙伴们正在做的事情 —— 点击分类标签可以筛选。</p>
    <div class="updated">最后更新：{TODAY:%Y年%m月%d日} ｜ 数据来源：九周年北美分享会报名表（“活动”表 + “个人信息”表）</div>
  </header>

  <h2 class="section-title">近期活动 <span class="count" id="event-count"></span></h2>
  <p class="section-sub">分“即将进行”“长期 / 进行中”“已举办”三个标签页；即将进行的活动按日期从近到远排列。数据来自报名表“活动”表。</p>
  <div class="tabs" id="event-tabs">
    <button class="tab active" data-tab="upcoming">即将进行 <span class="tab-count" id="tab-upcoming-count"></span></button>
    <button class="tab" data-tab="ongoing">长期 / 进行中 <span class="tab-count" id="tab-ongoing-count"></span></button>
    <button class="tab" data-tab="past">已举办 <span class="tab-count" id="tab-past-count"></span></button>
  </div>
  <div class="filters" id="event-filters"></div>
  <div class="events-grid" id="events-upcoming"></div>
  <div class="events-grid hidden" id="events-ongoing"></div>
  <div class="events-grid hidden" id="events-past"></div>

  <h2 class="section-title">社区Launch诺友 <span class="count" id="project-count"></span></h2>
  <p class="section-sub">社区伙伴们正在做的事，欢迎点击联系方式敲门。数据来自报名表“个人信息”表。</p>
  <div class="filters" id="project-filters"></div>
  <div class="events-grid projects" id="projects-container"></div>

  <footer>
    本页面由 Claude 自动生成，数据来自
    <a href="https://docs.google.com/spreadsheets/d/1gFd3Eae9j_l5CS6Ij2brwzEocD50e3SlBaAhMm13tN0/edit" target="_blank">九周年北美分享会报名表</a>。
    如信息有误或需要更新，请在群内或报名表中留言。
  </footer>
</div>

<script>
const EVENTS_UPCOMING = {js(upcoming)};
const EVENTS_ONGOING = {js(ongoing)};
const EVENTS_PAST = {js(past)};
const PROJECTS = {js(PROJECTS)};
const NEW_SINCE = {js(NEW_SINCE)};
{JS}
</script>
</body>
</html>
"""
os.makedirs("site", exist_ok=True)
open("site/index.html", "w", encoding="utf-8").write(page)
print(f"built site/index.html for {TODAY}: events {len(EVENTS)} (upcoming {len(upcoming)}, ongoing {len(ongoing)}, past {len(past)}), projects {len(PROJECTS)}, {len(page.encode())} bytes")
