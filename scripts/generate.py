"""RPG-style GitHub player card generator (stdlib only).

Edit the CONFIG block below to change your class, attributes and quests.
Level / XP / achievements are computed from your real GitHub data.
"""
import base64
import json
import math
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html import escape

# ================= CONFIG (edit me) =================
USERNAME = os.getenv("GITHUB_USERNAME", "amannarang04")
NAME = "AMAN NARANG"
CLASS = "AI / ML ENGINEER"
TITLE = "HACKATHON HERO"

# (code, description, value 0-100)
ATTRIBUTES = [
    ("INT", "AI / ML · GenAI · RAG", 85),
    ("DEX", "FULL STACK · React · Next.js", 78),
    ("STR", "BACKEND · FastAPI · Node", 72),
    ("WIS", "PRODUCT THINKING", 70),
    ("CHA", "SHIPPING SPEED", 80),
]

# (name, description, progress 0-100)
QUESTS = [
    ("VEYORA", "AI women's safety wearable", 60),
    ("Mentor Logins", "Student-mentor platform", 70),
    ("NextWave Transaction", "AI transaction categoriser", 55),
    ("Flight Price Tracker", "Flight price intelligence", 45),
]
# =====================================================

TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Accept": "application/vnd.github+json", "User-Agent": "aman-rpg-card"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def short(text, n):
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def parse(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def ago(iso):
    s = int((datetime.now(timezone.utc) - parse(iso)).total_seconds())
    if s < 3600:
        return f"{max(s // 60, 1)}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


def avatar_data(url):
    if not url:
        return None
    try:
        req = urllib.request.Request(url + ("&" if "?" in url else "?") + "s=160",
                                     headers={"User-Agent": "aman-rpg-card"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        mime = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(raw).decode()
    except Exception:
        return None


# ---------------- data ----------------
user = api(f"/users/{USERNAME}")
all_repos = api(f"/users/{USERNAME}/repos?per_page=100&sort=updated")
repos = [r for r in all_repos if not r.get("fork") and not r.get("archived")]
stars = sum(r.get("stargazers_count", 0) for r in repos)
forks = sum(r.get("forks_count", 0) for r in repos)
followers = user.get("followers", 0)
try:
    events = api(f"/users/{USERNAME}/events/public?per_page=30")
except Exception:
    events = []

age_days = (datetime.now(timezone.utc) - parse(user["created_at"])).days if user.get("created_at") else 0
lang_count = Counter(r["language"] for r in repos if r.get("language"))
lang_total = sum(lang_count.values()) or 1
langs = lang_count.most_common(6)

recent_active = bool(events) and (datetime.now(timezone.utc) - parse(events[0]["created_at"])).days < 7

# ---------------- level / xp ----------------
xp = len(repos) * 40 + stars * 25 + forks * 30 + followers * 15 + min(age_days, 730) // 5 + len(events) * 5
level = int(math.sqrt(xp / 20)) + 1
cur_xp = 20 * (level - 1) ** 2
next_xp = 20 * level ** 2
xp_pct = max(0.02, min(1, (xp - cur_xp) / (next_xp - cur_xp)))
rank = ("ROOKIE" if level < 3 else "APPRENTICE" if level < 6 else
        "BUILDER" if level < 10 else "VETERAN" if level < 15 else "LEGEND")

# ---------------- feed ----------------
def describe(ev):
    repo = short(ev["repo"]["name"].split("/")[-1], 22)
    t, p = ev["type"], ev.get("payload", {})
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits", [])) or 1
        return f"pushed {n} commit{'s' if n != 1 else ''} to {repo}"
    if t == "CreateEvent":
        return f"created {p.get('ref_type', 'repo')} in {repo}"
    if t == "PullRequestEvent":
        return f"{p.get('action', 'opened')} a PR in {repo}"
    if t == "IssuesEvent":
        return f"{p.get('action', 'opened')} an issue in {repo}"
    if t == "WatchEvent":
        return f"starred {repo}"
    if t == "ForkEvent":
        return f"forked {repo}"
    return None


feed = []
for ev in events:
    d = describe(ev)
    if d:
        feed.append((d, ago(ev["created_at"])))
    if len(feed) == 3:
        break
if not feed:
    feed = [("no recent public activity", "")]

# ---------------- svg helpers ----------------
LANG_COLORS = {
    "Python": "#3776AB", "JavaScript": "#F7DF1E", "TypeScript": "#3178C6", "Java": "#ED8B00",
    "HTML": "#E34F26", "CSS": "#1572B6", "C++": "#00599C", "C": "#A8B9CC",
    "Jupyter Notebook": "#F37626", "Shell": "#89E051", "Go": "#00ADD8", "Dart": "#00B4AB",
}
FALLBACK = ["#22D3EE", "#A78BFA", "#34D399", "#F472B6", "#FBBF24", "#60A5FA"]
H = 830


def panel(x, y, w, h, label):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#0b1220" stroke="#233247"/>'
            f'<text x="{x + 18}" y="{y + 26}" class="label">{label}</text>')


def bar(x, y, w, pct, color, delay=0.0, h=10):
    pct = max(0, min(100, pct)) / 100
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="#16213a"/>'
            f'<rect class="fill" style="animation-delay:{delay:.1f}s" x="{x}" y="{y}" '
            f'width="{w * pct:.1f}" height="{h}" rx="{h / 2}" fill="{color}"/>')


# ---- header ----
cx, cy, r = 110, 115, 54
hexpts = " ".join(f"{cx + r * math.cos(math.radians(a)):.1f},{cy + r * math.sin(math.radians(a)):.1f}"
                  for a in range(-90, 270, 60))
av = avatar_data(user.get("avatar_url"))
if av:
    avatar = (f'<clipPath id="hx"><polygon points="{hexpts}"/></clipPath>'
              f'<image href="{av}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
              f'clip-path="url(#hx)" preserveAspectRatio="xMidYMid slice"/>')
else:
    initials = "".join(w[0] for w in NAME.split()[:2])
    avatar = (f'<polygon points="{hexpts}" fill="url(#avg)"/>'
              f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" class="ini">{escape(initials)}</text>')
avatar += f'<polygon points="{hexpts}" fill="none" stroke="#22d3ee" stroke-width="2" class="pulse"/>'


def chip(x, y, label, value, accent):
    return (f'<rect x="{x}" y="{y}" width="94" height="52" rx="10" fill="#0e1729" stroke="#233247"/>'
            f'<rect x="{x}" y="{y}" width="3" height="52" rx="1.5" fill="{accent}"/>'
            f'<text x="{x + 14}" y="{y + 28}" class="num">{value}</text>'
            f'<text x="{x + 14}" y="{y + 44}" class="meta">{label}</text>')


chips = (chip(620, 62, "REPOS", len(repos), "#22d3ee") + chip(726, 62, "STARS", stars, "#fbbf24") +
         chip(620, 126, "FORKS", forks, "#a78bfa") + chip(726, 126, "FOLLOWERS", followers, "#34d399"))

header = f'''
<rect x="40" y="30" width="880" height="170" rx="16" fill="#0b1220" stroke="#233247"/>
<rect x="40" y="30" width="880" height="4" rx="2" fill="url(#acc)"/>
{avatar}
<text x="190" y="84" class="hero">{escape(NAME)}</text>
<text x="190" y="110" class="cls">{escape(CLASS)}  <tspan fill="#64748b">·</tspan>  <tspan fill="#a78bfa">{rank}</tspan></text>
<text x="190" y="134" class="gold">★ {escape(TITLE)}</text>
<text x="190" y="162" class="meta">EXPERIENCE  {xp} / {next_xp} XP</text>
{bar(190, 170, 410, xp_pct * 100, "url(#xpg)", 0.2, 12)}
{chips}
<rect x="842" y="62" width="62" height="116" rx="12" fill="#0e1729" stroke="#22d3ee" class="pulse"/>
<text x="873" y="92" text-anchor="middle" class="meta">LEVEL</text>
<text x="873" y="140" text-anchor="middle" class="lvl">{level}</text>
<text x="873" y="164" text-anchor="middle" class="meta">NEXT {level + 1}</text>
'''

# ---- attributes ----
attr = panel(40, 215, 430, 235, "ATTRIBUTES")
for i, (code, desc, val) in enumerate(ATTRIBUTES):
    y = 258 + i * 38
    col = FALLBACK[i % len(FALLBACK)]
    attr += (f'<text x="58" y="{y}" class="code">{code}</text>'
             f'<text x="100" y="{y}" class="meta">{escape(desc)}</text>'
             f'<text x="452" y="{y}" text-anchor="end" class="code">{val}</text>'
             + bar(58, y + 8, 394, val, col, 0.2 + i * 0.15))

# ---- achievements ----
ach_defs = [
    ("FIRST REPO", "★", len(repos) >= 1),
    ("COLLECTOR", "■", len(repos) >= 10),
    ("STARRED", "★", stars >= 1),
    ("POLYGLOT", "◆", len(lang_count) >= 3),
    ("POPULAR", "●", followers >= 10),
    ("VETERAN", "▲", age_days >= 365),
    ("ON FIRE", "▲", recent_active),
    ("HACKATHON", "◆", True),
]
ach = panel(490, 215, 430, 235, "ACHIEVEMENTS")
unlocked = sum(1 for a in ach_defs if a[2])
ach += f'<text x="902" y="241" text-anchor="end" class="meta">{unlocked}/{len(ach_defs)} UNLOCKED</text>'
for i, (nm, glyph, ok) in enumerate(ach_defs):
    x = 506 + (i % 4) * 104
    y = 256 + (i // 4) * 92
    stroke = "#fbbf24" if ok else "#26334a"
    fillc = "#fbbf24" if ok else "#334155"
    ach += (f'<rect x="{x}" y="{y}" width="96" height="82" rx="10" fill="#0e1729" stroke="{stroke}" '
            f'stroke-opacity="{.55 if ok else 1}"/>'
            f'<circle cx="{x + 48}" cy="{y + 30}" r="17" fill="{fillc}" fill-opacity="{.18 if ok else .25}" '
            f'stroke="{fillc}" class="{"glow" if ok else ""}"/>'
            f'<text x="{x + 48}" y="{y + 36}" text-anchor="middle" font-size="16" fill="{fillc}" '
            f'font-family="monospace">{glyph if ok else "?"}</text>'
            f'<text x="{x + 48}" y="{y + 68}" text-anchor="middle" class="{"ach" if ok else "achl"}">{nm}</text>')

# ---- quests ----
quest = panel(40, 465, 880, 190, "ACTIVE QUESTS")
for i, (qn, qd, pct) in enumerate(QUESTS):
    x = 58 + (i % 2) * 436
    y = 521 + (i // 2) * 72
    col = FALLBACK[i % len(FALLBACK)]
    quest += (f'<text x="{x}" y="{y}" class="title">{escape(short(qn, 26))}</text>'
              f'<text x="{x + 410}" y="{y}" text-anchor="end" class="code">{pct}%</text>'
              f'<text x="{x}" y="{y + 20}" class="desc">{escape(short(qd, 40))}</text>'
              + bar(x, y + 30, 410, pct, col, 0.3 + i * 0.15, 8))

# ---- inventory (languages) ----
inv = panel(40, 670, 430, 120, "INVENTORY // LANGUAGES")
bx = 58.0
legend = ""
for i, (lang, cnt) in enumerate(langs):
    w = 394 * cnt / lang_total
    c = LANG_COLORS.get(lang, FALLBACK[i % len(FALLBACK)])
    inv += f'<rect x="{bx:.1f}" y="706" width="{max(w - 2, 2):.1f}" height="12" rx="3" fill="{c}"/>'
    lx, ly = 58 + (i % 3) * 132, 744 + (i // 3) * 22
    legend += (f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{c}"/>'
               f'<text x="{lx + 16}" y="{ly}" class="meta">{escape(short(lang, 10))} {round(100 * cnt / lang_total)}%</text>')
    bx += w
if not langs:
    inv += '<rect x="58" y="706" width="394" height="12" rx="3" fill="#1e293b"/>'
inv += legend

# ---- quest log ----
log = panel(490, 670, 430, 120, "QUEST LOG")
for i, (txt, when) in enumerate(feed):
    y = 722 + i * 22
    log += (f'<text x="508" y="{y}" class="sub"><tspan fill="#22c55e">&gt;</tspan> {escape(txt)}</text>'
            f'<text x="902" y="{y}" text-anchor="end" class="meta">{escape(when)}</text>')

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

CSS = """
.title{fill:#f8fafc;font:600 15px monospace}
.desc{fill:#94a3b8;font:12px monospace}
.meta{fill:#64748b;font:11px monospace}
.label{fill:#22d3ee;font:11px monospace;letter-spacing:2px}
.hero{fill:url(#nm);font:700 36px monospace;letter-spacing:3px}
.cls{fill:#67e8f9;font:600 14px monospace;letter-spacing:1px}
.gold{fill:#fbbf24;font:600 13px monospace;letter-spacing:1px}
.sub{fill:#94a3b8;font:13px monospace}
.num{fill:#f8fafc;font:700 22px monospace}
.code{fill:#e2e8f0;font:700 13px monospace}
.lvl{fill:#22d3ee;font:700 44px monospace}
.ini{fill:#fff;font:700 36px monospace}
.ach{fill:#fbbf24;font:600 9.5px monospace;letter-spacing:.5px}
.achl{fill:#475569;font:600 9.5px monospace;letter-spacing:.5px}
.fill{transform-box:fill-box;transform-origin:left center;animation:grow 1.6s cubic-bezier(.2,.8,.2,1) both}
.pulse{animation:pulse 3s ease-in-out infinite}
.glow{animation:glow 3.5s ease-in-out infinite}
.blink{animation:blink 1.1s steps(2,start) infinite}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pulse{50%{opacity:.45}}
@keyframes glow{50%{fill-opacity:.38}}
@keyframes blink{50%{opacity:0}}
"""

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{H}" viewBox="0 0 960 {H}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#050816"/><stop offset="1" stop-color="#0b1020"/></linearGradient>
<linearGradient id="nm" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#f8fafc"/><stop offset=".65" stop-color="#67e8f9"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
<linearGradient id="acc" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#22d3ee"/><stop offset=".5" stop-color="#a78bfa"/><stop offset="1" stop-color="#fbbf24"/></linearGradient>
<linearGradient id="xpg" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#22d3ee"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
<linearGradient id="avg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#22d3ee"/><stop offset="1" stop-color="#7c3aed"/></linearGradient>
<style>{CSS}</style></defs>
<rect width="960" height="{H}" rx="18" fill="url(#bg)"/>
<rect x="1" y="1" width="958" height="{H - 2}" rx="18" fill="none" stroke="#1e293b"/>
<g opacity=".1" stroke="#334155"><path d="M0 205H960M0 460H960M0 660H960"/><path d="M160 0V{H}M480 0V{H}M800 0V{H}"/></g>
<text x="40" y="20" class="meta">PLAYER ONE // github.com/{USERNAME}</text>
<circle cx="866" cy="16" r="4" fill="#22c55e" class="pulse"/>
<text x="920" y="20" text-anchor="end" class="meta">ONLINE</text>
{header}
{attr}
{ach}
{quest}
{inv}
{log}
<text x="40" y="{H - 14}" class="meta">AUTO-UPDATED • {now}</text>
<text x="920" y="{H - 14}" text-anchor="end" class="meta">PRESS START<tspan class="blink"> █</tspan></text>
</svg>'''

os.makedirs("assets", exist_ok=True)
with open("assets/command-center.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print(f"ok: LV{level} {rank} xp={xp} repos={len(repos)} stars={stars} ach={unlocked}/{len(ach_defs)}")
