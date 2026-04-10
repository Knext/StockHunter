"""배치 스크리닝 파이프라인.

asyncio 기반으로 전 종목을 배치 단위로 스크리닝합니다.
동시 배치 수를 제한하고, 개별 종목 실패 시 스킵합니다.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from src.batch.types import BatchResult
from src.config import load_config
from src.data.cache import CachedDataFetcher
from src.data.krx import INDEX_CODES, get_all_stocks, get_index_data
from src.screener.dream_config import DreamIndexConfig, load_dream_index_config
from src.screener.engine import screen_stock
from src.screener.types import DreamTeamSignal
from src.types.ohlcv import StockData
from src.types.stock import StockInfo

logger = logging.getLogger(__name__)


def _get_batch_size() -> int:
    """환경변수에서 배치 크기를 읽습니다."""
    return int(os.environ.get("BATCH_SIZE", "50"))


def _get_max_concurrent() -> int:
    """환경변수에서 최대 동시 배치 수를 읽습니다."""
    return int(os.environ.get("MAX_CONCURRENT", "3"))


def _split_into_batches(
    items: list[StockInfo],
    batch_size: int,
) -> list[list[StockInfo]]:
    """종목 리스트를 batch_size 단위로 분할합니다."""
    return [
        items[i : i + batch_size]
        for i in range(0, len(items), batch_size)
    ]


async def _process_batch(
    batch: list[StockInfo],
    fetcher: CachedDataFetcher,
    days: int,
    batch_index: int,
    total_batches: int,
    dream_config: DreamIndexConfig,
) -> tuple[list[DreamTeamSignal], dict[str, StockData], list[str]]:
    """단일 배치를 순차 처리합니다.

    각 종목에 대해 데이터 수집 → 스크리닝을 수행합니다.
    동기 IO는 run_in_executor로 래핑합니다.

    Returns:
        (시그널 리스트, 종목데이터 맵, 실패 코드 리스트)
    """
    loop = asyncio.get_running_loop()
    signals: list[DreamTeamSignal] = []
    stock_data_map: dict[str, StockData] = {}
    failed_codes: list[str] = []

    logger.info(
        "배치 %d/%d 시작 (%d종목)",
        batch_index + 1,
        total_batches,
        len(batch),
    )

    for stock_info in batch:
        try:
            stock_data = await loop.run_in_executor(
                None,
                fetcher.get_stock_data,
                stock_info.code,
                days,
            )
            stock_data_map[stock_info.code] = stock_data

            signal = await loop.run_in_executor(
                None,
                screen_stock,
                stock_data,
                dream_config,
            )
            if signal is not None:
                signals.append(signal)
        except Exception:
            logger.warning("종목 처리 실패: %s (%s)", stock_info.code, stock_info.name)
            failed_codes.append(stock_info.code)

    logger.info(
        "배치 %d/%d 완료 (시그널 %d개, 실패 %d개)",
        batch_index + 1,
        total_batches,
        len(signals),
        len(failed_codes),
    )

    return signals, stock_data_map, failed_codes


async def run_batch(
    market: str = "ALL",
    batch_size: int = 50,
    max_concurrent: int = 3,
    days: int = 365,
    dream_config: DreamIndexConfig | None = None,
) -> BatchResult:
    """전 종목 배치 스크리닝을 실행합니다.

    MACD(주봉)에 최소 34주(~240영업일) 데이터가 필요하므로
    기본값은 365일입니다.

    Args:
        market: 대상 시장 ("KOSPI", "KOSDAQ", "ALL")
        batch_size: 배치당 종목 수
        max_concurrent: 최대 동시 배치 수
        days: 조회할 과거 일수
        dream_config: 드림팀 지표 설정. None이면 YAML에서 로드한다.

    Returns:
        BatchResult (signals는 signal_strength 내림차순 정렬)
    """
    started_at = datetime.now().isoformat()

    config = load_config()
    if dream_config is None:
        dream_config = load_dream_index_config()
        logger.info(
            "드림팀 설정 로드 완료 (min_strength=%d)",
            dream_config.report.min_strength,
        )
    fetcher = CachedDataFetcher(config)

    loop = asyncio.get_running_loop()
    all_stocks = await loop.run_in_executor(
        None,
        get_all_stocks,
        market,
        config,
    )

    total_stocks = len(all_stocks)
    logger.info("전체 종목 수: %d (시장: %s)", total_stocks, market)

    if total_stocks == 0:
        return BatchResult(
            signals=(),
            stock_data_map={},
            index_data={},
            total_stocks=0,
            success_count=0,
            failed_codes=(),
            started_at=started_at,
            finished_at=datetime.now().isoformat(),
            market=market,
        )

    batches = _split_into_batches(all_stocks, batch_size)
    total_batches = len(batches)
    logger.info("배치 수: %d (배치 크기: %d, 동시 실행: %d)", total_batches, batch_size, max_concurrent)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _run_with_semaphore(
        batch: list[StockInfo],
        batch_index: int,
    ) -> tuple[list[DreamTeamSignal], dict[str, StockData], list[str]]:
        async with semaphore:
            return await _process_batch(
                batch, fetcher, days, batch_index, total_batches, dream_config,
            )

    tasks = [
        _run_with_semaphore(batch, i)
        for i, batch in enumerate(batches)
    ]
    results = await asyncio.gather(*tasks)

    all_signals: list[DreamTeamSignal] = []
    all_stock_data: dict[str, StockData] = {}
    all_failed: list[str] = []

    for batch_signals, batch_data, batch_failed in results:
        all_signals.extend(batch_signals)
        all_stock_data.update(batch_data)
        all_failed.extend(batch_failed)

    sorted_signals = sorted(
        all_signals,
        key=lambda s: s.signal_strength,
        reverse=True,
    )

    success_count = total_stocks - len(all_failed)
    finished_at = datetime.now().isoformat()

    index_data: dict[str, StockData] = {}
    for idx_code in INDEX_CODES:
        try:
            idx_sd = await loop.run_in_executor(
                None, get_index_data, idx_code, days, config,
            )
            index_data[idx_code] = idx_sd
            logger.info("지수 수집 완료: %s (%d일봉)", idx_code, len(idx_sd.daily))
        except Exception:
            logger.warning("지수 수집 실패: %s", idx_code)

    logger.info(
        "배치 스크리닝 완료: 전체 %d / 성공 %d / 실패 %d / 시그널 %d",
        total_stocks,
        success_count,
        len(all_failed),
        len(sorted_signals),
    )

    return BatchResult(
        signals=tuple(sorted_signals),
        stock_data_map=all_stock_data,
        index_data=index_data,
        total_stocks=total_stocks,
        success_count=success_count,
        failed_codes=tuple(all_failed),
        started_at=started_at,
        finished_at=finished_at,
        market=market,
    )


async def run_full_pipeline(
    market: str = "ALL",
    batch_size: int = 50,
    max_concurrent: int = 3,
    dream_config: DreamIndexConfig | None = None,
) -> Path:
    """배치 스크리닝 전체 파이프라인을 실행합니다.

    1. run_batch()로 전 종목 스크리닝
    2. 시그널 종목 차트 생성
    3. HTML 보고서 생성

    Args:
        market: 대상 시장
        batch_size: 배치당 종목 수
        max_concurrent: 최대 동시 배치 수
        dream_config: 드림팀 지표 설정. None이면 YAML에서 로드한다.

    Returns:
        생성된 보고서 파일 경로
    """
    from src.report.generator import generate_report
    from src.report.types import ReportConfig
    from src.visualization.chart import generate_all_charts, generate_index_chart

    if dream_config is None:
        dream_config = load_dream_index_config()

    result = await run_batch(
        market=market,
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        dream_config=dream_config,
    )

    logger.info(
        "파이프라인 결과: 시장=%s, 시그널=%d개, 성공=%d/%d, 실패=%d",
        result.market,
        len(result.signals),
        result.success_count,
        result.total_stocks,
        len(result.failed_codes),
    )

    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path("reports") / today
    chart_dir = report_dir / "charts"

    chart_paths: dict[str, Path] = {}
    if result.signals:
        logger.info("차트 생성 시작: %d종목", len(result.signals))
        chart_paths = generate_all_charts(
            result.signals,
            result.stock_data_map,
            chart_dir,
        )
        logger.info("차트 생성 완료: %d/%d", len(chart_paths), len(result.signals))

    index_chart_paths: dict[str, Path] = {}
    for idx_code, idx_sd in result.index_data.items():
        try:
            path = generate_index_chart(idx_sd, chart_dir)
            index_chart_paths[idx_code] = path
        except Exception:
            logger.warning("지수 차트 생성 실패: %s", idx_code)

    report_config = ReportConfig(
        output_dir=Path("reports"),
        min_strength=dream_config.report.min_strength,
    )
    report_path = generate_report(result, chart_paths, index_chart_paths, report_config)

    logger.info("파이프라인 완료: %s", report_path.resolve())
    return report_path
