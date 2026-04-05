---
name: stock-hunter
description: "박문환 사프슈터 드림팀 지표 기반 한국 주식 스크리너 구축. /stock-hunter로 호출."
---

# StockHunter Orchestrator

박문환 사프슈터의 드림팀 지표를 리서치하고, 이를 기반으로 한국 주식시장에서 조건 충족 종목을 추출하는 서비스를 구축하는 에이전트 팀 오케스트레이터.

## 실행 모드: 에이전트 팀

## 에이전트 구성

| 팀원 | 에이전트 타입 | 역할 | 출력 |
|------|-------------|------|------|
| researcher | general-purpose | 드림팀 지표 리서치 및 정의 | `_workspace/01_dream_team_indicators.md` |
| data-eng | data-engineer (커스텀) | 한국 주식 데이터 수집 파이프라인 | `src/data/`, `src/types/` |
| indicator-dev | indicator-developer (커스텀) | 지표 계산 엔진 구현 | `src/indicators/`, `src/screener/` |
| integrator | service-integrator (커스텀) | 서비스 통합 및 API 구축 | `src/api/`, `src/main.py` |

## 워크플로우

### Phase 1: 준비 및 리서치

1. 프로젝트 루트에 `_workspace/` 생성
2. `references/dream-team-indicators.md`를 Read하여 기존 지표 정보 확인

3. 팀 생성:
   ```
   TeamCreate(
     team_name: "stock-hunter-team",
     members: [
       {
         name: "researcher",
         agent_type: "general-purpose",
         prompt: "당신은 금융 리서치 전문가입니다. 박문환(사프슈터, 메리츠증권)의 '드림팀 지표'를 리서치합니다.

목표: 박문환의 드림팀 지표의 정확한 구성과 기준을 문서화하세요.

작업:
1. WebSearch로 '박문환 드림팀 지표', '사프슈터 드림팀', '박문환 종목 선정 기준' 등을 검색
2. 각 지표의 정확한 임계값 (ROE > ?%, PER < ?배 등) 파악
3. 업종별 예외, 제외 조건, 특수 규칙 확인
4. references/dream-team-indicators.md를 Read하여 기존 정보와 비교

산출물: _workspace/01_dream_team_indicators.md에 다음 형식으로 작성:
- 지표명, 계산식, 임계값, 의미
- 복합 조건 (AND/OR)
- 제외 조건 (업종, 시가총액 등)
- 출처 URL

완료 후 리더에게 SendMessage로 알려주세요."
       },
       {
         name: "data-eng",
         agent_type: "data-engineer",
         prompt: "한국 주식시장 데이터 수집 파이프라인을 구축합니다.

Phase 1에서 researcher가 _workspace/01_dream_team_indicators.md를 작성할 때까지 대기하세요. 리더가 시작 지시를 보내면 작업을 시작합니다.

작업:
1. _workspace/01_dream_team_indicators.md를 Read하여 필요한 데이터 항목 파악
2. Python 프로젝트 스캐폴딩 (pyproject.toml, src/ 구조)
3. 데이터 모델/타입 정의 (src/types/stock.py, src/types/financial.py)
4. KRX 전 종목 목록 수집 모듈 (src/data/krx.py) — pykrx 사용
5. 재무제표 수집 모듈 (src/data/financial.py) — DART 또는 FinanceDataReader
6. 주가 데이터 수집 모듈 (src/data/price.py)
7. 데이터 캐싱 레이어 (src/data/cache.py)

원칙:
- 레이트 리미팅 필수
- null 데이터는 None으로 유지 (0 대체 금지)
- 각 모듈에 단위 테스트 작성

완료 후 indicator-dev에게 데이터 모델 구조를 SendMessage로 공유하고, 리더에게도 알려주세요."
       },
       {
         name: "indicator-dev",
         agent_type: "indicator-developer",
         prompt: "드림팀 지표 계산 엔진을 구현합니다.

Phase 1에서 researcher가 지표 정의를, data-eng가 데이터 모델을 완성할 때까지 대기하세요. 리더가 시작 지시를 보내면 작업을 시작합니다.

작업:
1. _workspace/01_dream_team_indicators.md를 Read하여 지표 정의 확인
2. data-eng의 데이터 모델(src/types/)을 Read하여 입력 구조 확인
3. 개별 지표 계산 함수 구현 (src/indicators/)
   - ROE, PER, PBR, 영업이익률, 부채비율, 매출성장률 등
4. 복합 스크리닝 엔진 (src/screener/engine.py)
   - 모든 지표 동시 충족 판정
   - 지표별 커스텀 임계값 지원
5. 각 지표 함수의 단위 테스트 (엣지 케이스 포함)

원칙:
- 순수 함수로 구현 (부작용 없음)
- 분모 0, None 입력 등 엣지 케이스 처리
- 계산 불가 시 None 반환 (에러 아님)

완료 후 integrator에게 스크리닝 API 인터페이스를 SendMessage로 공유하고, 리더에게도 알려주세요."
       },
       {
         name: "integrator",
         agent_type: "service-integrator",
         prompt: "스크리닝 서비스를 통합하고 API를 구축합니다.

data-eng와 indicator-dev의 작업이 완료될 때까지 대기하세요. 리더가 시작 지시를 보내면 작업을 시작합니다.

작업:
1. src/data/와 src/indicators/를 Read하여 구조 파악
2. FastAPI 기반 REST API 구현 (src/api/)
   - GET /api/screen — 드림팀 스크리닝 실행 (커스텀 임계값 파라미터)
   - GET /api/stocks/{code} — 개별 종목 상세 지표
   - GET /api/indicators — 현재 설정된 임계값 조회
3. 메인 엔트리포인트 (src/main.py)
4. 환경변수 설정 (.env.example)
5. 프로젝트 설정 완성 (pyproject.toml 의존성 추가)
6. 통합 테스트 작성
7. README.md 작성 (설치, 실행, API 문서)

원칙:
- API 응답 형식 통일: { success, data, error, meta }
- 입력 검증 (pydantic)
- 환경변수로 설정 관리

완료 후 리더에게 알려주세요."
       }
     ]
   )
   ```

