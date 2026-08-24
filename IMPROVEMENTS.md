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
- end-to-end Frontier benchmark는 기능·정책·종료 조건 변경을 모두 완료한 뒤, 배포 직전의
  통합 검증으로만 실행한다. 중간 구현의 단발 측정은 채택 또는 회귀 판단에 사용하지 않는다.

## 1. 자막 전처리 채택 벤치마크

**현재 결과:** 잠금된 영어 fixture에서 보수적 필러 제거는 약 2.2% token reduction을 보였다.
품질 평가는 아직 없으므로 `preprocess_transcript` 기본값은 계속 `false`다.

### 남은 작업

1. 한국어 대화형 fixture를 추가한다. 한국어 강의 fixture
   `youtube_ko_45m46s_for_benchmark`는 lock에 추가되었지만, baseline/candidate 측정은
   배포 직전 통합 gate까지 실행하지 않는다.
2. 39분, 55분 영상과 한국어 fixture의 baseline과 candidate를 같은 조건에서 측정한다.
3. 같은 Frontier runtime/model, prompt fingerprint, concurrency에서 raw와 processed 경로를 비교한다.
4. token/cost, 전체 시간, evidence recall, timestamp accuracy, missing range, unsupported claim을 함께 기록한다.
5. `reports/performance-comparisons/` 아래 검토된 보고서에 기본값 채택 여부를 명시한다.

### 채택 기준

기본 활성화는 다음을 모두 만족할 때만 검토한다.

1. 실제 provider input usage 또는 비용이 기준선보다 10% 이상 감소한다.
2. evidence recall, timestamp accuracy, 핵심 주장 recall이 저하되지 않는다.
3. partial result와 missing range가 증가하지 않는다.
4. 30분 및 1시간 fixture의 처리 시간 중앙값이 허용한 회귀 한도를 넘지 않는다.

미달하면 전처리는 opt-in으로 유지하며 절감률을 마케팅 문구로 사용하지 않는다.

## 2. 짧은 영상 Frontier 경로 선택

15분 이하 영상은 계층 요약의 호출·schema·중간 output 오버헤드가 이득보다 클 수 있다.
같은 Frontier runtime으로 단일 요약과 계층 요약을 비교해 더 단순한 기본 경로를 선택한다.

1. 같은 transcript, Frontier runtime/model, prompt version에서 두 경로의 provider usage와 전체 시간을 비교한다.
2. overview 품질, evidence coverage, timestamp accuracy, key-claim recall을 함께 검토한다.
3. 단일 경로가 비용·시간에서 유리하면서 품질이 저하되지 않을 때만 짧은 영상의 기본 경로로 채택한다.

## 3. 보류: 자연어 입력 해석

`chew야 <URL> 이거 정리해줘` 같은 자연어를 현재 CLI 명령과 옵션으로만 구조화하는
`IntentParser`를 검토한다. 기본 경로는 결정적 URL·옵션 추출을 사용하며, 이후 opt-in local LLM은
허용된 `CommandIntent` JSON만 반환할 수 있다. 입력 해석기는 YouTube 접근, 브라우저·쿠키·Keychain
접근, 파일 삭제, 또는 Frontier 요약·판단을 수행하지 않는다. 데이터 변경 명령은 자연어 해석 후에도
명시적 확인이 필요하다.

이 항목은 현재 구현하지 않는다.

## 4. 보류: Agent 세션과 외부 호출 대기 최적화

대화형 session tree는 기존 run/job 재개 상태와 분리해, 사용자 메시지·해석된 명령·부모 session node·연결된
run ID·output artifact만 참조한다. 실행 중인 `ExecutionPlan`이나 run의 불변 정책을 session이 변경하지
않으며, 중단 후에는 기존 run state machine으로 재개한다.

MCP 또는 외부 agent/LLM 호출을 도입할 때는 `await` 기반의 비차단 대기, durable external-request 상태,
deadline, cancellation, idempotency key, 그리고 재개 가능한 결과 수집을 별도 설계한다. 대기 중인 요청은
이벤트 루프를 점유하지 않아야 하지만, 실제 provider 요청이 진행 중인 동안에는 rate limit과 중복 과금을
막기 위해 해당 provider concurrency slot을 해제하지 않는다. 폴링은 busy-wait 대신 이벤트·callback 또는
제한된 backoff를 사용한다.

이 항목은 현재 구현하지 않는다.
