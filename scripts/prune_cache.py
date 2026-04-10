#!/usr/bin/env python3
"""캐시 파일 단위 보존 정책 — cached_at 기준 오래된 파일 제거.

각 캐시 JSON의 `cached_at` 필드를 읽어 기준일 초과 파일을 삭제한다.
- 상장폐지/미조회 종목: 주간 배치에서 더 이상 쓰여지지 않아 오래된 cached_at이 유지 → 제거
- 실제 활동 중인 종목: 매주 갱신되어 cached_at이 최신 → 보존
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def parse_cached_at(path: Path) -> datetime | None:
    """캐시 파일에서 cached_at 타임스탬프를 파싱. 실패 시 None."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    raw = payload.get("cached_at") if isinstance(payload, dict) else None
    if not isinstance(raw, str):
        return None

    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def prune(cache_dir: Path, max_age_days: int) -> tuple[int, int, int]:
    """(검사, 유지, 삭제) 카운트 반환."""
    if not cache_dir.exists():
        return (0, 0, 0)

    cutoff = datetime.now() - timedelta(days=max_age_days)
    checked = 0
    kept = 0
    removed = 0

    for path in sorted(cache_dir.glob("*.json")):
        checked += 1
        cached_at = parse_cached_at(path)
        # 타임스탬프 없는 파일은 보수적으로 유지
        if cached_at is None:
            kept += 1
            continue
        if cached_at < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
        else:
            kept += 1

    return (checked, kept, removed)


def main() -> int:
    parser = argparse.ArgumentParser(description="cached_at 기준 오래된 캐시 파일 제거")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache"),
        help="캐시 디렉토리 (기본 .cache)",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=180,
        help="cached_at가 이 일수보다 오래된 파일은 삭제 (기본 180일 = 약 6개월)",
    )
    args = parser.parse_args()

    checked, kept, removed = prune(args.cache_dir, args.max_age_days)
    print(
        f"[prune-cache] 검사={checked} 유지={kept} 삭제={removed} "
        f"(기준: cached_at < now - {args.max_age_days}일)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
