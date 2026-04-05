"""배치 스크리닝 결과 타입 정의."""

from dataclasses import dataclass

from src.screener.types import DreamTeamSignal
from src.types.ohlcv import StockData


@dataclass(frozen=True)
class BatchResult:
    """배치 스크리닝 실행 결과.

    Attributes:
        signals: 스크리닝 통과 종목 (signal_strength 내림차순)
        stock_data_map: 종목코드 → StockData 매핑 (차트 생성용)
        total_stocks: 전체 대상 종목 수
        success_count: 데이터 수집 성공 종목 수
        failed_codes: 데이터 수집 실패 종목 코드
        started_at: 배치 시작 시간 (ISO 형식)
        finished_at: 배치 종료 시간 (ISO 형식)
        market: 대상 시장 ("KOSPI", "KOSDAQ", "ALL")
    """

    signals: tuple[DreamTeamSignal, ...]
    stock_data_map: dict[str, StockData]
    index_data: dict[str, StockData]
    total_stocks: int
    success_count: int
    failed_codes: tuple[str, ...]
    started_at: str
    finished_at: str
    market: str
