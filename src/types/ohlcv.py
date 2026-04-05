from dataclasses import dataclass
from datetime import date

from src.types.stock import StockInfo


@dataclass(frozen=True)
class OHLCV:
    """일봉/주봉 OHLCV 데이터.

    Attributes:
        date: 거래일
        open: 시가 (None이면 데이터 없음)
        high: 고가 (None이면 데이터 없음)
        low: 저가 (None이면 데이터 없음)
        close: 종가 (None이면 데이터 없음)
        volume: 거래량 (None이면 데이터 없음)
    """

    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None


@dataclass(frozen=True)
class StockData:
    """종목의 전체 OHLCV 데이터 (일봉 + 주봉).

    Attributes:
        info: 종목 정보
        daily: 일봉 데이터 목록
        weekly: 주봉 데이터 목록
    """

    info: StockInfo
    daily: tuple[OHLCV, ...]
    weekly: tuple[OHLCV, ...]
