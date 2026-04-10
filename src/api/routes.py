"""API 라우트 정의."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import get_config, get_fetcher
from src.api.schemas import (
    ApiResponse,
    ChaikinIndicator,
    DMIIndicator,
    DeMarkIndicator,
    DreamTeamSummary,
    IndicatorConfigResponse,
    IndicatorsDetail,
    MACDIndicator,
    ScreenMeta,
    ScreenResult,
    StochasticIndicator,
    StockDetail,
    StockInfoSchema,
)
from src.api.schemas import ChaikinConfig as ChaikinConfigSchema
from src.api.schemas import DMIConfig as DMIConfigSchema
from src.api.schemas import DeMarkConfig as DeMarkConfigSchema
from src.api.schemas import MACDConfig as MACDConfigSchema
from src.api.schemas import ScreeningConfig as ScreeningConfigSchema
from src.api.schemas import StochasticConfig as StochasticConfigSchema
from src.config import Config
from src.data import krx
from src.data.cache import CachedDataFetcher
from src.indicators.chaikin import calculate_chaikin
from src.indicators.demark import calculate_demark
from src.indicators.dmi import calculate_dmi
from src.indicators.macd import calculate_macd_oscillator
from src.indicators.stochastic import calculate_stochastic
from src.screener.dream_config import load_dream_index_config
from src.screener.engine import screen_all, screen_stock
from src.types.ohlcv import StockData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/screen", response_model=ApiResponse[list[ScreenResult]])
def screen_stocks(
    fetcher: CachedDataFetcher = Depends(get_fetcher),
    config: Config = Depends(get_config),
    market: str = Query("ALL", pattern="^(KOSPI|KOSDAQ|ALL)$"),
    codes: str | None = Query(None),
    min_strength: int = Query(1, ge=1, le=4),
    days: int = Query(200, ge=1, le=1000),
) -> ApiResponse[list[ScreenResult]]:
    """드림팀 스크리닝을 실행합니다."""
    try:
        dream_config = load_dream_index_config()
        stock_data_list = _collect_stock_data(fetcher, config, market, codes, days)
        signals = screen_all(stock_data_list, config=dream_config)

        filtered = [s for s in signals if s.signal_strength >= min_strength]

        results = [
            ScreenResult(
                code=s.stock_info.code,
                name=s.stock_info.name,
                market=s.stock_info.market,
                date=s.date.isoformat(),
                dmi_signal=s.dmi_signal,
                stochastic_signal=s.stochastic_signal,
                chaikin_signal=s.chaikin_signal,
                macd_signal=s.macd_signal,
                demark_signal=s.demark_signal,
                signal_strength=s.signal_strength,
                signal_grade=s.signal_grade,
            )
            for s in filtered
        ]

        meta = ScreenMeta(
            total=len(results),
            screened_at=datetime.now().isoformat(timespec="seconds"),
            market=market,
        )

        return ApiResponse(
            success=True,
            data=results,
            meta=meta.model_dump(),
        )
    except Exception as e:
        logger.exception("스크리닝 실패: %s", e)
        raise HTTPException(
            status_code=500,
            detail="스크리닝 처리 중 오류가 발생했습니다",
        ) from e


def _collect_stock_data(
    fetcher: CachedDataFetcher,
    config: Config,
    market: str,
    codes: str | None,
    days: int,
) -> list[StockData]:
    """스크리닝 대상 종목의 데이터를 수집합니다."""
    stock_data_list: list[StockData] = []

    if codes:
        code_list = [c.strip() for c in codes.split(",") if c.strip()]
        for code in code_list:
            try:
                stock_data_list.append(fetcher.get_stock_data(code, days))
            except Exception as e:
                logger.warning("종목 %s 데이터 수집 실패: %s", code, e)
    else:
        try:
            all_stocks = krx.get_all_stocks(market, config)
        except Exception as e:
            logger.error("종목 목록 조회 실패: %s", e)
            return stock_data_list

        logger.info("전체 %d개 종목 데이터 수집 시작", len(all_stocks))
        for i, stock_info in enumerate(all_stocks):
            try:
                stock_data_list.append(
                    fetcher.get_stock_data(stock_info.code, days)
                )
            except Exception as e:
                logger.warning("종목 %s 데이터 수집 실패: %s", stock_info.code, e)
            if (i + 1) % 100 == 0:
                logger.info("진행: %d/%d", i + 1, len(all_stocks))

    return stock_data_list


@router.get("/stocks/{code}", response_model=ApiResponse[StockDetail])
def get_stock_detail(
    code: str,
    fetcher: CachedDataFetcher = Depends(get_fetcher),
    days: int = Query(200, ge=1, le=1000),
) -> ApiResponse[StockDetail]:
    """개별 종목의 상세 지표를 조회합니다."""
    try:
        stock_data = fetcher.get_stock_data(code, days)
    except Exception as e:
        logger.error("종목 데이터 조회 실패: %s - %s", code, e)
        raise HTTPException(
            status_code=404,
            detail="종목 데이터를 조회할 수 없습니다",
        ) from e

    daily = stock_data.daily
    weekly = stock_data.weekly

    dmi_results = calculate_dmi(daily)
    stoch_results = calculate_stochastic(daily)
    chaikin_results = calculate_chaikin(daily)
    macd_results = calculate_macd_oscillator(weekly)
    demark_results = calculate_demark(daily)

    dmi_latest = dmi_results[-1] if dmi_results else None
    stoch_latest = stoch_results[-1] if stoch_results else None
    chaikin_latest = chaikin_results[-1] if chaikin_results else None
    macd_latest = macd_results[-1] if macd_results else None
    demark_latest = demark_results[-1] if demark_results else None

    signal = screen_stock(stock_data, config=load_dream_index_config())

    detail = StockDetail(
        info=StockInfoSchema(
            code=stock_data.info.code,
            name=stock_data.info.name,
            market=stock_data.info.market,
            sector=stock_data.info.sector,
        ),
        indicators=IndicatorsDetail(
            dmi=DMIIndicator(
                plus_di=dmi_latest.plus_di if dmi_latest else None,
                minus_di=dmi_latest.minus_di if dmi_latest else None,
                adx=dmi_latest.adx if dmi_latest else None,
                buy_signal=dmi_latest.buy_signal if dmi_latest else False,
            ),
            stochastic=StochasticIndicator(
                k=stoch_latest.k if stoch_latest else None,
                d=stoch_latest.d if stoch_latest else None,
                buy_reinforcement=stoch_latest.buy_reinforcement if stoch_latest else False,
            ),
            chaikin=ChaikinIndicator(
                value=chaikin_latest.co_value if chaikin_latest else None,
                buy_signal=chaikin_latest.buy_signal if chaikin_latest else False,
            ),
            macd=MACDIndicator(
                macd=macd_latest.macd if macd_latest else None,
                signal=macd_latest.signal if macd_latest else None,
                oscillator=macd_latest.oscillator if macd_latest else None,
                buy_signal=macd_latest.buy_signal if macd_latest else False,
            ),
            demark=DeMarkIndicator(
                setup_count=demark_latest.setup_count if demark_latest else 0,
                countdown_count=demark_latest.countdown_count if demark_latest else 0,
                setup_complete=demark_latest.setup_complete if demark_latest else False,
            ),
        ),
        dream_team=DreamTeamSummary(
            signal_strength=signal.signal_strength if signal else 0,
            signal_grade=signal.signal_grade if signal else "",
        ),
    )

    return ApiResponse(success=True, data=detail)


@router.get("/indicators", response_model=ApiResponse[IndicatorConfigResponse])
def get_indicator_config() -> ApiResponse[IndicatorConfigResponse]:
    """현재 지표 설정값을 조회합니다 (dream-index-config.yaml 기반)."""
    dream_config = load_dream_index_config()
    response = IndicatorConfigResponse(
        dmi=DMIConfigSchema(period=dream_config.dmi.period),
        stochastic=StochasticConfigSchema(
            k_period=dream_config.stochastic.k,
            d_period=dream_config.stochastic.d,
            slowing=dream_config.stochastic.slowing,
        ),
        chaikin=ChaikinConfigSchema(
            fast_period=dream_config.chaikin.fast,
            slow_period=dream_config.chaikin.slow,
        ),
        macd=MACDConfigSchema(
            fast=dream_config.macd.fast,
            slow=dream_config.macd.slow,
            signal=dream_config.macd.signal,
        ),
        demark=DeMarkConfigSchema(lookback=dream_config.demark.lookback),
        screening=ScreeningConfigSchema(
            lookback_days=dream_config.dmi.lookback_days,
        ),
    )
    return ApiResponse(success=True, data=response)
