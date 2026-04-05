"""100개 종목 테스트 배치 스크리닝."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.batch.types import BatchResult
from src.config import load_config
from src.data.cache import CachedDataFetcher
from src.data.krx import get_all_stocks
from src.report.generator import generate_report
from src.report.types import ReportConfig
from src.screener.engine import screen_stock
from src.visualization.chart import generate_all_charts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_batch")


async def run_test():
    config = load_config()
    fetcher = CachedDataFetcher(config)

    logger.info("종목 목록 수집 중...")
    all_stocks = get_all_stocks("ALL", config)
    test_stocks = all_stocks[:100]
    logger.info(
        "테스트 대상: %d종목 (전체 %d종목 중)", len(test_stocks), len(all_stocks)
    )

    started_at = datetime.now().isoformat()
    signals = []
    stock_data_map = {}
    failed_codes = []

    loop = asyncio.get_running_loop()
    for i, stock_info in enumerate(test_stocks):
        if (i + 1) % 10 == 0:
            logger.info("진행: %d/%d", i + 1, len(test_stocks))
        try:
            stock_data = await loop.run_in_executor(
                None, fetcher.get_stock_data, stock_info.code, 365
            )
            stock_data_map[stock_info.code] = stock_data
            signal = screen_stock(stock_data)
            if signal is not None:
                signals.append(signal)
        except Exception as e:
            logger.warning("실패: %s - %s", stock_info.code, e)
            failed_codes.append(stock_info.code)

    signals.sort(key=lambda s: s.signal_strength, reverse=True)
    finished_at = datetime.now().isoformat()

    batch_result = BatchResult(
        signals=tuple(signals),
        stock_data_map=stock_data_map,
        total_stocks=len(test_stocks),
        success_count=len(test_stocks) - len(failed_codes),
        failed_codes=tuple(failed_codes),
        started_at=started_at,
        finished_at=finished_at,
        market="ALL",
    )

    logger.info(
        "스크리닝 완료: 시그널 %d개, 성공 %d, 실패 %d",
        len(signals),
        batch_result.success_count,
        len(failed_codes),
    )

    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path("reports") / today
    chart_dir = report_dir / "charts"

    chart_paths = {}
    if signals:
        logger.info("차트 생성 시작: %d종목", len(signals))
        chart_paths = generate_all_charts(tuple(signals), stock_data_map, chart_dir)
        logger.info("차트 생성 완료: %d/%d", len(chart_paths), len(signals))

    report_config = ReportConfig(output_dir=Path("reports"))
    report_path = generate_report(batch_result, chart_paths, report_config)
    logger.info("보고서 생성 완료: %s", report_path)

    return report_path, batch_result


def main():
    report_path, result = asyncio.run(run_test())
    print("\n========== 결과 ==========")
    print("보고서:", report_path.resolve())
    print("대상:", result.total_stocks, "종목")
    print("성공:", result.success_count)
    print("실패:", len(result.failed_codes))
    print("시그널:", len(result.signals), "종목")
    for s in result.signals:
        indicators = []
        if s.dmi_signal:
            indicators.append("DMI")
        if s.stochastic_signal:
            indicators.append("스토캐스틱")
        if s.chaikin_signal:
            indicators.append("채킨")
        if s.macd_signal:
            indicators.append("MACD")
        if s.demark_signal:
            indicators.append("드마크")
        ind_str = ", ".join(indicators)
        name = s.stock_info.name
        code = s.stock_info.code
        grade = s.signal_grade
        strength = s.signal_strength
        print(f"  {grade}({strength}) {name}({code}) - {ind_str}")


main()
