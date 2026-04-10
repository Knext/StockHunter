#!/usr/bin/env python3
"""GitHub Pages용 리포트 인덱스 생성 + 보존 정책 적용.

- 대상 디렉토리(--site-dir) 내의 YYYY-MM-DD 폴더를 스캔
- 최신순 정렬 후 --keep 개수만큼만 남기고 나머지 삭제
- 루트에 index.html 생성 (한글, 최신 리포트로의 바로가기 포함)
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def discover_reports(site_dir: Path) -> list[Path]:
    """YYYY-MM-DD 형식 폴더 중 report.html을 가진 것만 최신순으로 반환."""
    if not site_dir.exists():
        return []

    reports: list[tuple[datetime, Path]] = []
    for entry in site_dir.iterdir():
        if not entry.is_dir() or not DATE_RE.match(entry.name):
            continue
        if not (entry / "report.html").exists():
            continue
        try:
            dt = datetime.strptime(entry.name, "%Y-%m-%d")
        except ValueError:
            continue
        reports.append((dt, entry))

    reports.sort(key=lambda item: item[0], reverse=True)
    return [path for _, path in reports]


def prune(reports: list[Path], keep: int) -> tuple[list[Path], list[Path]]:
    """최신 keep개만 남기고 나머지 삭제. (유지, 삭제) 경로 반환."""
    kept = reports[:keep]
    removed = reports[keep:]
    for path in removed:
        shutil.rmtree(path, ignore_errors=True)
    return kept, removed


def render_index(kept: list[Path], generated_at: datetime) -> str:
    """인덱스 HTML 렌더링."""
    if kept:
        latest = kept[0].name
        cards = "\n".join(
            f"""        <li class="report-card">
            <a href="./{escape(path.name)}/report.html">
                <span class="date">{escape(path.name)}</span>
                <span class="arrow">&rarr;</span>
            </a>
        </li>"""
            for path in kept
        )
        latest_link = (
            f'<a class="latest-link" href="./{escape(latest)}/report.html">'
            f"최신 리포트 바로 열기 ({escape(latest)})</a>"
        )
    else:
        cards = '        <li class="empty">아직 생성된 리포트가 없습니다.</li>'
        latest_link = ""

    timestamp = generated_at.strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>드림팀 주간 스크리닝 리포트</title>
    <style>
        :root {{
            --bg: #0b0d10;
            --panel: #14181d;
            --text: #e8ecf1;
            --muted: #8a94a4;
            --accent: #4ea8ff;
            --border: rgba(255, 255, 255, 0.08);
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 48px 24px;
            font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 720px; margin: 0 auto; }}
        h1 {{ margin: 0 0 8px; font-size: 28px; font-weight: 700; }}
        .subtitle {{ color: var(--muted); margin: 0 0 32px; font-size: 14px; }}
        .latest-link {{
            display: inline-block;
            margin-bottom: 32px;
            padding: 12px 20px;
            background: var(--accent);
            color: #0b0d10;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }}
        .latest-link:hover {{ opacity: 0.9; }}
        .section-title {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
            margin: 0 0 12px;
        }}
        ul.reports {{ list-style: none; padding: 0; margin: 0; }}
        .report-card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            margin-bottom: 10px;
            transition: border-color 0.15s;
        }}
        .report-card:hover {{ border-color: var(--accent); }}
        .report-card a {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            color: var(--text);
            text-decoration: none;
            font-family: 'SF Mono', Menlo, monospace;
        }}
        .report-card .date {{ font-size: 16px; }}
        .report-card .arrow {{ color: var(--muted); }}
        .empty {{
            padding: 24px;
            background: var(--panel);
            border: 1px dashed var(--border);
            border-radius: 10px;
            text-align: center;
            color: var(--muted);
        }}
        footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 12px;
        }}
        footer a {{ color: var(--muted); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>드림팀 주간 스크리닝 리포트</h1>
        <p class="subtitle">박문환 사프슈터 드림팀 지표 기반 한국 주식 스크리너 &middot; 매주 금요일 자동 실행</p>

        {latest_link}

        <p class="section-title">최근 리포트 (최대 4주)</p>
        <ul class="reports">
{cards}
        </ul>

        <footer>
            생성 시각: {escape(timestamp)} &middot;
            <a href="https://github.com/Knext/StockHunter">소스 저장소</a>
        </footer>
    </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="리포트 인덱스 생성 및 보존 정리")
    parser.add_argument(
        "--site-dir",
        type=Path,
        required=True,
        help="gh-pages 배포 디렉토리 (YYYY-MM-DD 폴더들이 위치)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=4,
        help="유지할 최신 리포트 개수 (기본 4)",
    )
    args = parser.parse_args()

    site_dir: Path = args.site_dir
    site_dir.mkdir(parents=True, exist_ok=True)

    reports = discover_reports(site_dir)
    kept, removed = prune(reports, args.keep)

    for path in removed:
        print(f"[prune] removed {path.name}", file=sys.stderr)
    for path in kept:
        print(f"[keep]  {path.name}", file=sys.stderr)

    index_html = render_index(kept, datetime.now(timezone.utc))
    (site_dir / "index.html").write_text(index_html, encoding="utf-8")
    print(f"[index] wrote {site_dir / 'index.html'}", file=sys.stderr)

    # .nojekyll을 두어 _로 시작하는 파일/폴더가 무시되지 않도록 보장
    (site_dir / ".nojekyll").touch()

    return 0


if __name__ == "__main__":
    sys.exit(main())
