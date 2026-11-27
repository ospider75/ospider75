import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = "ospider75"
TOKEN = os.environ["GITHUB_TOKEN"]

# Paleta OSPIDER (0 commits até 10+ commits)
COLORS = [
    "#0b1221",  # 0 commits (azul quase preto)
    "#0a3673",  # 1-2 commits (azul escuro)
    "#0066cc",  # 3-5 commits (azul cobalto)
    "#00aaff",  # 6-9 commits (azul vibrante)
    "#00f0ff",  # 10+ commits (ciano neon)
]

def get_color(count):
    if count == 0:
        return COLORS[0]
    elif count <= 2:
        return COLORS[1]
    elif count <= 5:
        return COLORS[2]
    elif count <= 9:
        return COLORS[3]
    return COLORS[4]

# Período exato de 13 semanas (91 dias = ~3 meses)
now = datetime.now(timezone.utc)
start = now - timedelta(days=90)

query = """
query($userName:String!, $from:DateTime!, $to:DateTime!) {
  user(login: $userName) {
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
    }
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
    data = json.loads(resp.read().decode("utf-8"))

weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

# Renderização SVG: grade pixelizada contínua (zero padding)
pixel_size = 18
cols = len(weeks)
rows = 7
width = cols * pixel_size
height = rows * pixel_size

rects = []
for col_idx, week in enumerate(weeks):
    for row_idx, day in enumerate(week["contributionDays"]):
        color = get_color(day["contributionCount"])
        x = col_idx * pixel_size
        y = row_idx * pixel_size
        rects.append(
            f'<rect x="{x}" y="{y}" width="{pixel_size}" height="{pixel_size}" fill="{color}" />'
        )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" shape-rendering="crispEdges">
  {"".join(rects)}
</svg>'''

with open("commits-3m.svg", "w", encoding="utf-8") as f:
    f.write(svg)
