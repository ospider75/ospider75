import html
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = "ospider75"
TOKEN = os.environ["GITHUB_TOKEN"]

COLORS = [
    "#0d1117",  # 0 commits (preto GitHub dark)
    "#0a2540",  # 1-2 commits (azul petróleo escuro)
    "#0052cc",  # 3-5 commits (azul cobalto)
    "#0099ff",  # 6-9 commits (azul vibrante)
    "#00f0ff",  # 10+ commits (ciano neon)
]

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def get_color(count):
    if count == 0:
        return COLORS[0]
    if count <= 2:
        return COLORS[1]
    if count <= 5:
        return COLORS[2]
    if count <= 9:
        return COLORS[3]
    return COLORS[4]


def truncate_title(title, max_len=21):
    if len(title) <= max_len:
        return title
    return title[: max_len - 1].rstrip("_") + "…"


def wrap_text(text, max_chars=34, max_lines=2):
    if not text:
        return ["No description provided."]
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines and current:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = lines[-1][: max_chars - 3].rstrip() + "..."
    return lines


now = datetime.now(timezone.utc)
start = now - timedelta(days=90)

query = """
query($userName:String!, $from:DateTime!, $to:DateTime!) {
  user(login: $userName) {
    repositories(first: 20, privacy: PUBLIC, isFork: false, ownerAffiliations: OWNER, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        description
        url
        pushedAt
        stargazerCount
        primaryLanguage {
          name
          color
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {
        "userName": USERNAME,
        "from": start.strftime("%Y-%m-%dT00:00:00Z"),
        "to": now.strftime("%Y-%m-%dT23:59:59Z"),
    },
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    },
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))["data"]["user"]

# 1. Gerar Grade de Commits estilo GitHub (3 meses, zero padding, preto -> azul)
calendar = data["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total_3m = calendar["totalContributions"]

pixel_size = 18
pad_left = 44
pad_top = 46
pad_right = 20
pad_bottom = 36

grid_w = len(weeks) * pixel_size
grid_h = 7 * pixel_size
svg_w = pad_left + grid_w + pad_right
svg_h = pad_top + grid_h + pad_bottom

rects = []
month_labels = []
last_month = None

for col_idx, week in enumerate(weeks):
    days = week["contributionDays"]
    if days:
        first_day_month = int(days[0]["date"].split("-")[1])
        if first_day_month != last_month:
            if col_idx > 0 or len(days) >= 4:
                x_pos = pad_left + col_idx * pixel_size
                month_labels.append(
                    f'<text x="{x_pos}" y="{pad_top - 10}" fill="#8b949e" font-family="monospace" font-size="11">{MONTH_NAMES[first_day_month - 1]}</text>'
                )
            last_month = first_day_month

    for row_idx, day in enumerate(days):
        color = get_color(day["contributionCount"])
        x = pad_left + col_idx * pixel_size
        y = pad_top + row_idx * pixel_size
        rects.append(
            f'<rect x="{x}" y="{y}" width="{pixel_size}" height="{pixel_size}" fill="{color}" />'
        )

day_labels = [
    f'<text x="{pad_left - 8}" y="{pad_top + 1 * pixel_size + 13}" fill="#8b949e" font-family="monospace" font-size="11" text-anchor="end">Mon</text>',
    f'<text x="{pad_left - 8}" y="{pad_top + 3 * pixel_size + 13}" fill="#8b949e" font-family="monospace" font-size="11" text-anchor="end">Wed</text>',
    f'<text x="{pad_left - 8}" y="{pad_top + 5 * pixel_size + 13}" fill="#8b949e" font-family="monospace" font-size="11" text-anchor="end">Fri</text>',
]

legend_y = pad_top + grid_h + 14
legend_box = 11
legend_gap = 3
more_x = pad_left + grid_w
boxes_start_x = more_x - 34 - (len(COLORS) * (legend_box + legend_gap))
less_x = boxes_start_x - 6

legend_items = [
    f'<text x="{less_x}" y="{legend_y + 9}" fill="#8b949e" font-family="monospace" font-size="10" text-anchor="end">Less</text>'
]
for i, c in enumerate(COLORS):
    bx = boxes_start_x + i * (legend_box + legend_gap)
    stroke = ' stroke="#1e293b" stroke-width="1"' if i == 0 else ""
    legend_items.append(
        f'<rect x="{bx}" y="{legend_y}" width="{legend_box}" height="{legend_box}" fill="{c}"{stroke} />'
    )
legend_items.append(
    f'<text x="{more_x}" y="{legend_y + 9}" fill="#8b949e" font-family="monospace" font-size="10" text-anchor="end">More</text>'
)

commits_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" shape-rendering="crispEdges">
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="#0b1221" stroke="#1e293b" stroke-width="2" />
  <text x="16" y="22" fill="#e6edf3" font-family="monospace" font-size="12" font-weight="bold">{total_3m} contributions in the last 3 months</text>
  {"".join(month_labels)}
  {"".join(day_labels)}
  {"".join(rects)}
  <rect x="{pad_left}" y="{pad_top}" width="{grid_w}" height="{grid_h}" fill="none" stroke="#1e293b" stroke-width="1" />
  {"".join(legend_items)}
</svg>'''

with open("commits-3m.svg", "w", encoding="utf-8") as f:
    f.write(commits_svg)

# 2. Filtrar e Ordenar: Estrelas DESC -> Mais Recentes (pushedAt) DESC
all_repos = [
    r for r in data["repositories"]["nodes"]
    if r["name"].lower() != USERNAME.lower()
]
all_repos.sort(key=lambda r: (r["stargazerCount"], r["pushedAt"] or ""), reverse=True)
top_repos = all_repos[:3]

repo_links_md = []
for idx, repo in enumerate(top_repos):
    raw_name = repo["name"]
    display_name = html.escape(truncate_title(raw_name))
    stars = repo["stargazerCount"]
    lang = repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else "Code"
    lang_color = repo["primaryLanguage"]["color"] if repo["primaryLanguage"] else "#00aaff"
    desc_lines = [html.escape(line) for line in wrap_text(repo["description"])]

    desc_svg = ""
    for line_idx, line in enumerate(desc_lines):
        desc_svg += f'<text x="16" y="{54 + line_idx * 18}" fill="#94a3b8" font-family="monospace" font-size="12">{line}</text>'

    card_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="280" height="125" viewBox="0 0 280 125" shape-rendering="crispEdges">
  <rect x="0" y="0" width="280" height="125" fill="#0b1221" stroke="#1e293b" stroke-width="2" />
  <rect x="0" y="0" width="4" height="125" fill="#ff2a2a" />
  <text x="16" y="30" fill="#00aaff" font-family="monospace" font-size="15" font-weight="bold">{display_name}</text>
  <text x="264" y="30" fill="#ff2a2a" font-family="monospace" font-size="13" font-weight="bold" text-anchor="end">★ {stars}</text>
  {desc_svg}
  <rect x="16" y="100" width="8" height="8" fill="{lang_color}" />
  <text x="30" y="108" fill="#cbd5e1" font-family="monospace" font-size="12">{html.escape(lang)}</text>
</svg>'''

    filename = f"repo-{idx}.svg"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(card_svg)

    repo_links_md.append(f'<a href="{repo["url"]}"><img src="./{filename}" alt="{html.escape(raw_name)}" /></a>')

# 3. Atualizar README.md
with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

new_block = (
    "<!-- TOP_REPOS_START -->\n"
    '<p align="left">\n  ' + "\n  ".join(repo_links_md) + "\n</p>\n"
    "<!-- TOP_REPOS_END -->"
)

if "<!-- TOP_REPOS_START -->" in readme and "<!-- TOP_REPOS_END -->" in readme:
    updated_readme = re.sub(
        r"<!-- TOP_REPOS_START -->.*?<!-- TOP_REPOS_END -->",
        new_block,
        readme,
        flags=re.DOTALL,
    )
else:
    updated_readme = f"### 📌 Featured Projects\n\n{new_block}\n\n---\n\n{readme}"

with open("README.md", "w", encoding="utf-8") as f:
    f.write(updated_readme)
