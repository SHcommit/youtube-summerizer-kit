# research-engine

> 현재는 **문서 경계만** 존재합니다. 아직 Python 패키지, RAG index, LangGraph, MCP 서버,
> 세션 저장소, 모델 의존성은 없습니다.

## 목적

`research-engine`은 완성된 Knowledge Pack을 바탕으로 후속 질문과 심층 조사를 수행할
미래 실행계입니다. 배포 이름은 `research-engine`, 미래의 Python import 이름은
`research_engine`입니다.

`chew`는 원문을 근거와 함께 Knowledge Pack으로 컴파일하는 **Grounded Knowledge
Compiler**이고, `research-engine`은 그 Pack을 읽어 별도 research session을 쌓는 소비자입니다.

```text
intent-analysis 결과
        ↓
research-engine
  ├─ completed Pack retrieval
  ├─ follow-up question / research session
  ├─ notes and hypotheses
  └─ optional graph orchestration
        ↓
versioned read-only KnowledgeGateway
        ↓
chew — Grounded Knowledge Compiler
```

## 미래 책임

- completed Knowledge Pack 기반 retrieval 및 근거 연결
- 후속 질문, research session, 노트와 가설의 별도 관리
- 필요한 경우에만 LangGraph 기반 orchestration
- `intent-analysis`가 만든 허용된 intent의 소비

대화와 조사에서 생긴 추론·외부 근거·메모는 immutable source-derived Knowledge Pack을
수정하지 않습니다. Pack과 session은 `pack_ref`, `tree_id`, `run_id` 같은 식별자로만 연결합니다.

## 필수 경계

`research-engine`은 미래의 versioned, typed, read-only `KnowledgeGateway`만 통해 `chew`의
완성된 Pack 데이터를 읽습니다. 다음 직접 접근은 허용하지 않습니다.

- `chew` SQLite database와 canonical run/job/artifact schema
- artifact file path, shell, browser session, cookie, Keychain, vendor credential
- transcript provider와 AI harness adapter
- 명시적 승인 없는 외부 write 또는 불확실한 provider 요청의 자동 재전송

## 비범위

- `chew`의 source acquisition, evidence validation, GKT synthesis, Pack persistence, output compilation
- 기본 영상 분석 경로의 RAG, vector DB, LangGraph 추가
- 자연어 자체의 해석 (`intent-analysis`의 책임)
- 현재 CLI, HTTP API, MCP server, web UI 구현

## 다음 구현 전 조건

첫 end-to-end 사용자 흐름을 하나 선택하고, `chew`가 노출할 read-only
`KnowledgeGateway` 계약을 versioned DTO로 정의해야 합니다. 그 뒤에만 retrieval storage,
session persistence, graph runtime, 또는 독립 저장소 추출 여부를 결정합니다. 전체 설계는
[`docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md`](../../docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)를 참고합니다.
