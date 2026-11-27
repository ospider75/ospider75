import html
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = "ospider75"
TOKEN = os.environ["GITHUB_TOKEN"]

COLORS = [
    "#0b1221",  # 0 commits
    "#0a3673",  # 1-2 commits
    "#0066cc",  # 3-5 commits
    "#00aaff",  # 6-9 commits
    "#00f0ff",  # 10+ commits
]


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


def wrap_text(text, max_chars=42, max_lines=2):
    if not text:
        return ["Sem descrição."]
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
    repositories(first: 3, privacy: PUBLIC, isFork: false, ownerAffiliations: OWNER, orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        name
        description
        url
        stargazerCount
        primaryLanguage {
          name
          color
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
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

# 1. Gerar Grade de Commits (3 meses, zero padding)
weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]
pixel_size = 18
width = len(weeks) * pixel_size
height = 7 * pixel_size

rects = []
for col_idx, week in enumerate(weeks):
    for row_idx, day in enumerate(week["contributionDays"]):
        color = get_color(day["contributionCount"])
        rects.append(
            f'<rect x="{col_idx * pixel_size}" y="{row_idx * pixel_size}" '
            f'width="{pixel_size}" height="{pixel_size}" fill="{color}" />'
        )

commits_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" shape-rendering="crispEdges">
  {"".join(rects)}
</svg>'''

with open("commits-3m.svg", "w", encoding="utf-8") as f:
    f.write(commits_svg)

# 2. Gerar Cards SVG dos 3 Repositórios com Mais Estrelas
repos = data["repositories"]["nodes"]
repo_links_md = []

for idx, repo in enumerate(repos):
    name = html.escape(repo["name"])
    stars = repo["stargazerCount"]
    lang = repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else "Code"
    lang_color = repo["primaryLanguage"]["color"] if repo["primaryLanguage"] else "#00aaff"
    desc_lines = [html.escape(line) for line in wrap_text(repo["description"])]

    desc_svg = ""
    for line_idx, line in enumerate(desc_lines):
        desc_svg += f'<text x="16" y="{54 + line_idx * 18}" fill="#94a3b8" font-family="monospace" font-size="12">{line}</text>'

    card_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="275" height="125" viewBox="0 0 275 125" shape-rendering="crispEdges">
  <rect x="0" y="0" width="275" height="125" fill="#0b1221" stroke="#1e293b" stroke-width="2" />
  <rect x="0" y="0" width="4" height="125" fill="#ff2a2a" />
  <text x="16" y="30" fill="#00aaff" font-family="monospace" font-size="15" font-weight="bold">{name}</text>
  <text x="258" y="30" fill="#ff2a2a" font-family="monospace" font-size="13" font-weight="bold" text-anchor="end">★ {stars}</text>
  {desc_svg}
  <rect x="16" y="100" width="8" height="8" fill="{lang_color}" />
  <text x="30" y="108" fill="#cbd5e1" font-family="monospace" font-size="12">{html.escape(lang)}</text>
</svg>'''

    filename = f"repo-{idx}.svg"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(card_svg)

    repo_links_md.append(f'<a href="{repo["url"]}"><img src="./{filename}" alt="{name}" /></a>')

# 3. Atualizar bloco no README.md
with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

new_block = "<!-- TOP_REPOS_START -->\n<p align=\"left\">\n  " + "\n  ".join(repo_links_md) + "\n</p>\n<!-- TOP_REPOS_END -->"
updated_readme = re.sub(
    r"<!-- TOP_REPOS_START -->.*?<!-- TOP_REPOS_END -->",
    new_block,
    readme,
    flags=re.DOTALL,
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(updated_readme)
