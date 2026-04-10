import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """애플리케이션 설정.

    환경변수에서 읽어오며, 기본값을 제공합니다.

    Attributes:
        cache_dir: 캐시 디렉토리 경로
        cache_ttl_hours: 캐시 TTL (시간 단위)
        rate_limit_seconds: API 호출 간 대기 시간 (초)
        cache_max_history_days: stock_data 캐시 파일당 보존할 최대 과거 일수.
            캐시 무한 누적을 방지한다. MACD 주봉(34주)을 위해 최소 400일 권장.
    """

    cache_dir: Path
    cache_ttl_hours: int
    rate_limit_seconds: float
    cache_max_history_days: int = 400


def load_config() -> Config:
    """환경변수에서 설정을 로드합니다."""
    return Config(
        cache_dir=Path(os.environ.get("CACHE_DIR", ".cache")),
        cache_ttl_hours=int(os.environ.get("CACHE_TTL_HOURS", "24")),
        rate_limit_seconds=float(os.environ.get("RATE_LIMIT_SECONDS", "0.5")),
        cache_max_history_days=int(os.environ.get("CACHE_MAX_HISTORY_DAYS", "400")),
    )
