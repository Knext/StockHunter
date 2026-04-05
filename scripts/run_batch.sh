#!/bin/bash
# 드림팀 주간 배치 스크리닝 실행 스크립트
# 매주 금요일 12:00 PM KST에 launchd로 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Python 경로 (conda 환경)
PYTHON="/Users/sean/langchain/miniconda3/bin/python"

# 환경변수
export MARKET="ALL"
export BATCH_SIZE="50"
export MAX_CONCURRENT="3"

# 로그 디렉토리
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/batch_$(date +%Y-%m-%d_%H%M%S).log"

echo "=== 드림팀 배치 스크리닝 시작: $(date) ===" >> "$LOG_FILE"

$PYTHON -m src.batch >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "=== 배치 스크리닝 종료: $(date), exit=$EXIT_CODE ===" >> "$LOG_FILE"

exit $EXIT_CODE
