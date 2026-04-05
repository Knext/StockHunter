"""FastAPI 앱 생성 모듈."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routes import router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성합니다."""
    app = FastAPI(
        title="StockHunter API",
        description="박문환 드림팀 지표 기반 종목 스크리너 API",
        version="0.1.0",
    )

    app.include_router(router)

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("처리되지 않은 오류: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "서버 내부 오류가 발생했습니다",
            },
        )

    return app
