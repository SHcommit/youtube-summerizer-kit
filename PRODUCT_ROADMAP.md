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
| Research Engine | 완료된 Knowledge Pack으로 후속 질문·근거 연결·별도 research session 수행 | 첫 user flow와 versioned read-only `KnowledgeGateway` 확정; [`design`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md) 및 [`module boundary`](modules/research-engine/README.md) 검토 | Deferred |
| MCP server | Agent가 분석과 재조립 결과를 tool로 사용 | public API, 권한, 실행 격리 설계 확정 | Deferred |
| REST API and automation | n8n, Zapier, Make 등 자동화 연결 | API 인증, rate limit, 장기 job 운영 모델 확정 | Deferred |
| Scoped DI container | MCP/server/session의 app·run·action 수명과 resource cleanup을 일관되게 관리 | 수동 `ApplicationContainer`로 telemetry injection을 정리하고, 실제 다중 request/session lifecycle이 활성화될 것 | Deferred |

## Reconsideration Rules

- 단발성 영상 요약에는 임베딩이나 RAG를 기본 경로에 넣지 않는다.
- 최종 요약과 주장 판단은 Frontier runtime이 담당한다.
- 각 기능은 실제 사용자 문제, 보안 경계, 유지 비용, 성능 측정이 확인될 때만 승격한다.
- scoped DI container를 재검토할 때는 `dishka`의 async `APP → REQUEST/RUN → ACTION` scope가 수동 조립보다 lifecycle cleanup과 test override를 실제로 단순화하는지 spike로 확인한다. container는 entrypoint에서만 사용하며, core/pipeline code는 service locator에 의존하지 않는다.
