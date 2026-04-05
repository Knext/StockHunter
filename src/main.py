"""StockHunter API 메인 엔트리포인트."""

import logging
import os

import uvicorn

from src.api.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("src.main:app", host=host, port=port, reload=True)