4. 작업 등록:
   ```
   TaskCreate(tasks: [
     { title: "드림팀 지표 리서치", description: "박문환 드림팀 지표의 정확한 구성, 임계값, 조건을 리서치하여 문서화", assignee: "researcher" },
     { title: "프로젝트 스캐폴딩", description: "Python 프로젝트 구조 생성 (pyproject.toml, src/ 디렉토리)", assignee: "data-eng" },
     { title: "데이터 모델 정의", description: "종목, 재무제표, 지표 결과의 데이터 타입 정의", assignee: "data-eng", depends_on: ["드림팀 지표 리서치"] },
     { title: "KRX 데이터 수집 모듈", description: "pykrx로 전 종목 목록 및 시세 수집", assignee: "data-eng" },
     { title: "재무제표 수집 모듈", description: "DART/FDR로 재무제표 데이터 수집", assignee: "data-eng", depends_on: ["데이터 모델 정의"] },
     { title: "지표 계산 함수 구현", description: "ROE, PER, PBR 등 개별 지표 계산 함수", assignee: "indicator-dev", depends_on: ["드림팀 지표 리서치", "데이터 모델 정의"] },
     { title: "스크리닝 엔진 구현", description: "복합 조건 스크리닝 로직", assignee: "indicator-dev", depends_on: ["지표 계산 함수 구현"] },
     { title: "REST API 구현", description: "FastAPI 기반 스크리닝 API 엔드포인트", assignee: "integrator", depends_on: ["스크리닝 엔진 구현", "재무제표 수집 모듈"] },
     { title: "통합 테스트", description: "End-to-End 스크리닝 파이프라인 테스트", assignee: "integrator", depends_on: ["REST API 구현"] },
     { title: "프로젝트 문서화", description: "README, API 문서, 실행 가이드", assignee: "integrator", depends_on: ["통합 테스트"] }
   ])
   ```

### Phase 2: 리서치 수행

**실행 방식:** researcher가 독립 수행, 나머지는 대기

1. researcher가 드림팀 지표 리서치 수행
2. researcher가 `_workspace/01_dream_team_indicators.md` 작성 완료
3. researcher가 리더에게 완료 알림
4. 리더가 산출물을 Read하여 품질 확인
5. 충분한 정보가 확보되면 Phase 3 진행

**리더 개입 조건:**
- 리서치 결과에 구체적 임계값이 없으면 researcher에게 추가 검색 요청
- 10분 이상 결과가 없으면 현재까지의 부분 결과로 진행

