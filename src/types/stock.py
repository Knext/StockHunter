from dataclasses import dataclass


@dataclass(frozen=True)
class StockInfo:
    """KRX 종목 정보.

    Attributes:
        code: 6자리 종목코드 (예: "005930")
        name: 종목명 (예: "삼성전자")
        market: 시장 구분 ("KOSPI" | "KOSDAQ")
        sector: 업종 (예: "전기전자")
    """

    code: str
    name: str
    market: str
    sector: str
