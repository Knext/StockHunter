"""배치 스크리닝 CLI 엔트리포인트.

사용법:
    python -m src.batch

환경변수:
    MARKET: 대상 시장 (기본 "ALL")
    BATCH_SIZE: 배치당 종목 수 (기본 50)
    MAX_CONCURRENT: 최대 동시 배치 수 (기본 3)
"""

import asyncio
import logging
import os

from src.batch.runner import run_full_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    """배치 스크리닝 파이프라인을 실행합니다."""
    market = os.environ.get("MARKET", "ALL")
    batch_size = int(os.environ.get("BATCH_SIZE", "50"))
    max_concurrent = int(os.environ.get("MAX_CONCURRENT", "3"))

    output_path = asyncio.run(
        run_full_pipeline(
            market=market,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
        )
    )

    logging.getLogger(__name__).info("출력 경로: %s", output_path.resolve())


main()
