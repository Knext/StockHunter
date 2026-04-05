# StockHunter

박문환 드림팀 지표 기반 한국 주식 종목 스크리너.

KRX(한국거래소) 상장 종목을 대상으로 5개 기술적 지표를 종합 분석하여 매수 신호를 탐지합니다.

## 드림팀 지표

| 지표 | 개발자 | 역할 | 신호 조건 |
|------|--------|------|-----------|
| DMI | J. Welles Wilder | 저점 족집게 | -DI가 ADX를 30 이상에서 하향 돌파 + ADX 하락 전환 |
| 스토캐스틱 | George Lane | 매수 강화 확인 | Slow %K가 80 상향 돌파 |
| 채킨 오실레이터 | Marc Chaikin | 수급 확인 | 0선 상향 돌파 |
| MACD 오실레이터 | Gerald Appel | 최종 매수 결정 | 주봉 오실레이터 양전환 또는 상승 전환 |
| TD Sequential | Tom DeMark | 보완 지표 | Setup 9 또는 Countdown 13 완성 |

**신호 등급:**
- 1개 충족 (DMI): 기본매수
- 2개 충족: 매수강화
- 3~4개 충족: 이중매수
- 5개 충족: 완전매수

## 설치

```bash
# 기본 설치
pip install -e .

# API 서버 포함
pip install -e ".[api]"

# 개발 환경 (테스트 포함)
pip install -e ".[api,dev]"
```

## 실행

```bash
# API 서버 시작
python -m src.main

# 또는
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 시작 후 Swagger 문서: http://localhost:8000/docs

## API 엔드포인트

### GET /api/screen

드림팀 스크리닝 실행. 전 종목 또는 지정 종목에 대해 스크리닝합니다.

**Query Parameters:**
| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `market` | string | "ALL" | "KOSPI", "KOSDAQ", "ALL" |
| `codes` | string | - | 쉼표 구분 종목코드 (예: "005930,000660") |
| `min_strength` | int | 1 | 최소 신호 강도 (1-5) |
| `days` | int | 200 | 과거 데이터 일수 |

```bash
# 전 종목 스크리닝
curl "http://localhost:8000/api/screen"

# 특정 종목 스크리닝
curl "http://localhost:8000/api/screen?codes=005930,000660"

# KOSPI 종목만, 이중매수 이상
curl "http://localhost:8000/api/screen?market=KOSPI&min_strength=3"
```

### GET /api/stocks/{code}

개별 종목의 상세 지표를 조회합니다. 5개 지표의 최근 값과 신호 여부를 반환합니다.

```bash
curl "http://localhost:8000/api/stocks/005930"
```

### GET /api/indicators

현재 지표 설정값을 조회합니다.

```bash
curl "http://localhost:8000/api/indicators"
```

## 프로젝트 구조

```
src/
  api/
    app.py          # FastAPI 앱 생성
    routes.py       # API 라우트 정의
    schemas.py      # Pydantic 응답/요청 모델
    dependencies.py # 의존성 주입
  data/
    krx.py          # KRX 데이터 수집
    cache.py        # JSON 파일 기반 캐시
  types/
    stock.py        # StockInfo 타입
    ohlcv.py        # OHLCV, StockData 타입
  indicators/
    dmi.py          # DMI 지표
    stochastic.py   # 스토캐스틱 오실레이터
    chaikin.py      # 채킨 오실레이터
    macd.py         # MACD 오실레이터
    demark.py       # TD Sequential
  screener/
    engine.py       # 드림팀 스크리닝 엔진
    types.py        # DreamTeamSignal 타입
  config.py         # 환경변수 기반 설정
  main.py           # 서버 엔트리포인트
tests/
  test_api.py       # API 통합 테스트
```

## 설정

환경변수 또는 `.env` 파일로 설정합니다. `.env.example`을 참고하세요.

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `CACHE_DIR` | `.cache` | 캐시 디렉토리 경로 |
| `CACHE_TTL_HOURS` | `24` | 캐시 유효 시간 |
| `RATE_LIMIT_SECONDS` | `0.5` | KRX API 호출 간격 (초) |
| `HOST` | `0.0.0.0` | 서버 바인드 주소 |
| `PORT` | `8000` | 서버 포트 |

## 주의사항

- 본 프로그램은 기술적 분석 보조 도구입니다. 투자 판단의 최종 책임은 사용자에게 있습니다.
- KRX 데이터는 pykrx 라이브러리를 통해 수집되며, 데이터의 정확성을 보장하지 않습니다.
- 과거 지표 신호가 미래 수익을 보장하지 않습니다.
- 전 종목 스크리닝은 KRX API 호출 횟수가 많아 상당한 시간이 소요될 수 있습니다.
