# intent-analysis

> 현재는 **문서 경계만** 존재합니다. 아직 Python 패키지, 의존성, 모델 다운로드, CLI, MCP 서버는 없습니다.

## 목적

`intent-analysis`는 여러 제품이 공유할 수 있는 자연어 요청 분석 모듈입니다. 배포 이름은
`intent-analysis`, 미래의 Python import 이름은 `intent_analysis`이며, 단일 진입점은
`IntentParser`로 둡니다.

이 모듈은 사용자의 문장을 실행 가능한 제품 의도로 바꾸거나, 정보가 부족할 때 안전하게
되묻습니다. 실제 도구·모델·외부 시스템을 실행하지 않습니다.

```text
자연어 Message + 선택적 대화 Context + Capability catalog
                          ↓
                     IntentParser
                          ↓
Intent | Clarification | Unsupported
```

## 미래 계약

- 입력: transport-neutral `Message`, 선택적 `Context`, 제품이 제공하는 `Capability` 목록
- 성공: 허용된 capability와 인자만 담은 typed `Intent`
- 불명확: 실행하지 않고 `Clarification`
- 미지원: 실행하지 않고 `Unsupported`

명시 CLI는 이 모듈을 우회합니다. 예를 들어 `chew summarize <URL>`은 이미 구조화된
명령이므로 `IntentParser`가 다시 해석하지 않습니다. 자연어 CLI, 웹 채팅, MCP 같은
입구만 이 모듈을 선택적으로 호출할 수 있습니다.

## 기본 및 확장 전략

처음에는 모델 다운로드 없이 URL·파일·명시 옵션 추출과 고신뢰 한국어·영어 패턴만 사용합니다.
모호한 요청은 추측하지 않고 되묻습니다.

나중에 필요성과 평가셋이 확인될 때만 다음 어댑터를 opt-in으로 검토합니다.

- 작은 ONNX intent classifier
- 사용자가 이미 설치한 Ollama 모델

어떤 모델도 등록되지 않은 intent·인자를 만들어 실행할 수 없습니다. 출력은 schema 검증을
통과한 intent 후보일 뿐이며, 낮은 신뢰도·검증 실패는 `Clarification`으로 끝납니다.

## 비범위

이 모듈은 다음을 소유하거나 의존하지 않습니다.

- RAG, vector DB, LangGraph, research session
- MCP, HTTP, 웹 UI, CLI 구현
- 도구 실행, 파일 변경, 외부 write, 승인 판단
- SQLite, artifact path, shell, browser/cookie/Keychain, vendor credential
- `chew` 또는 다른 제품의 도메인 API

## 다음 구현 전 조건

첫 사용자 흐름과 capability catalog를 확정한 뒤, 별도 Python package로 만들지 또는
다른 저장소로 추출할지를 결정합니다. 설계 기준은
[`docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md`](../../docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)를 참고합니다.
