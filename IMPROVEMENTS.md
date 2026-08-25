# `youtube-summarizer-kit` 활성 개선 작업

> 이 문서는 아직 끝나지 않은 성능, 품질, 안전성 작업만 관리한다.
> 완료된 구현 이력은 [`CHANGELOG.md`](CHANGELOG.md), 보류된 제품 확장 기능은
> [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)를 기준으로 한다.

## 운영 원칙

- 최종 요약과 사용자에게 보이는 판단은 사용자의 BYOK Frontier runtime이 담당한다.
- Ollama는 설치된 단일 모델이 있을 때 입력 정리 annotation만 제안할 수 있다. 요약·판단·claim 생성,
  Knowledge Pack 작성은 Frontier를 대체하지 않으며 실행 중 모델을 자동 설치하지 않는다.
- 단발성 영상 요약에는 임베딩, RAG, vector DB를 기본 경로에 넣지 않는다.
- 원문 transcript는 근거 검증의 기준이며, 전처리본은 별도 derived artifact로 취급한다.
- end-to-end Frontier benchmark는 기능·정책·종료 조건 변경을 모두 완료한 뒤, 배포 직전의
  통합 검증으로만 실행한다. 중간 구현의 단발 측정은 채택 또는 회귀 판단에 사용하지 않는다.

## 1. 자막 전처리 채택 벤치마크

**현재 결과:** `2026-08-24`에 원래 잠금된 5개 영어 fixture를 metrics-only로 다시 측정했다.
보수적 필러 제거는 79,788에서 78,056 token으로 **2.2%** 감소했고 모든 영상이 같은 lock으로
성공했다. 이는 tokenizer 측정이며 provider 비용은 아니다. Frontier 품질 평가는 아직 없으므로
`preprocess_transcript` 기본값은 계속 `false`다.

### 남은 작업

1. 한국어 강의·대화형 fixture의 baseline과 candidate를 같은 조건에서 측정한다.
2. 같은 Frontier runtime/model, prompt fingerprint, concurrency에서 raw와 processed 경로를 비교한다.
3. token/cost, 전체 시간, evidence recall, timestamp accuracy, missing range, unsupported claim을 함께 기록한다.
4. `benchmarks/reference-drafts/`의 후보를 사람이 승인한 뒤 executable JSON reference로 전사한다.
5. `reports/performance-comparisons/` 아래 검토된 보고서에 기본값 채택 여부를 명시한다.

### 채택 기준

기본 활성화는 다음을 모두 만족할 때만 검토한다.

1. 실제 provider input usage 또는 비용이 기준선보다 10% 이상 감소한다.
2. evidence recall, timestamp accuracy, 핵심 주장 recall이 저하되지 않는다.
3. partial result와 missing range가 증가하지 않는다.
4. 30분 및 1시간 fixture의 처리 시간 중앙값이 허용한 회귀 한도를 넘지 않는다.

미달하면 전처리는 opt-in으로 유지하며 절감률을 마케팅 문구로 사용하지 않는다.

## 2. Grounded Knowledge Tree 기반 단일 Frontier Compiler

영상 길이에 따라 topic/chapter/compose Frontier fan-out을 선택하지 않는다. 준비된 transcript가 선택한
runtime/model의 정적 입력 예산에 맞으면 전체 구조화 Knowledge Pack 초안을 Frontier 1회로 생성한다.
맞지 않을 때만 두 단계 refine을 허용하며 영상당 semantic Frontier 호출 상한은 2회다.
구현 계약은 [`docs/superpowers/specs/2026-08-25-grounded-knowledge-tree-hybrid-design.md`](docs/superpowers/specs/2026-08-25-grounded-knowledge-tree-hybrid-design.md)를 따른다. 기존 `KnowledgePack` 호환성을 유지하면서
미검증 `KnowledgeTreeDraft`와 검증 완료 `GroundedKnowledgeTree`를 분리하고, 기본 output profile은
Grounded Knowledge Tree에서 추가 모델 호출 없이 렌더링한다.

