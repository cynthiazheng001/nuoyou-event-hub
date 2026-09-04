# 北美诺友活动中心 — 每周更新流程 (RUNBOOK)

Site: https://nuoyou-north-america.netlify.app
Repo: https://github.com/cynthiazheng001/nuoyou-event-hub (push to `main` → Netlify auto-deploys `site/`)
Source of truth: Google Sheet 九周年北美分享会报名表, id `1gFd3Eae9j_l5CS6Ij2brwzEocD50e3SlBaAhMm13tN0`
(owned by bekids2023@gmail.com, shared with jinjiezheng@gmail.com). Two sheets matter: **活动** and **个人信息**.
The third sheet (`Sheet1`, an old merged table) is ignored.

## Files

| file | what |
|---|---|
| `data.json` | the page's data: `events[]`, `projects[]`, `new_since[]` — the ONLY thing the weekly job edits |
| `posters/*.jpg` | poster cache (in-cell images from the sheet's 活动海报 column). Cannot be fetched from the cloud — see §Posters |
| `build.py` | `data.json` + posters → `site/index.html` (single self-contained file, posters inlined as base64) |
| `style.css`, `app.js` | page styling / rendering; do not touch during a routine update |
| `site/index.html` | build output, committed so Netlify serves it without a build step |

## Weekly job — GitHub Actions, no AI, no Mac

`.github/workflows/weekly.yml` runs every Monday 12:00 UTC (and on demand via the Actions tab → "weekly refresh" → Run workflow):

1. `sync_sheet.py` downloads the two sheets as CSV through the public gviz endpoint (the sheet is shared as "anyone with the link can edit", so no login is needed) and rewrites `data.json`.
   Rules are deterministic; previous `cat` / `poster` / `location` per entry are preserved; `overrides` in `data.json` always win; `seen` tracks first-appearance dates and drives the NEW badge (28 days).
2. `build.py` renders `site/index.html`.
3. If anything changed, the bot commits and pushes to `main`; Netlify (linked to this repo, publish dir `site/`) deploys within ~30 s. No change → no commit → no deploy.
4. `NEEDS_POSTER.md` lists new events that have no poster file yet. Check it after adding a row with a poster to the sheet; see §Posters.

Pushing a change to `data.json`, `posters/`, `build.py`, `app.js` or `style.css` also triggers a rebuild (sync is skipped on push so a manual edit is not overwritten before it deploys; the next Monday run re-syncs from the sheet — put durable manual facts in `overrides`, not in `events` directly).

## Field rules for `data.json`

Event:
```
{ "cat": "book|workshop|media|good|offline|online|other",
  "title": "...", "meta": ["日期或频率", "线上|线下|录播课", ...optional extras],
  "desc": "...", "contact": "组织者：<name> · <contact from sheet>",
  "start": "YYYY-MM-DD", "end": "YYYY-MM-DD",      // only if the sheet gives real dates; omit for 长期/滚动开/每月一期
  "location": "Kyoto, Japan",                       // optional, for the calendar link; default 线上
  "joinLink": "https://...", "joinLabel": "参与详情", // only real URLs; 微信小店 / 磁场活动 strings go into meta or contact instead
  "poster": "file.jpg" }                            // only if the file exists in posters/
```
- Date formats in the sheet look like `26/9/14-26/9/28`, `26/09/20-27/1/20`, `2026年11月7号晚`, `26/9/19`. Convert to ISO. `build.py` derives status (upcoming / ongoing / past) from `start`/`end` and today's date, and generates the Google Calendar link — do not hand-write those.
- Category mapping: 读书会/共读 → book; 工作坊/训练营/课程/认证 → workshop; 公众号/播客/视频号/自媒体 → media; 公益/成长/心理/教练/正念/社区 → good; 线下聚会 → offline; 线上分享会 → online; else other.
- Never invent data. If a cell is empty, leave the field out or write "—".

Project: `{ "cat", "name", "city", "desc", "contact" }` — copy the sheet text verbatim; `city` "—" if empty.

## Posters

The sheet's poster column holds in-cell images. The Drive export of this sheet fails ("file too large"), so the weekly cloud job **cannot** fetch new posters. Rule: if a new event appears and `posters/` has no file for it, publish the event without a poster and tell Jinjie: "X 有新活动但没海报，回复「补海报」我来补". Fetching posters requires her Mac's logged-in browser (the `sheets-images-rt` URLs in the Sheets tab, resized to ≤560 px wide JPEG q0.8), then add the file to `posters/` and set `"poster"` in `data.json`.

## Build locally

```
python3 build.py             # today's date (America/New_York)
python3 build.py 2026-09-03  # pinned date
```
