"""KRX(한국거래소) OHLCV 데이터 수집 모듈.

pykrx 라이브러리를 사용하여 OHLCV 데이터를 수집하고,
FinanceDataReader를 사용하여 종목 목록을 조회합니다.
레이트 리미팅을 적용하여 API 호출 간격을 조절합니다.
"""

import logging
import time
from datetime import date, timedelta

import FinanceDataReader as fdr
import pandas as pd
from pykrx import stock

from src.config import Config, load_config
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo

logger = logging.getLogger(__name__)


def _format_date(d: date) -> str:
    """date 객체를 pykrx 형식 문자열로 변환합니다."""
    return d.strftime("%Y%m%d")


def _rate_limit(seconds: float) -> None:
    """API 호출 간 대기합니다."""
    time.sleep(seconds)


def _parse_ohlcv_row(row_date: date, row: pd.Series) -> OHLCV:
    """pandas Series를 OHLCV 데이터클래스로 변환합니다.

    0 값은 데이터 없음으로 간주하여 None으로 변환합니다.
    """
    open_val = float(row["시가"]) if row["시가"] != 0 else None
    high_val = float(row["고가"]) if row["고가"] != 0 else None
    low_val = float(row["저가"]) if row["저가"] != 0 else None
    close_val = float(row["종가"]) if row["종가"] != 0 else None
    volume_val = int(row["거래량"]) if row["거래량"] != 0 else None

    return OHLCV(
        date=row_date,
        open=open_val,
        high=high_val,
        low=low_val,
        close=close_val,
        volume=volume_val,
    )


def _daily_to_weekly(daily_data: tuple[OHLCV, ...]) -> tuple[OHLCV, ...]:
    """일봉 데이터를 주봉으로 변환합니다.

    월~금 기준으로 그룹핑하여 주봉을 생성합니다.
    - 시가: 해당 주 첫 거래일의 시가
    - 고가: 해당 주 최고가
    - 저가: 해당 주 최저가
    - 종가: 해당 주 마지막 거래일의 종가
    - 거래량: 해당 주 거래량 합계
    """
    if not daily_data:
        return ()

    weeks: dict[str, list[OHLCV]] = {}
    for candle in daily_data:
        iso_year, iso_week, _ = candle.date.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        weeks.setdefault(week_key, []).append(candle)

    weekly_candles: list[OHLCV] = []
    for week_key in sorted(weeks.keys()):
        week_days = sorted(weeks[week_key], key=lambda c: c.date)

        highs = [c.high for c in week_days if c.high is not None]
        lows = [c.low for c in week_days if c.low is not None]
        volumes = [c.volume for c in week_days if c.volume is not None]

        weekly_candles.append(
            OHLCV(
                date=week_days[-1].date,
                open=week_days[0].open,
                high=max(highs) if highs else None,
                low=min(lows) if lows else None,
                close=week_days[-1].close,
                volume=sum(volumes) if volumes else None,
            )
        )

    return tuple(weekly_candles)


def get_all_stocks(
    market: str = "ALL",
    config: Config | None = None,
) -> list[StockInfo]:
    """전 종목 목록을 조회합니다.

    FinanceDataReader를 사용하여 종목 목록을 가져옵니다.

    Args:
        market: "KOSPI", "KOSDAQ", 또는 "ALL"
        config: 설정 객체 (None이면 기본값 로드)

    Returns:
        StockInfo 목록
    """
    markets = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]
    result: list[StockInfo] = []

    for mkt in markets:
        logger.info("종목 목록 조회: %s", mkt)
        try:
            df = fdr.StockListing(mkt)
        except Exception:
            logger.error("종목 목록 조회 실패: %s", mkt)
            continue

        for _, row in df.iterrows():
            code = str(row.get("Code", "")).strip()
            name = str(row.get("Name", "")).strip()
            if not code or not name:
                continue

            result.append(
                StockInfo(
                    code=code,
                    name=name,
                    market=mkt,
                    sector=str(row.get("Dept", "")),
                )
            )

    logger.info("총 %d개 종목 조회 완료", len(result))
    return result


def get_daily_ohlcv(
    code: str,
    start: str,
    end: str,
    config: Config | None = None,
) -> tuple[OHLCV, ...]:
    """일봉 OHLCV 데이터를 조회합니다.

    Args:
        code: 6자리 종목코드
        start: 시작일 (YYYYMMDD)
        end: 종료일 (YYYYMMDD)
        config: 설정 객체

    Returns:
        OHLCV 튜플 (날짜 오름차순)
    """
    cfg = config or load_config()
    logger.info("일봉 조회: %s (%s ~ %s)", code, start, end)

    df = stock.get_market_ohlcv_by_date(start, end, code)
    _rate_limit(cfg.rate_limit_seconds)

    if df.empty:
        logger.warning("일봉 데이터 없음: %s", code)
        return ()

    candles: list[OHLCV] = []
    for idx, row in df.iterrows():
        row_date = idx.date() if hasattr(idx, "date") else idx
        candles.append(_parse_ohlcv_row(row_date, row))

    return tuple(candles)


def get_weekly_ohlcv(
    code: str,
    start: str,
    end: str,
    config: Config | None = None,
) -> tuple[OHLCV, ...]:
    """주봉 OHLCV 데이터를 조회합니다.

    일봉 데이터를 조회한 후 주봉으로 변환합니다.

    Args:
        code: 6자리 종목코드
        start: 시작일 (YYYYMMDD)
        end: 종료일 (YYYYMMDD)
        config: 설정 객체

    Returns:
        OHLCV 튜플 (주 단위, 날짜 오름차순)
    """
    daily = get_daily_ohlcv(code, start, end, config)
    weekly = _daily_to_weekly(daily)
    logger.info("주봉 변환 완료: %s (%d일봉 -> %d주봉)", code, len(daily), len(weekly))
    return weekly


def get_stock_data(
    code: str,
    days: int = 200,
    config: Config | None = None,
) -> StockData:
    """종목의 전체 데이터 (정보 + 일봉 + 주봉)를 조회합니다.

    Args:
        code: 6자리 종목코드
        days: 조회할 과거 일수 (기본 200일)
        config: 설정 객체

    Returns:
        StockData (종목정보 + 일봉 + 주봉)
    """
    cfg = config or load_config()

    end = date.today()
    start = end - timedelta(days=days)
    start_str = _format_date(start)
    end_str = _format_date(end)

    name = stock.get_market_ticker_name(code)
    _rate_limit(cfg.rate_limit_seconds)

    info = StockInfo(code=code, name=name, market="", sector="")

    daily = get_daily_ohlcv(code, start_str, end_str, cfg)
    weekly = _daily_to_weekly(daily)

    logger.info(
        "종목 데이터 조회 완료: %s %s (일봉 %d, 주봉 %d)",
        code,
        name,
        len(daily),
        len(weekly),
    )

    return StockData(info=info, daily=daily, weekly=weekly)
