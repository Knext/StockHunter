from dataclasses import dataclass
from datetime import date

from src.types.stock import StockInfo


@dataclass(frozen=True)
class DreamTeamSignal:
    """드림팀 복합 매수 신호 결과.

    Attributes:
        stock_info: 종목 정보
        date: 신호 발생일
        dmi_signal: DMI 매수 신호 여부
        stochastic_signal: 스토캐스틱 매수 강화 여부
        chaikin_signal: 채킨 오실레이터 매수 신호 여부
        macd_signal: MACD 오실레이터 매수 신호 여부
        demark_signal: 드마크 신호 여부 (setup 또는 countdown 완성)
        signal_strength: 충족된 지표 수 (0-5)
        signal_grade: 신호 등급
    """

    stock_info: StockInfo
    date: date
    dmi_signal: bool
    stochastic_signal: bool
    chaikin_signal: bool
    macd_signal: bool
    demark_signal: bool
    signal_strength: int
    signal_grade: str
