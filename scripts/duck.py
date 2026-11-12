#!/usr/bin/env python3
"""
Duck Contribution Eater 🦆
Sinh ra SVG động: một con vịt đi zig-zag qua lưới contribution GitHub
và "ăn" từng ô có đóng góp. Thay thế cho Contribution Snake.

Usage:
    python duck.py --user ghism137 --out dist          # cần env GITHUB_TOKEN
    python duck.py --demo --out dist                   # dữ liệu giả để xem thử
"""
import argparse
import json
import os
import random
import urllib.request

CELL, GAP, MARGIN_X, MARGIN_TOP = 11, 3, 18, 18
PITCH = CELL + GAP
STEP_S = 0.055      # thời gian vịt đi qua 1 ô (giây)
PAUSE_S = 2.5       # nghỉ ở cuối trước khi lặp lại

THEMES = {
    "light": {
        "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "text": "#57606a",
    },
    "dark": {
        "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "text": "#8b949e",
    },
}

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionLevel weekday } }
      }
    }
  }
}"""


def fetch_grid(user: str, token: str):
    """Trả về (grid[col][row] ∈ {0..4}, totalContributions)."""
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    grid = []
    for w in cal["weeks"]:
        col = [None] * 7  # tuần đầu/cuối có thể thiếu ngày
        for d in w["contributionDays"]:
            col[d["weekday"]] = LEVEL_MAP[d["contributionLevel"]]
        grid.append(col)
    return grid, cal["totalContributions"]


def demo_grid(seed=137):
    rnd = random.Random(seed)
    grid = []
    for c in range(53):
        col = []
        for r in range(7):
            p = rnd.random()
            col.append(0 if p < 0.45 else 1 if p < 0.7 else 2 if p < 0.85 else 3 if p < 0.95 else 4)
        grid.append(col)
    return grid, sum(1 for col in grid for v in col if v) * 3


def duck_path(grid):
    """Đường đi boustrophedon: cột chẵn đi xuống, cột lẻ đi lên."""
    path = []
    for c, col in enumerate(grid):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        for r in rows:
            path.append((c, r))
    return path


def cell_xy(c, r):
    return MARGIN_X + c * PITCH, MARGIN_TOP + r * PITCH


DUCK = """
<g class="bob">
  <path d="M-8 1 L-12 -3 L-7 4 Z" fill="#F5C518" stroke="#C99700" stroke-width=".6"/>
  <ellipse cx="-1" cy="3" rx="7.5" ry="5.2" fill="#FFD43B" stroke="#C99700" stroke-width=".6"/>
  <ellipse cx="-2.5" cy="3" rx="3.8" ry="2.3" fill="#F5C518"/>
  <circle cx="4.5" cy="-4" r="4.3" fill="#FFD43B" stroke="#C99700" stroke-width=".6"/>
  <path d="M8.2 -5 L12.8 -3.6 L8.2 -1.8 Z" fill="#FF8C1A"/>
  <circle cx="5.6" cy="-5" r="1" fill="#1f2328"/>
  <circle cx="5.9" cy="-5.3" r=".3" fill="#fff"/>
</g>"""


def render(grid, total, theme, user):
    pal = THEMES[theme]
    cols = len(grid)
    W = MARGIN_X * 2 + cols * PITCH - GAP
    H = MARGIN_TOP + 7 * PITCH - GAP + 30
    path = duck_path(grid)
    n = len(path)
    T = n * STEP_S + PAUSE_S
    pct = lambda t: f"{100 * t / T:.3f}%"

    css, rects = [], []
    eaten = 0
    for i, (c, r) in enumerate(path):
        lvl = grid[c][r]
        if lvl is None:
            continue
        x, y = cell_xy(c, r)
        if lvl == 0:
            rects.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{pal["levels"][0]}"/>')
            continue
        eaten += 1
        t_eat = (i + 0.5) * STEP_S
        p1, p2 = pct(t_eat), pct(t_eat + 0.01)
        css.append(
            f"@keyframes e{i}{{0%,{p1}{{fill:{pal['levels'][lvl]}}}{p2},100%{{fill:{pal['levels'][0]}}}}}"
            f".e{i}{{animation:e{i} {T:.2f}s linear infinite}}"
        )
        rects.append(
            f'<rect class="e{i}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{pal["levels"][lvl]}"/>'
        )

    # keyframes cho vịt: dừng ở tâm từng ô theo thứ tự đường đi
    frames = []
    for i, (c, r) in enumerate(path):
        x, y = cell_xy(c, r)
        frames.append(f"{pct(i * STEP_S)}{{transform:translate({x + CELL / 2:.1f}px,{y + CELL / 2:.1f}px)}}")
    lx, ly = cell_xy(*path[-1])
    frames.append(f"100%{{transform:translate({lx + CELL / 2 + 40:.1f}px,{ly + CELL / 2:.1f}px)}}")
    css.append("@keyframes walk{" + "".join(frames) + "}")
    css.append(f".duck{{animation:walk {T:.2f}s linear infinite}}")
    css.append("@keyframes bob{from{transform:translateY(0) rotate(-4deg)}to{transform:translateY(-1.6px) rotate(4deg)}}")
    css.append(".bob{animation:bob .28s ease-in-out infinite alternate}")

    caption = f"quack! 🦆 ate {total} of {user}'s contributions this year — rubber-duck debugging, literally"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>{''.join(css)}
text{{font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{pal['text']}}}</style>
{''.join(rects)}
<g class="duck"><g transform="scale(1.3)">{DUCK}</g></g>
<text x="{MARGIN_X}" y="{H - 8}">{caption}</text>
</svg>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="ghism137")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        grid, total = demo_grid()
    else:
        grid, total = fetch_grid(a.user, os.environ["GITHUB_TOKEN"])
    os.makedirs(a.out, exist_ok=True)
    for theme, name in [("light", "duck.svg"), ("dark", "duck-dark.svg")]:
        with open(os.path.join(a.out, name), "w", encoding="utf-8") as f:
            f.write(render(grid, total, theme, a.user))
    print(f"OK: {total} contributions -> {a.out}/duck.svg, duck-dark.svg")


if __name__ == "__main__":
    main()