### Phase 3: 병렬 구현

**실행 방식:** data-eng + indicator-dev 병렬 수행, integrator 대기

1. 리더가 data-eng에게 시작 지시: `SendMessage({to: "data-eng", message: "리서치 완료. _workspace/01_dream_team_indicators.md를 확인하고 데이터 파이프라인 구축을 시작하세요."})`
2. data-eng가 프로젝트 스캐폴딩 + 데이터 모델 정의
3. data-eng가 데이터 모델 완성 후 indicator-dev에게 SendMessage
4. 리더가 indicator-dev에게 시작 지시
5. data-eng: KRX 수집 + 재무제표 수집 (계속)
6. indicator-dev: 지표 계산 함수 + 스크리닝 엔진 (병렬)

**팀원 간 통신 규칙:**
- data-eng → indicator-dev: 데이터 모델 구조, 필드명, 타입 정보
- indicator-dev → integrator: 스크리닝 API 인터페이스 (입력 파라미터, 출력 구조)
- data-eng → integrator: 데이터 갱신 주기, API 제한 정보

**산출물 저장:**

| 팀원 | 출력 경로 |
|------|----------|
| data-eng | `src/data/`, `src/types/`, `pyproject.toml` |
| indicator-dev | `src/indicators/`, `src/screener/` |

### Phase 4: 서비스 통합

**실행 방식:** integrator 수행

1. data-eng, indicator-dev 작업 완료 확인 (TaskGet)
2. 리더가 integrator에게 시작 지시
3. integrator가 모든 모듈 통합 + API 구현
4. 통합 테스트 실행
5. 프로젝트 문서화

**산출물:** `src/api/`, `src/main.py`, `README.md`, `.env.example`

### Phase 5: 검증 및 정리

1. 리더가 최종 산출물 확인:
   - `src/` 디렉토리 구조 검증
   - API 엔드포인트 동작 확인 (가능하면 테스트 실행)
   - README 내용 확인
2. `_workspace/` 보존 (중간 산출물 감사 추적용)
3. 팀원들에게 종료 요청
4. 사용자에게 결과 요약 보고:
   - 드림팀 지표 요약
   - 프로젝트 구조
   - 실행 방법
   - 알려진 제한사항

## 데이터 흐름

```
[리더] → TeamCreate → [researcher] ──(지표 정의)──→ _workspace/01_*.md
                                                         │
                           ┌─────────────── Read ────────┘
                           ↓                             ↓
                      [data-eng]                  [indicator-dev]
                      src/data/                   src/indicators/
                      src/types/                  src/screener/
                           │      SendMessage         │
                           └──── (데이터 모델) ────→──┘
                           │                          │
                           └──────── Read ────────────┘
                                       ↓
                                [integrator]
                                  src/api/
                                  src/main.py
                                  README.md
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| researcher 리서치 실패 | references/dream-team-indicators.md의 기본 정보로 진행, 보고서에 명시 |
| data-eng API 연동 실패 | mock 데이터로 개발 진행, 실제 API 연동은 TODO로 남김 |
| indicator-dev 지표 정의 모호 | 보수적 임계값 적용, 커스터마이징 가능하도록 설계 |
| integrator 통합 실패 | data-eng/indicator-dev에게 SendMessage로 인터페이스 확인 |
| 팀원 과반 실패 | 사용자에게 알리고 부분 결과 제공 |

## 테스트 시나리오

### 정상 흐름
1. 사용자가 `/stock-hunter` 호출
2. Phase 1: 팀 구성 (4명 + 10개 작업)
3. Phase 2: researcher가 드림팀 지표 리서치 → 문서화
4. Phase 3: data-eng + indicator-dev 병렬 구현
5. Phase 4: integrator가 서비스 통합 + API 구현
6. Phase 5: 검증 완료
7. 결과: Python 프로젝트 (`src/` 하위 완성)

### 에러 흐름
1. Phase 2에서 researcher가 정확한 임계값을 찾지 못함
2. 리더가 references의 기본 정보 + researcher의 부분 결과를 결합
3. `_workspace/01_dream_team_indicators.md`에 "확인 필요" 항목 표시
4. Phase 3에서 indicator-dev가 임계값을 설정 파일로 외부화
5. 사용자가 나중에 임계값을 조정 가능하도록 설계
6. 최종 보고서에 "임계값 검증 필요" 명시
