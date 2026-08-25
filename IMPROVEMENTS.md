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
- end-to-end Frontier benchmark는 활성 검증 범위가 아니다. `--live` 명령은 호환성을 위해
  유지하지만, provider 호출 비용이 드는 비교 실행·결과 보존·채택 판단은 진행하지 않는다.

## 1. 보류: 자연어 입력 해석

`chew야 <URL> 이거 정리해줘` 같은 자연어를 현재 CLI 명령과 옵션으로만 구조화하는
`IntentParser`를 검토한다. 기본 경로는 결정적 URL·옵션 추출을 사용하며, 이후 opt-in local LLM은
허용된 `CommandIntent` JSON만 반환할 수 있다. 입력 해석기는 YouTube 접근, 브라우저·쿠키·Keychain
접근, 파일 삭제, 또는 Frontier 요약·판단을 수행하지 않는다. 데이터 변경 명령은 자연어 해석 후에도
명시적 확인이 필요하다.

이 항목은 현재 구현하지 않는다.

## 2. 보류: Grounded Knowledge Tree Agent runtime

기본 control-plane 계약은 구현되었다. `agents`의 immutable budget·tool grant·request/result과 승인 전
tool 실행을 차단하는 policy, 그리고 `interfaces`의 protocol-neutral presenter는 `CHANGELOG.md`에 기록한다.
이는 LangGraph, MCP, HTTP API, 또는 웹 UI를 추가한 것이 아니다.

실제 user flow가 정해질 때까지 typed Application Service tool, LangGraph optional `agents` extra, MCP,
HTTP API, 웹 UI를 추가하지 않는다. 재개할 때에는 먼저 완성된 Grounded Knowledge Tree만 읽고 렌더링하는
typed tool의 필요성을 검토한다. 선택된 Research, Style, Conversation, Publishing 역할에는 allowlist,
model/step/deadline 예산, 읽기·쓰기 artifact 범위, 승인 조건을 실행 전에 고정한다.

대화 session과 `CompilationRun`·`AgentRun`은 분리한다. graph checkpointer는 canonical SQLite
run/job/artifact schema와 분리하고 `session_id`, `run_id`, `tree_id`만 연결한다. 수신 여부가 불명확한
provider 요청이나 외부 write는 자동 반복하지 않는다. recursive dispatch와 agent의 DB·파일·credential
직접 접근은 허용하지 않는다.
