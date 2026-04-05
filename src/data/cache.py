"""JSON 파일 기반 캐싱 모듈 (증분 업데이트 지원).

KRX 데이터 수집 결과를 로컬 파일 시스템에 캐시합니다.
캐시에 저장된 마지막 날짜 이후 데이터만 추가 조회하여 병합합니다.
"""

import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import Config, load_config
from src.data import krx
from src.types.ohlcv import OHLCV, StockData
from src.types.stock import StockInfo

logger = logging.getLogger(__name__)


def _ohlcv_to_dict(candle: OHLCV) -> dict:
    """OHLCV를 직렬화 가능한 딕셔너리로 변환합니다."""
    return {
        "date": candle.date.isoformat(),
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
    }


def _dict_to_ohlcv(data: dict) -> OHLCV:
    """딕셔너리를 OHLCV로 변환합니다."""
    return OHLCV(
        date=date.fromisoformat(data["date"]),
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        volume=data["volume"],
    )


def _stock_info_to_dict(info: StockInfo) -> dict:
    """StockInfo를 직렬화 가능한 딕셔너리로 변환합니다."""
    return {
        "code": info.code,
        "name": info.name,
        "market": info.market,
        "sector": info.sector,
    }


def _dict_to_stock_info(data: dict) -> StockInfo:
    """딕셔너리를 StockInfo로 변환합니다."""
    return StockInfo(
        code=data["code"],
        name=data["name"],
        market=data["market"],
        sector=data["sector"],
    )


def _stock_data_to_dict(stock_data: StockData) -> dict:
    """StockData를 직렬화 가능한 딕셔너리로 변환합니다."""
    return {
        "info": _stock_info_to_dict(stock_data.info),
        "daily": [_ohlcv_to_dict(c) for c in stock_data.daily],
        "weekly": [_ohlcv_to_dict(c) for c in stock_data.weekly],
    }


def _dict_to_stock_data(data: dict) -> StockData:
    """딕셔너리를 StockData로 변환합니다."""
    return StockData(
        info=_dict_to_stock_info(data["info"]),
        daily=tuple(_dict_to_ohlcv(c) for c in data["daily"]),
        weekly=tuple(_dict_to_ohlcv(c) for c in data["weekly"]),
    )


def _make_cache_key(prefix: str, *args: str) -> str:
    """캐시 키를 생성합니다."""
    raw = f"{prefix}:{'|'.join(args)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _merge_daily(
    existing: tuple[OHLCV, ...],
    new_data: tuple[OHLCV, ...],
) -> tuple[OHLCV, ...]:
    """기존 일봉에 신규 일봉을 병합합니다.

    날짜 기준으로 중복을 제거하고 오름차순 정렬합니다.
    """
    by_date: dict[date, OHLCV] = {}
    for candle in existing:
        by_date[candle.date] = candle
    for candle in new_data:
        by_date[candle.date] = candle
    return tuple(sorted(by_date.values(), key=lambda c: c.date))


