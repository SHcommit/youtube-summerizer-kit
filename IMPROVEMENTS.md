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

## 미래 모듈 경계

[`Grounded Knowledge Compiler and Future Modules Design`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)에서 `chew`를 **Grounded Knowledge Compiler**로 정의한다. [`modules/intent-analysis/README.md`](modules/intent-analysis/README.md)와 [`modules/research-engine/README.md`](modules/research-engine/README.md)는 미래에 독립 추출할 모듈의 문서 경계이며, 현재는 실행 가능한 패키지가 아니다.

## 저장소 거버넌스 기준

[`Repository Governance Decision`](docs/decisions/0002-repository-governance.md)은 GitHub Repository를
Engineering OS로 발전시키기 위한 원본 평가와 운영 원칙을 보존한다. 이 문서의 P0/P1/P2 항목은 그 결정의
실행 큐다. 세부 배경이나 "왜 이 자동화는 지금 도입하고 다른 자동화는 보류하는가"는 decision 문서를 기준으로
판단한다.

### 실행 규칙

각 항목을 구현하기 전에 먼저 decision 문서의 관련 구간을 읽고, 이번 작업이 어떤 부족함을 메우는지
작업 기록이나 PR 설명에 짧게 남긴다.

- 버전·태그·릴리스 작업 전: `Release Version Policy`, `Tooling Decision`을 확인한다.
- `CHANGELOG.md`나 GitHub Release 작업 전: `CHANGELOG Policy`를 확인한다.
- 라벨·브랜치·PR·Issue·Project 작업 전: 각각 `Label Policy`, `Branch Policy`, `PR Policy`,
  `Issue and Project Policy`를 확인한다.
- prompt, model, harness, benchmark, runtime 관련 작업 전: `AI Project Policy`를 확인한다.
- 자동화 추가 전: `Context`, `Tooling Decision`, `Consequences`를 확인해 현재 규모에서 ROI가 맞는지
  다시 판단한다.

이 규칙의 목적은 개선 작업이 체크리스트 소거로 흐르지 않게 하고, 원본 감사에서 확인한 실제 결함
— traceability 부족, version drift, stale naming, 과도한 CHANGELOG 책임, GitHub 운영 객체 미연결 — 을
계속 기준점으로 삼는 것이다.

## 1. P0: 릴리스 required checks 연결 — 완료 (release/\* 제외)

