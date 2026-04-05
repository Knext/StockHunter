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
    """

    cache_dir: Path
    cache_ttl_hours: int
    rate_limit_seconds: float


def load_config() -> Config:
    """환경변수에서 설정을 로드합니다."""
    return Config(
        cache_dir=Path(os.environ.get("CACHE_DIR", ".cache")),
        cache_ttl_hours=int(os.environ.get("CACHE_TTL_HOURS", "24")),
        rate_limit_seconds=float(os.environ.get("RATE_LIMIT_SECONDS", "0.5")),
    )
