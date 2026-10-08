import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html import escape

USERNAME = os.getenv("GITHUB_USERNAME", "amannarang04")
TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "aman-github-command-center",
}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def short(text, n):
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def ago(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    s = int((datetime.now(timezone.utc) - dt).total_seconds())
    if s < 3600:
        return f"{max(s // 60, 1)}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


# ---------- data ----------
user = api(f"/users/{USERNAME}")
all_repos = api(f"/users/{USERNAME}/repos?per_page=100&sort=updated")
repos = [r for r in all_repos if not r.get("fork") and not r.get("archived")]
repos.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at") or ""), reverse=True)
top = repos[:6]

total_stars = sum(r.get("stargazers_count", 0) for r in repos)
total_forks = sum(r.get("forks_count", 0) for r in repos)

lang_count = Counter(r["language"] for r in repos if r.get("language"))
lang_total = sum(lang_count.values()) or 1
langs = lang_count.most_common(6)

try:
    events = api(f"/users/{USERNAME}/events/public?per_page=30")
except Exception:
    events = []


def describe(ev):
    repo = short(ev["repo"]["name"].split("/")[-1], 24)
    t = ev["type"]
    p = ev.get("payload", {})
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
    if len(feed) == 4:
        break
if not feed:
    feed = [("no recent public activity", "")]

COLORS = {
    "Python": "#3776AB", "JavaScript": "#F7DF1E", "TypeScript": "#3178C6",
    "Java": "#ED8B00", "HTML": "#E34F26", "CSS": "#1572B6", "C++": "#00599C",
    "C": "#A8B9CC", "Jupyter Notebook": "#F37626", "Shell": "#89E051",
    "Go": "#00ADD8", "Rust": "#DEA584", "PHP": "#777BB4", "Dart": "#00B4AB",
}
FALLBACK = ["#22D3EE", "#A78BFA", "#34D399", "#F472B6", "#FBBF24", "#60A5FA"]


def color(lang, i):
    return COLORS.get(lang, FALLBACK[i % len(FALLBACK)])


# ---------- svg pieces ----------
def tile(x, label, value, accent):
    return f'''
<g transform="translate({x},150)">
  <rect width="205" height="78" rx="12" fill="#0b1220" stroke="#233247"/>
  <rect x="0" y="0" width="205" height="3" rx="1.5" fill="{accent}" opacity=".9"/>
  <text x="18" y="46" class="num">{value}</text>
  <text x="18" y="66" class="meta">{label}</text>
</g>'''


tiles = "".join([
    tile(40, "REPOSITORIES", len(repos), "#22d3ee"),
    tile(265, "TOTAL STARS", total_stars, "#fbbf24"),
    tile(490, "TOTAL FORKS", total_forks, "#a78bfa"),
    tile(715, "FOLLOWERS", user.get("followers", 0), "#34d399"),
])

bar, x = "", 40.0
legend = ""
for i, (lang, cnt) in enumerate(langs):
    w = 880 * cnt / lang_total
    c = color(lang, i)
    bar += f'<rect x="{x:.1f}" y="262" width="{max(w - 2, 2):.1f}" height="12" rx="3" fill="{c}"/>'
    lx = 40 + (i % 3) * 295
    ly = 304 + (i // 3) * 22
    legend += (f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{c}"/>'
               f'<text x="{lx + 18}" y="{ly}" class="meta">{escape(lang)} · {round(100 * cnt / lang_total)}%</text>')
    x += w
if not langs:
    bar = '<rect x="40" y="262" width="880" height="12" rx="3" fill="#1e293b"/>'


def card(repo, x, y):
    name = escape(short(repo["name"], 22))
    desc = escape(short(repo.get("description") or "No description yet", 31))
    lang = repo.get("language") or "Code"
    dot = COLORS.get(lang, "#22D3EE")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    return f'''
<g transform="translate({x},{y})">
  <rect width="285" height="112" rx="12" fill="#0b1220" stroke="#233247"/>
  <rect width="4" height="112" rx="2" fill="{dot}"/>
  <text x="18" y="30" class="title">{name}</text>
  <text x="18" y="54" class="desc">{desc}</text>
  <circle cx="20" cy="88" r="5" fill="{dot}"/>
  <text x="32" y="92" class="meta">{escape(lang)}</text>
  <text x="165" y="92" class="meta">★ {stars}</text>
  <text x="205" y="92" class="meta">fork {forks}</text>
</g>'''


positions = [(40, 380), (335, 380), (630, 380), (40, 505), (335, 505), (630, 505)]
cards = "".join(card(r, *p) for r, p in zip(top, positions))

feed_svg = ""
for i, (text, when) in enumerate(feed):
    y = 704 + i * 24
    feed_svg += (f'<text x="62" y="{y}" class="sub"><tspan fill="#22c55e">&gt;</tspan> {escape(text)}</text>'
                 f'<text x="900" y="{y}" class="meta" text-anchor="end">{escape(when)}</text>')

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
H = 810

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{H}" viewBox="0 0 960 {H}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#050816"/><stop offset="1" stop-color="#0b1020"/></linearGradient>
<linearGradient id="name" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#f8fafc"/><stop offset=".6" stop-color="#67e8f9"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
<filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<style>
.title{{fill:#f8fafc;font:600 17px monospace}}
.desc{{fill:#94a3b8;font:13px monospace}}
.meta{{fill:#64748b;font:12px monospace}}
.label{{fill:#22d3ee;font:12px monospace;letter-spacing:2px}}
.hero{{fill:url(#name);font:700 40px monospace;letter-spacing:3px}}
.sub{{fill:#94a3b8;font:14px monospace}}
.role{{fill:#67e8f9;font:600 15px monospace;opacity:0;animation:role 9s infinite backwards}}
.r2{{animation-delay:3s}}.r3{{animation-delay:6s}}
.num{{fill:#f8fafc;font:700 30px monospace}}
.cursor{{animation:blink 1s steps(2,start) infinite}}
.pulse{{animation:pulse 3s ease-in-out infinite}}
.scan{{animation:scan 6s linear infinite}}
@keyframes role{{0%{{opacity:0}}5%{{opacity:1}}30%{{opacity:1}}35%{{opacity:0}}100%{{opacity:0}}}}
@keyframes blink{{50%{{opacity:0}}}}
@keyframes pulse{{50%{{opacity:.3}}}}
@keyframes scan{{from{{transform:translateY(0)}}to{{transform:translateY({H}px)}}}}
</style></defs>
<rect width="960" height="{H}" rx="18" fill="url(#bg)"/>
<rect x="1" y="1" width="958" height="{H - 2}" rx="18" fill="none" stroke="#1e293b"/>
<g opacity=".14" stroke="#334155"><path d="M0 110H960M0 240H960M0 350H960M0 680H960"/><path d="M160 0V{H}M320 0V{H}M640 0V{H}M800 0V{H}"/></g>
<rect class="scan" x="0" y="-60" width="960" height="60" fill="#22d3ee" opacity=".04"/>
<circle cx="830" cy="92" r="95" fill="#22d3ee" opacity=".08" class="pulse"/>
<circle cx="120" cy="700" r="110" fill="#a78bfa" opacity=".05" class="pulse"/>

<text x="40" y="45" class="label">AMAN // GITHUB COMMAND CENTER</text>
<circle cx="880" cy="39" r="6" fill="#22c55e" filter="url(#glow)" class="pulse"/>
<text x="895" y="44" class="meta">ONLINE</text>
<text x="40" y="95" class="hero">AMAN NARANG</text>
<text x="42" y="126" class="role">&gt; AI / ML developer<tspan class="cursor">_</tspan></text>
<text x="42" y="126" class="role r2">&gt; Full-stack builder<tspan class="cursor">_</tspan></text>
<text x="42" y="126" class="role r3">&gt; Product-focused engineer<tspan class="cursor">_</tspan></text>

{tiles}

<text x="40" y="252" class="label">LANGUAGE MIX</text>
{bar}
{legend}

<text x="40" y="368" class="label">LIVE PROJECT MATRIX</text>
{cards}

<rect x="40" y="640" width="880" height="140" rx="12" fill="#070d19" stroke="#1e293b"/>
<text x="62" y="668" class="label">RECENT ACTIVITY</text>
{feed_svg}

<text x="920" y="632" class="meta" text-anchor="end">AUTO-UPDATED • {now}</text>
</svg>'''

os.makedirs("assets", exist_ok=True)
with open("assets/command-center.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print(f"ok: {len(repos)} repos, {total_stars} stars, {len(feed)} events")