class CachedDataFetcher:
    """캐시 기능이 있는 KRX 데이터 수집기 (증분 업데이트).

    캐시에 저장된 마지막 날짜 이후 데이터만 API로 조회하여 병합합니다.
    전체 재조회를 최소화하여 API 호출을 줄입니다.

    Attributes:
        config: 애플리케이션 설정
        cache_dir: 캐시 디렉토리 경로
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, cache_key: str) -> Path:
        """캐시 파일 경로를 반환합니다."""
        return self.cache_dir / f"{cache_key}.json"

    def _read_cache_raw(self, cache_path: Path) -> dict | None:
        """캐시 파일에서 원본 데이터를 읽습니다 (TTL 무시)."""
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("손상된 캐시 파일 삭제: %s", cache_path)
            cache_path.unlink(missing_ok=True)
            return None

    def _is_cache_fresh(self, cached: dict) -> bool:
        """캐시가 TTL 내인지 확인합니다."""
        try:
            cached_at = datetime.fromisoformat(cached["cached_at"])
            ttl = timedelta(hours=self.config.cache_ttl_hours)
            return datetime.now() - cached_at < ttl
        except (KeyError, ValueError):
            return False

    def _write_cache(self, cache_path: Path, data: dict) -> None:
        """데이터를 캐시 파일에 저장합니다."""
        payload = {
            "cached_at": datetime.now().isoformat(),
            "data": data,
        }
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.debug("캐시 저장: %s", cache_path.name)
        except OSError as e:
            logger.error("캐시 저장 실패: %s - %s", cache_path, e)

    def get_stock_data(self, code: str, days: int = 365) -> StockData:
        """종목 데이터를 증분 업데이트 방식으로 조회합니다.

        1. 캐시에 데이터가 있으면 마지막 날짜를 확인
        2. 마지막 날짜 다음 날 ~ 오늘까지만 API 조회
        3. 기존 데이터에 병합하여 캐시 갱신
        4. 요청 기간(days)에 맞게 트리밍

        Args:
            code: 6자리 종목코드
            days: 조회할 과거 일수

        Returns:
            StockData
        """
        cache_key = _make_cache_key("stock_data_v2", code)
        cache_path = self._cache_path(cache_key)

        today = date.today()
        desired_start = today - timedelta(days=days)

        cached_raw = self._read_cache_raw(cache_path)
        cached_daily: tuple[OHLCV, ...] = ()
        cached_info: StockInfo | None = None

        if cached_raw is not None and "data" in cached_raw:
            try:
                cached_stock = _dict_to_stock_data(cached_raw["data"])
                cached_daily = cached_stock.daily
                cached_info = cached_stock.info
            except (KeyError, TypeError, ValueError):
                logger.warning("캐시 데이터 파싱 실패: %s", code)

        if cached_daily:
            last_cached_date = cached_daily[-1].date
            if last_cached_date >= today:
                logger.info("캐시 최신: %s (마지막: %s)", code, last_cached_date)
                trimmed = _trim_daily(cached_daily, desired_start)
                weekly = krx._daily_to_weekly(trimmed)
                return StockData(
                    info=cached_info or StockInfo(code=code, name="", market="", sector=""),
                    daily=trimmed,
                    weekly=weekly,
                )

            fetch_start = last_cached_date + timedelta(days=1)
            fetch_start_str = krx._format_date(fetch_start)
            fetch_end_str = krx._format_date(today)

            logger.info(
                "증분 조회: %s (%s ~ %s, 캐시 %d일 보유)",
                code, fetch_start_str, fetch_end_str, len(cached_daily),
            )

            info = cached_info or StockInfo(code=code, name="", market="", sector="")
            try:
                new_daily = krx.get_daily_ohlcv(code, fetch_start_str, fetch_end_str, self.config)
            except Exception:
                logger.warning("증분 조회 실패, 캐시 사용: %s", code)
                trimmed = _trim_daily(cached_daily, desired_start)
                weekly = krx._daily_to_weekly(trimmed)
                return StockData(info=info, daily=trimmed, weekly=weekly)

            if new_daily:
                try:
                    name = krx.stock.get_market_ticker_name(code)
                    krx._rate_limit(self.config.rate_limit_seconds)
                    info = StockInfo(code=code, name=name, market=info.market, sector=info.sector)
                except Exception:
                    pass

            merged = _merge_daily(cached_daily, new_daily)
            trimmed = _trim_daily(merged, desired_start)
            weekly = krx._daily_to_weekly(trimmed)

            result = StockData(info=info, daily=trimmed, weekly=weekly)
            self._write_cache(cache_path, _stock_data_to_dict(
                StockData(info=info, daily=merged, weekly=krx._daily_to_weekly(merged))
            ))

            logger.info(
                "증분 완료: %s (기존 %d + 신규 %d = 총 %d일)",
                code, len(cached_daily), len(new_daily), len(merged),
            )
            return result

        logger.info("캐시 미스, 전체 조회: %s", code)
        stock_data = krx.get_stock_data(code, days, self.config)
        self._write_cache(cache_path, _stock_data_to_dict(stock_data))
        return stock_data

    def get_daily_ohlcv(
        self, code: str, start: str, end: str
    ) -> tuple[OHLCV, ...]:
        """일봉 데이터를 캐시에서 조회하거나 새로 수집합니다."""
        cache_key = _make_cache_key("daily", code, start, end)
        cache_path = self._cache_path(cache_key)

        cached_raw = self._read_cache_raw(cache_path)
        if cached_raw is not None and self._is_cache_fresh(cached_raw):
            logger.debug("캐시 히트: %s", cache_path.name)
            return tuple(_dict_to_ohlcv(c) for c in cached_raw["data"])

        daily = krx.get_daily_ohlcv(code, start, end, self.config)
        self._write_cache(cache_path, [_ohlcv_to_dict(c) for c in daily])
        return daily

    def get_weekly_ohlcv(
        self, code: str, start: str, end: str
    ) -> tuple[OHLCV, ...]:
        """주봉 데이터를 캐시에서 조회하거나 새로 수집합니다."""
        cache_key = _make_cache_key("weekly", code, start, end)
        cache_path = self._cache_path(cache_key)

        cached_raw = self._read_cache_raw(cache_path)
        if cached_raw is not None and self._is_cache_fresh(cached_raw):
            logger.debug("캐시 히트: %s", cache_path.name)
            return tuple(_dict_to_ohlcv(c) for c in cached_raw["data"])

        weekly = krx.get_weekly_ohlcv(code, start, end, self.config)
        self._write_cache(cache_path, [_ohlcv_to_dict(c) for c in weekly])
        return weekly

    def clear_cache(self) -> int:
        """모든 캐시 파일을 삭제합니다.

        Returns:
            삭제된 파일 수
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        logger.info("캐시 %d개 파일 삭제", count)
        return count


def _trim_daily(
    daily: tuple[OHLCV, ...],
    start_date: date,
) -> tuple[OHLCV, ...]:
    """시작일 이후 데이터만 남깁니다."""
    return tuple(c for c in daily if c.date >= start_date)
