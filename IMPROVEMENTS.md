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

[`Grounded Knowledge Compiler and Future Modules Design`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)에서 `chew`를 **Grounded Knowledge Compiler**로 정의한다. [`modules/intent-analysis/README.md`](modules/intent-analysis/README.md)와 [`modules/research-engine/README.md`](modules/research-engine/README.md)는 미래에 독립 추출할 모듈의 문서 경계이며, 현재는 실행 가능한 패키지가 아니다. 두 모듈을 실제로 활성화하는 조건과 제약은 [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)의 해당 항목에서 관리한다.

## 저장소 거버넌스 기준

[`Repository Governance Decision`](docs/decisions/0002-repository-governance.md)은 GitHub Repository를
Engineering OS로 발전시키기 위한 원본 평가와 운영 원칙을 보존한다. 이 결정의 P0/P1/P2 실행 큐(required
status checks, 명칭/문서 drift 감시, GitHub Labels 자동 분류, CHANGELOG 역할 축소, Engineering
Knowledge Management)는 v0.3.1 릴리스 기준으로 모두 완료 또는 상시 유지 단계로 전환되었다 — 완료 이력은
`CHANGELOG.md`와 과거 PR(#12, #16, #18, #20, #23)에 남아 있다. 새 결함이나 항목이 발견되면 아래
"실행 규칙"을 따라 이 문서에 다시 추가한다.

### 실행 규칙

각 항목을 구현하기 전에 먼저 decision 문서의 관련 구간을 읽고, 이번 작업이 어떤 부족함을 메우는지
작업 기록이나 PR 설명에 짧게 남긴다.

- 버전·태그·릴리스 작업 전: `Release Version Policy`, `Tooling Decision`을 확인한다.
- `CHANGELOG.md`나 GitHub Release 작업 전: `CHANGELOG Policy`를 확인한다.
- 라벨·브랜치·PR·Issue 작업 전: 각각 `Label Policy`, `Branch Policy`, `PR Policy`,
  `Issue and Work Tracking Policy`를 확인한다.
- prompt, model, harness, benchmark, runtime 관련 작업 전: `AI Project Policy`를 확인한다.
- 자동화 추가 전: `Context`, `Tooling Decision`, `Consequences`를 확인해 현재 규모에서 ROI가 맞는지
  다시 판단한다.

이 규칙의 목적은 개선 작업이 체크리스트 소거로 흐르지 않게 하고, 원본 감사에서 확인한 실제 결함
— traceability 부족, version drift, stale naming, 과도한 CHANGELOG 책임, GitHub 운영 객체 미연결 — 을
계속 기준점으로 삼는 것이다.
