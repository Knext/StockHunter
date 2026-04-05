"""FastAPI 의존성 주입."""

import logging
from functools import lru_cache

from src.config import Config, load_config
from src.data.cache import CachedDataFetcher

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """애플리케이션 설정을 반환합니다."""
    return load_config()


@lru_cache(maxsize=1)
def get_fetcher() -> CachedDataFetcher:
    """캐시 기반 데이터 페처를 반환합니다."""
    config = get_config()
    return CachedDataFetcher(config)
