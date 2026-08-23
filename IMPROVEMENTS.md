# `youtube-summarizer-kit` 활성 개선 작업

> 이 문서는 아직 끝나지 않은 성능, 품질, 안전성 작업만 관리한다.
> 완료된 구현 이력은 [`CHANGELOG.md`](CHANGELOG.md), 보류된 제품 확장 기능은
> [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)를 기준으로 한다.

## 운영 원칙

- 최종 요약과 사용자에게 보이는 판단은 사용자의 BYOK Frontier runtime이 담당한다.
- Ollama는 Frontier의 요약·판단을 대체하지 않는다. 명확히 정의된 저위험 보조 작업이 생기고
  실측 이득이 확인될 때만 별도 opt-in으로 검토한다.
- 단발성 영상 요약에는 임베딩, RAG, vector DB를 기본 경로에 넣지 않는다.
- 원문 transcript는 근거 검증의 기준이며, 전처리본은 별도 derived artifact로 취급한다.

## 1. 자막 전처리 채택 벤치마크

**현재 결과:** 잠금된 영어 fixture에서 보수적 필러 제거는 약 2.2% token reduction을 보였다.
품질 평가는 아직 없으므로 `preprocess_transcript` 기본값은 계속 `false`다.

### 남은 작업

1. 한국어 대화형·강의형 fixture를 추가하고 39분, 55분 영상의 baseline과 candidate를 다시 측정한다.
2. 같은 Frontier runtime/model, prompt fingerprint, concurrency에서 raw와 processed 경로를 비교한다.
3. token/cost, 전체 시간, evidence recall, timestamp accuracy, missing range, unsupported claim을 함께 기록한다.
4. `reports/performance-comparisons/` 아래 검토된 보고서에 기본값 채택 여부를 명시한다.

### 채택 기준

기본 활성화는 다음을 모두 만족할 때만 검토한다.

1. 실제 provider input usage 또는 비용이 기준선보다 10% 이상 감소한다.
2. evidence recall, timestamp accuracy, 핵심 주장 recall이 저하되지 않는다.
3. partial result와 missing range가 증가하지 않는다.
4. 30분 및 1시간 fixture의 처리 시간 중앙값이 허용한 회귀 한도를 넘지 않는다.

미달하면 전처리는 opt-in으로 유지하며 절감률을 마케팅 문구로 사용하지 않는다.

## 1.5 P0: 입력 획득 신뢰성 및 Keychain 비의존

이 서비스의 첫 번째 성공 조건은 Frontier 요약 이전에 검증 가능한 raw transcript를 얻는 것이다.
2026-08-24 실측에서 5분 fixture의 정식 `chew summarize`는 YouTube provider chain에서 3분 이상
대기한 뒤 중단됐으며 Knowledge Pack과 Frontier 호출까지 도달하지 못했다. 브라우저 로그인 쿠키를
읽는 방식은 macOS Keychain 접근을 유발하므로 기본 경로나 필수 복구 경로가 될 수 없다.

### P0 원칙

- 쿠키, 비밀번호, Keychain 값, 브라우저 credential store를 읽거나 저장하지 않는다.
- 제3자 transcript 웹사이트를 제품의 서버 fallback으로 의존하지 않는다.
- 공개 YouTube provider가 실패해도 전체 CLI가 무기한 대기하지 않는다.
- 사용자가 제공하거나 화면에서 명시적으로 캡처한 transcript는 provenance를 보존한 raw input으로
  받아 이후 Frontier-first 파이프라인을 완주할 수 있어야 한다.

### 남은 작업

1. 각 transcript provider에 20초 deadline, 전체 acquisition에 60초 deadline을 적용한다. timeout,
   `429`, `FAILED_PRECONDITION`, 세션 갱신 요구를 구조화된 attempt reason으로 보존하고 즉시 다음
   provider 또는 사용자 복구 경로로 넘어간다.
2. `chew summarize --transcript <VTT|SRT|TXT>` 입력 adapter를 추가한다. 원본 URL은 `--source-url`로
   별도 제공받아 identity와 결과 링크를 보존하고, parser가 timestamp/language/provenance를 검증한다.
3. 로그인 브라우저의 **보이는 YouTube 스크립트 패널만** 사용자가 명시적으로 캡처해 전달하는 browser
   capture adapter를 별도 설계한다. 쿠키·네트워크 요청·Keychain 접근은 금지한다.
4. 실제 5분 fixture에서 `URL/사용자 transcript → raw snapshot → 전처리 → Frontier → Knowledge Pack`
   전체 흐름을 실행해 transcript provenance, elapsed time, Frontier usage, output evidence를 기록한다.
5. 기존 browser-cookie `auth youtube` 경로는 P0 원칙을 만족하는 transcript input 경로가 검증될 때까지
   기본 안내에서 제거하고, Keychain 접근이 발생할 수 있음을 명시한다.

### 완료 기준

1. YouTube 공개 자막이 `429`여도 60초 이내에 실패 이유 또는 사용자 제공 transcript 경로를 반환한다.
2. VTT/SRT/TXT 입력만으로 Chrome/Keychain/쿠키 접근 없이 Knowledge Pack과 Digest를 생성한다.
3. 5분 fixture에서 실제 transcript 기반 end-to-end run이 Frontier output까지 완료되고 생성 artifact가
   재실행 없이 재조립된다.
4. provider outage가 있으면 quality report를 생성하지 않으며, benchmark의 두 조건은 동일 raw transcript
   snapshot을 공유한다.

## 2. 짧은 영상 Frontier 경로 선택

15분 이하 영상은 계층 요약의 호출·schema·중간 output 오버헤드가 이득보다 클 수 있다.
같은 Frontier runtime으로 단일 요약과 계층 요약을 비교해 더 단순한 기본 경로를 선택한다.

1. 같은 transcript, Frontier runtime/model, prompt version에서 두 경로의 provider usage와 전체 시간을 비교한다.
2. overview 품질, evidence coverage, timestamp accuracy, key-claim recall을 함께 검토한다.
3. 단일 경로가 비용·시간에서 유리하면서 품질이 저하되지 않을 때만 짧은 영상의 기본 경로로 채택한다.

## 3. Policy 및 Sandbox 경계 강화

Evidence span 검증과 Frontier-first `ExecutionPlan`은 구현되어 있다. 남은 작업은 문서상의
논리 경계를 실제 강제 경계에 가깝게 만드는 것이다.

1. `ExecutionPlan`에 task별 timeout, retry limit, partial-result 정책을 기록할지 결정하고,
   채택하면 scheduler가 해당 기록만 사용하도록 한다.
2. 실제 Frontier run에서 invalid evidence candidate 처리와 partial result 표시를 검증한다.

OS container와 subprocess sandbox는 현재 범위가 아니다. MCP 또는 REST API를 다시 검토할 때
권한 모델과 함께 별도 설계한다.

## 4. 낮은 우선순위 기술 부채

- telemetry 전역 singleton을 `ContextVar`로 격리
- SQLite migration을 버전별 migration 체계로 정식화
- segmentation의 하드코딩 한국어 키워드 제거

이 항목은 benchmark 완료와 sandbox 보강보다 우선하지 않는다.