`feat/repository-governance` → `develop` PR(#12)에서 각 workflow의 실제 check run 이름을 확인한 뒤
required status checks를 연결했다.

- `require-ci-status` ruleset (`develop`, `master`): `test (3.12)`, `test (3.13)`,
  `Check PR metadata and stale instructions`.
- `require-release-consistency` ruleset (`master`만): `Check release version consistency`.
- 기존 `protect-branches` ruleset(`~DEFAULT_BRANCH`, `develop`, `master`, `release/*`)의
  deletion/non-fast-forward/PR requirement는 변경하지 않았다.

### `release/*`를 제외한 이유

`ci.yml`과 `pr-governance.yml`의 `pull_request.branches`는 `[develop, master, main]`만 포함하고
`release/*`를 포함하지 않는다. `protect-branches`가 이미 `release/*`를 대상으로 하기 때문에, 만약
required status checks를 `release/*`까지 포함한 단일 ruleset에 걸었다면 release 브랜치를 base로 하는
PR은 존재하지 않는 check를 영원히 기다리며 merge가 막혔을 것이다. 그래서 required checks는 실제로 해당
workflow가 트리거되는 `develop`/`master`에만 연결했다.

### 남은 작업

- `release/*`를 base로 하는 PR(예: release 브랜치로의 hotfix)이 실제로 필요해지면, 먼저
  `ci.yml`/`pr-governance.yml`의 `pull_request.branches`에 `release/*`를 추가해 check run이 실제로
  생성되게 한 뒤, `require-ci-status` ruleset의 대상에 `refs/heads/release/*`를 추가한다. 지금은 해당
  시나리오가 없으므로 선제적으로 만들지 않는다.

### Acceptance gates

- [x] `gh api repos/SHcommit/youtube-summerizer-kit/rules/branches/master`에 `required_status_checks`가
  2건(CI/PR Governance, Release Consistency) 보인다.
- [x] `gh api repos/SHcommit/youtube-summerizer-kit/rules/branches/develop`에 `required_status_checks`가
  1건(CI/PR Governance) 보인다.
- [ ] `release/*` PR 시나리오가 생기면 위 "남은 작업"을 수행한다.

## 2. P1: 저장소 명칭과 문서 drift 감시

활성 문서와 테스트 env var는 `chew` 기준으로 정리되었다. 남은 작업은 오래된 명칭이 다시 들어오지 않게
PR governance를 유지하고, GitHub repository URL의 `youtube-summerizer-kit` 철자와 package/distribution 이름
`youtube-summarizer-kit`의 차이를 사용자 문서에서 혼동하지 않도록 관리하는 것이다.

### 작업

- `pr-governance.yml`의 stale instruction check가 기본 브랜치에서 안정적으로 통과하는지 확인한다.
- repository URL 철자는 실제 GitHub slug로만 쓰고, package/distribution 이름은 `youtube-summarizer-kit`로
  표기하는 원칙을 유지한다.

### Acceptance gates

- active instruction 검색에서 `mypy src/ytsum` 또는 `YTSUM_LIVE_`가 다시 나타나지 않는다.
- historical changelog와 ADR 문제 설명을 제외하고 `src/ytsum`이 active contributor instruction에 남지 않는다.

## 3. P1: GitHub Labels와 자동 분류 체계 유지

GitHub prefix labels, file-based `area:*` labeler, PR title/branch 기반 metadata labeler는 도입되었다.
남은 작업은 새 PR에서 Auto Labeler가 실패하지 않는지 확인하고, priority/impact/status 자동화가 실제로
필요한지 판단하는 것이다.

### 작업

- priority와 final impact는 파일 경로만으로 판단하지 않는다. 실제 triage 비용이 남는 경우에만 추가 자동화를
  검토한다.

### Acceptance gates

- Auto Labeler가 `pull_request_target`에서 성공한다.
- 자동화되지 않은 priority/final impact는 maintainer triage로 남긴다.

## 4. P1: Branch와 PR 운영 규칙 강화 유지

`master`와 `develop` 강제 push 방지는 repository ruleset으로 적용되었다. PR template, PR governance
workflow, topic branch CI trigger는 도입되었다. 남은 작업은 새 workflow들이 기본 브랜치에 올라간 뒤
ruleset required status checks에 연결하는 것이다.

### 작업

- `develop`과 `master`에 required status checks를 연결한다.

### Acceptance gates

- `develop`과 `master`로 직접 merge되기 전 CI가 required check로 동작한다.
- release PR은 `release/vX.Y.Z`에서 `master`를 target으로 한다.

## 5. P1: Project 운영 자동화

YAML Issue Forms는 도입되었고, 기존 open issue #1-#3는 라벨과 `youtube-summarizer-kit Engineering`
Project에 편입되었다. 새 issue/PR 자동 편입 workflow도 도입되었지만, 사용자 Project 쓰기 권한을 가진
`PROJECTS_TOKEN`이 설정되어야 실제로 동작한다.

### 작업

- 기본 status는 `Inbox`, `Ready`, `Doing`, `Review`, `Benchmark`, `Release`, `Done`으로 둔다.
- `PROJECTS_TOKEN`을 설정할지, 수동 Project triage를 유지할지 결정한다.

### Acceptance gates

- `PROJECTS_TOKEN`이 있으면 새 issue/PR이 Project에 자동 편입된다.
- `PROJECTS_TOKEN`이 없으면 workflow가 실패하지 않고 수동 triage로 남는다.
- Project가 roadmap 문서의 중복물이 아니라 현재 실행 상태만 보여준다.

## 6. P1: CHANGELOG 역할 축소와 Release Note 연결

`CHANGELOG.md`는 유지하되 내부 작업 일지를 모두 담는 문서가 되면 안 된다. GitHub Release generated notes,
PR release note, ADR, benchmark report와 책임을 나누어야 한다.

### 작업

- `CHANGELOG.md`는 사용자·운영자가 알아야 할 완료 변경만 기록한다.
- PR template의 `Release Note` 필드를 GitHub Release 초안의 근거로 사용한다.
- 내부 결정은 `docs/decisions/`, 성능 근거는 `reports/BENCHMARK.md`, 현재 진행 상태는 Project와
  `handoff.md`로 분리한다.
- release PR에서 `[Unreleased]` 내용을 `## [X.Y.Z] - YYYY-MM-DD`로 이동하는 절차를 문서화한다.

### Acceptance gates

- `CHANGELOG.md`의 `[Unreleased]`가 release마다 비워지거나 다음 개발 항목만 남는다.
- GitHub Release 본문이 단순 PR 목록만이 아니라 핵심 사용자 영향과 benchmark/report 링크를 포함한다.
- `docs/agent-index.md`가 changelog, ADR, benchmark, wiki, project의 역할 차이를 설명한다.

## 7. P2: Architecture, Benchmark, AI 변경 감지 자동화

모든 PR에 live provider benchmark를 돌리는 것은 비용 대비 과하다. 대신 변경 영역을 감지해 필요한
검증을 요구하는 조건부 자동화가 맞다.

### 작업

- `src/chew/core/**`, `src/chew/pipeline/**`, `src/chew/app/**`, `src/chew/interfaces/**` import 방향을
  검사하는 architecture validation을 추가한다.
- `area:pipeline`, `area:harness`, `area:benchmark`, `impact:performance` 라벨이 붙은 PR에는 benchmark 필요 여부를
  PR checklist에서 명시하게 한다.
- prompt, schema, model, harness 변경은 `AI / Runtime Impact` checklist에서 evaluation 필요 여부를 남긴다.

### Acceptance gates

- architecture boundary 위반이 CI에서 실패한다.
- performance-sensitive PR은 benchmark를 실행했거나 실행하지 않은 이유를 PR에 남긴다.
- live provider test는 명시적 opt-in으로만 실행된다.

## 8. P2: Engineering Knowledge Management 유지

ADR index와 release playbook은 도입되었다. 남은 작업은 새 decision/report가 생길 때
`docs/agent-index.md`를 계속 갱신하는 것이다.

### 작업

- prompt/model/evaluation history는 실제 변경 빈도가 생길 때 `docs/ai/` 또는 `docs/models/`로 분리한다.
  지금은 빈 체계를 만들지 않는다.

### Acceptance gates

- 장기 지식은 `CHANGELOG.md`가 아니라 ADR/wiki/report 중 맞는 위치에 저장된다.

## 9. 보류: `intent-analysis` 자연어 요청 분석

`intent-analysis`는 `IntentParser`를 통해 자연어 Message를 허용된 Intent, Clarification, Unsupported 중 하나로만 해석한다. 기본 경로는 결정적 URL·옵션 추출과 고신뢰 패턴이며, 이후 opt-in local adapter는 schema-validated intent 후보만 반환할 수 있다. 입력 해석기는 YouTube 접근, 브라우저·쿠키·Keychain 접근, 파일 삭제, 도구 실행, 또는 Frontier 요약·판단을 수행하지 않는다. 데이터 변경 명령은 자연어 해석 후에도 명시적 확인이 필요하다.

이 항목은 현재 구현하지 않는다. 먼저 첫 user flow와 capability catalog를 확정해야 한다.

## 10. 보류: `research-engine`와 Grounded Knowledge Tree Agent runtime

기본 control-plane 계약은 구현되었다. `agents`의 immutable budget·tool grant·request/result과 승인 전
tool 실행을 차단하는 policy, 그리고 `interfaces`의 protocol-neutral presenter는 `CHANGELOG.md`에 기록한다.
이는 LangGraph, MCP, HTTP API, 또는 웹 UI를 추가한 것이 아니다.

실제 user flow와 versioned read-only `KnowledgeGateway`가 정해질 때까지 typed Application Service tool,
LangGraph optional `agents` extra, MCP, HTTP API, 웹 UI, 모델 의존성을 추가하지 않는다. 재개할 때에는 먼저
완성된 Grounded Knowledge Tree와 Knowledge Pack만 읽는 typed gateway의 필요성을 검토한다. 선택된 Research,
Style, Conversation, Publishing 역할에는 allowlist,
model/step/deadline 예산, 읽기·쓰기 artifact 범위, 승인 조건을 실행 전에 고정한다.

대화 session과 `CompilationRun`·`AgentRun`은 분리한다. graph checkpointer는 canonical SQLite
run/job/artifact schema와 분리하고 `session_id`, `run_id`, `tree_id`만 연결한다. 수신 여부가 불명확한
provider 요청이나 외부 write는 자동 반복하지 않는다. recursive dispatch와 agent의 DB·파일·credential
직접 접근은 허용하지 않는다.