**현재 결과:** `2026-08-24`에 사용자 승인 reference로 공개 영어 자동자막 영상
[`aBUniZHgCnE`](https://www.youtube.com/watch?v=aBUniZHgCnE) (14분 34초)을 Codex로 3회씩
비교했다. 동일 raw transcript snapshot을 사용했지만 단일 경로의 중앙 latency/usage는
16.952초/29,192, 계층 경로는 57.744초/348,963이었다. 계층 경로의 key-point recall과
timestamp accuracy 중앙값은 각각 0.25였고, 두 경로의 evidence coverage는 0.0이었다.
reference-evidence 정합성과 경로 간 prompt fingerprint가 아직 비교 기준을 만족하지 않으므로,
이 결과로 기본 경로를 바꾸지 않는다.

### 구현 작업

1. **Input Compiler:** raw transcript를 불변 보존하고 prepared transcript와 segment ID mapping을 만든다.
   설치된 단일 Ollama 모델은 최대 1회의 입력 정리 annotation만 제안하며, 실패하거나 token을 5% 넘게
   증가시키면 결정론적 baseline으로 fallback한다.
2. **Grounded Knowledge Tree Compiler:** 기존 topic N + chapter M + compose Frontier DAG를 기본 경로에서
   단일 structured extraction으로 교체한다. 입력 예산 초과 시에만 최대 2회의 refine을 허용하고, raw
   evidence와 timestamp를 로컬 검증한 뒤 Grounded Knowledge Tree와 호환 Knowledge Pack을 조립한다.
3. **Output Renderer:** digest/blog/study/obsidian 기본 출력의 outline/compose/verify 모델 호출을 제거하고
   Grounded Knowledge Tree에서 결정론적으로 렌더링한다. 이후 Output Pack과 Render Skill은 이 경계 위에
   추가하며 기본 compiler의 Frontier 호출 예산을 사용하지 않는다.
4. **Workflow:** role-based runtime policy, 단계별 checkpoint, pause/resume, unknown external outcome,
   OpenTelemetry span, 기존 benchmark 전략 호환을 같은 실행 계약으로 연결한다.

### 수용 기준

1. 일반 입력의 Frontier semantic 호출은 정확히 1회다.
2. 입력 예산 초과 fallback도 최대 2회이며 자동 3회 이상 fan-out이 없다.
3. Ollama의 존재·실패 여부가 Frontier 호출 수를 늘리지 않는다.
4. 모든 기본 출력 profile은 저장된 Knowledge Pack만으로 생성된다.
5. evidence recall, timestamp accuracy, 핵심 claim recall이 기존 검토 기준보다 저하되지 않는다.

## 3. 보류: 자연어 입력 해석

`chew야 <URL> 이거 정리해줘` 같은 자연어를 현재 CLI 명령과 옵션으로만 구조화하는
`IntentParser`를 검토한다. 기본 경로는 결정적 URL·옵션 추출을 사용하며, 이후 opt-in local LLM은
허용된 `CommandIntent` JSON만 반환할 수 있다. 입력 해석기는 YouTube 접근, 브라우저·쿠키·Keychain
접근, 파일 삭제, 또는 Frontier 요약·판단을 수행하지 않는다. 데이터 변경 명령은 자연어 해석 후에도
명시적 확인이 필요하다.

이 항목은 현재 구현하지 않는다.

## 4. Grounded Knowledge Tree Agent 오케스트레이션 기반

Grounded Knowledge Tree compiler를 먼저 완성한 뒤 LangGraph를 optional `agents` extra로 추가한다. core compiler는 LangGraph를
import하지 않으며, `SessionGraph`와 bounded agent subgraph가 typed Application Service tool을 통해 완성된
Grounded Knowledge Tree를 소비한다. Research, Style, Conversation, Publishing agent는 각각 tool allowlist, model/step/deadline
예산, 읽기·쓰기 artifact 범위, 승인 조건을 실행 전에 고정한다.

대화 session과 `CompilationRun`·`AgentRun`은 분리한다. LangGraph checkpointer는 기존 canonical SQLite
run/job/artifact schema와 분리하고 `session_id`, `run_id`, `tree_id`로 연결한다. pause/resume은 단계별
checkpoint를 사용하며, 수신 여부가 불명확한 provider 요청이나 외부 write는 자동 반복하지 않는다.

첫 Agent 구현 전에도 role-based policy, Harness adapter 경계, Grounded Knowledge Tree typed tool, durable
correlation ID를 먼저 정의한다. recursive agent dispatch와 agent의 DB·파일·credential 직접 접근은 허용하지 않는다.
