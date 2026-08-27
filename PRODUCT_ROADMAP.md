# Product Roadmap

> 현재 범위 밖의 제품 확장 아이디어를 기록한다. 이 문서는 구현 순서나 출시 약속이 아니다.
> 현재 실행할 성능·신뢰성 개선은 [`IMPROVEMENTS.md`](IMPROVEMENTS.md)에서 관리한다.

## Product Direction

`chew`는 개발자와 AI agent 사용자가 긴 영상의 transcript를 신뢰할 수 있는
Knowledge Pack으로 바꾸는 local-first, BYOK 도구다. 최종 요약과 사용자에게 보이는
판단은 사용자가 선택한 Frontier runtime이 맡는다.

아래 기능은 핵심 분석 경로의 품질, 비용, 운영 안정성이 실측으로 확인된 후에만 별도
spec으로 다시 검토한다.

## Deferred Product Opportunities

| Opportunity | User value | Preconditions for reconsideration | Status |
|---|---|---|---|
| Knowledge Graph and embeddings | 여러 영상의 주제, 인물, 주장 연결 | 반복 분석·재탐색 수요와 저장/검색 비용 근거 | Deferred |
| Notion integration | Knowledge Pack을 Notion database와 page로 발행 | 안정적인 export schema와 실제 사용자 수요 | Deferred |
| Podcast RSS and additional sources | RSS, article, PDF 등 입력 확대 | YouTube workflow 품질과 운영 안정성 확보 | Deferred |
| Public Python API | 스크립트와 내부 도구에서 직접 분석 호출 | CLI API와 결과 schema 안정화 | Deferred |
| Research Engine and Grounded Knowledge Tree Agent runtime | 완료된 Knowledge Pack으로 후속 질문·근거 연결·별도 research session 수행 | 첫 user flow와 versioned read-only `KnowledgeGateway` 확정 후에만 typed Application Service tool, LangGraph optional `agents` extra, MCP, HTTP API, 웹 UI, 모델 의존성을 추가한다. 재개 시 Research·Style·Conversation·Publishing 각 역할의 allowlist, model/step/deadline 예산, 읽기·쓰기 artifact 범위, 승인 조건을 실행 전에 고정한다. 대화 session과 `CompilationRun`/`AgentRun`은 분리하고, graph checkpointer는 canonical SQLite run/job/artifact schema와 분리해 `session_id`/`run_id`/`tree_id`만 연결한다. 수신 여부가 불명확한 provider 요청이나 외부 write는 자동 반복하지 않으며, recursive dispatch와 agent의 DB·파일·credential 직접 접근은 허용하지 않는다. `agents` 패키지의 immutable budget·grant·request/result 계약과 승인 전 tool 실행을 막는 policy, `interfaces`의 protocol-neutral presenter는 이미 구현되어 있다(`CHANGELOG.md` 기록). [`design`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md) 및 [`module boundary`](modules/research-engine/README.md) 검토 | Deferred |
| Natural-language intent parsing (`intent-analysis`) | 자연어 요청을 결정적 URL·옵션 추출을 보조하는 허용된 Intent/Clarification/Unsupported로 해석 | 첫 user flow와 capability catalog 확정. 기본 경로는 결정적 URL·옵션 추출과 고신뢰 패턴이며, opt-in local adapter는 schema-validated intent 후보만 반환한다. 입력 해석기는 YouTube 접근, 브라우저·쿠키·Keychain 접근, 파일 삭제, 도구 실행, Frontier 요약·판단을 수행하지 않는다. 데이터 변경 명령은 자연어 해석 후에도 명시적 확인이 필요하다. [`module boundary`](modules/intent-analysis/README.md) 검토 | Deferred |
| MCP server | Agent가 분석과 재조립 결과를 tool로 사용 | public API, 권한, 실행 격리 설계 확정 | Deferred |
| REST API and automation | n8n, Zapier, Make 등 자동화 연결 | API 인증, rate limit, 장기 job 운영 모델 확정 | Deferred |
| Scoped DI container | MCP/server/session의 app·run·action 수명과 resource cleanup을 일관되게 관리 | 수동 `ApplicationContainer`로 telemetry injection을 정리하고, 실제 다중 request/session lifecycle이 활성화될 것 | Deferred |
| `chew diagnostics export --run <run_id>` | 사용자가 이슈를 리포트할 때 재현에 필요한 정보(`RunManifest`, redacted config, execution plan, checkpoint 요약, runtime/model, 에러 종류, artifact hash 목록)를 민감정보 제거된 zip/JSON 하나로 제공 | 실제 사용자 이슈 리포트 사례 발생(재료는 이미 있음 — `RunManifest`(ADR-003), `compiler_checkpoints` 테이블) | Deferred |

## Reconsideration Rules

- 단발성 영상 요약에는 임베딩이나 RAG를 기본 경로에 넣지 않는다.
- 최종 요약과 주장 판단은 Frontier runtime이 담당한다.
- 각 기능은 실제 사용자 문제, 보안 경계, 유지 비용, 성능 측정이 확인될 때만 승격한다.
- scoped DI container를 재검토할 때는 `dishka`의 async `APP → REQUEST/RUN → ACTION` scope가 수동 조립보다 lifecycle cleanup과 test override를 실제로 단순화하는지 spike로 확인한다. container는 entrypoint에서만 사용하며, core/pipeline code는 service locator에 의존하지 않는다.
