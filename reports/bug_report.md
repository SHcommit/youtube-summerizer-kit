# Bug & Performance Issue Report

이 보고서는 `youtube-summarizer-kit` 서비스 실행 중 발생한 심각한 성능 저하 문제, 아키텍처적 병목, 그리고 비정상적인 디렉토리 검색 동작(보안/프라이버시 우려)을 요약하고 정리한 문서입니다.

---

## 1. 심각한 성능 저하 및 병목 현상 (Performance Bottleneck)

### 현상
* 약 25분 길이의 유튜브 비디오 요약 시, 전체 연산이 30분 이상 지연되거나 정상 범위 내에서 완료되지 못함.

### 원인 분석
1. **과도하게 잘게 쪼개진 세그먼트**:
   * 영상 내용 분석 시 트랜스크립트가 총 30개의 세그먼트(토픽/챕터)로 쪼개져 30개 이상의 독립적인 LLM 요청 태스크가 빌드됨.
2. **`AntigravityHarness`의 낮은 병렬성 제한**:
   * [`src/ytsum/harness/antigravity.py`](file:///Users/yangseunghyeon/Development/youtube-summarizer-kit/src/ytsum/harness/antigravity.py) 내 `maximum_concurrency`가 단 `2`로 고정되어 있음.
   * 이로 인해 30개 세그먼트를 2개씩 순차 배치 처리하므로 15단계 이상의 배치 루프를 돌아야 함.
3. **CLI 실행 파일 구동 오버헤드 (Cold Start)**:
   * 로컬 CLI 도구인 `agy --print`를 실행할 때마다 프로세스가 새로 포크(Fork) 및 인스턴스화됩니다.
   * 하나의 요청당 10~15초 이상 소요되며, 이를 15회 이상 반복 실행하므로 오버헤드가 극단적으로 누적됨.
4. **스케줄러의 상태 감시 및 폴링 주기 지연**:
   * 스케줄러가 SQLite WAL 상태 데이터베이스를 감시하며 작업을 워커에 할당하는 루프 주기와 록(Lock) 획득 대기가 지연을 심화시킴.

---

## 2. 보안 및 프라이버시 문제 (Security & Privacy Intrusion)

### 현상
* 분석 중 `FileNotFoundError` 발생 시, 에이전트가 데이터베이스 경로를 수동으로 찾기 위해 사용자 홈 디렉토리 전체(`Path.home().glob()`)를 탐색함.

### 원인 분석
* **에이전트의 잘못된 오류 복구 로직**:
   * 앱 실행 중에 `user_data_path`가 다르게 해석되어 생긴 파일 경로 문제를 디버깅하기 위해, 에이전트가 시스템 설정을 뒤적이지 않고 하드디스크 전체를 스캔하려는 무리한 파일 찾기 명령을 수행함.
   * 이는 사용자의 파일 시스템 위치 노출 및 프라이버시 침해를 일으키는 매우 부적절한 탐색 방식임.

---

## 3. 최종 합성 단계 (`compose`) 실패 버그

### 현상
* 모든 토픽 및 챕터 요약이 정상 완료되었음에도 불구하고, 마지막 전체 요약본을 취합하는 `compose` 단계에서 `PipelineExecutionError: Knowledge Pack 생성 실패: 1개 작업 실패`를 띄우며 최종 실패함.

### 원인 분석
1. **타입 검증 실패 및 복구(Repair) 루프의 한계**:
   * [`src/ytsum/pipeline/engine.py`](file:///Users/yangseunghyeon/Development/youtube-summarizer-kit/src/ytsum/pipeline/engine.py)의 `_validate_output`에서 `compose` 결과가 `overview` (String) 및 `further_study` (List) 형식을 엄격히 만족하는지 확인하도록 되어 있음.
   * `agy` 로컬 CLI 출력이 불규칙하거나 텍스트 래핑이 섞이면 파싱 에러로 인해 복구(`repair`) 요청이 실행되며, 복구 단계마저 실패하면 최종 Job이 영구 에러 상태가 됨.
2. **실패 캐시의 재사용 오동작**:
   * 특정 Job이 실패로 마킹된 후 에이전트가 재시도를 수행할 때, 데이터베이스에 이전에 성공/실패했던 부분 데이터들이 올바르게 롤백되지 않고 캐시된 채 남아 있어 `0개 작업 실패`인데도 `pack_hash`가 `None`으로 반환되는 비일관성 에러가 발생함.

---

## 4. 아키텍처 개선 및 해결 방향 (Action Items)

- [x] **동적/유연한 세그먼테이션 (Dynamic & Flexible Segmentation) 도입**
  - **개선**: 비디오의 총 재생 시간(Duration)에 비례하여 동적으로 토픽 개수의 상한선을 제한하는 정책을 도입함 (30분 미만 비디오 -> 최대 5개 세그먼트로 자동 합성).

- [ ] **초고속 단일 패스 프로필 (Single-Pass Fast Path Summary) 추가**
  - **개선**: 계층형 분할 분석(Map-Reduce)을 거치지 않고, 비디오 전체 자막을 단 한 번의 LLM 프롬프트 요청으로 요약하는 초고속(`fast` / `simple`) 프로필 추가.
  - 특히 사용자가 로그인한 CLI AI Agent(예: `agy` 등)를 그대로 활용하되, 호출 횟수를 1회로 극축하여 에이전트 인증 세션은 유지하면서 스케줄러 오버헤드 없이 **10~15초 내외로 빠른 응답**을 받도록 최적화.

- [x] **병렬성 증가 (Concurrency Limit Tuning)**
  - **개선**: `AntigravityHarness.maximum_concurrency` 제한을 현재 `2`에서 `8`로 대폭 높여 다수의 요청을 한 번에 동시 처리하도록 개선.

- [x] **에이전트 행동 지침 강제화**
  - **개선**: 파일 시스템 전체 검색(`glob`) 도구를 절대 사용하지 못하도록 AGENTS.md 규칙 8을 신설하고 강제함.

- [x] **취합(Compose) 결과 유연성 및 견고성 확보**
  - **개선**: `overview` 및 `further_study` 형식 검증에 폴백 기법을 추가하여 최종 Knowledge Pack 생성이 실패하지 않도록 보완.

---

## 5. 실수를 반복하지 않기 위한 아키텍처적 교훈 (Lessons Learned)

1. **로컬 CLI와 통신할 때 고주파 요청(Loop) 금지**:
   * 로컬 CLI 도구(예: `agy`, `codex`, `claude` 등)는 독립 프로세스 구동 비용이 매우 크므로 배치(Batch) 모드 또는 단일 호출(Single-pass) 아키텍처를 우선적으로 설계해야 함.
2. **에이전트의 로컬 하드 스캔 제한**:
   * 로컬 파일 시스템 전체를 `glob()`으로 도는 탐색 행위 금지. `platformdirs` 명세를 먼저 체크하고 탐색 전에 사용자에게 직접 경로를 질의함.
3. **데이터베이스 트랜잭션 및 캐시 일관성**:
   * 파이프라인 태스크 재시도 시 이전 캐시와 성공 여부를 온전히 관리할 수 있도록 초기화 로직을 세심하게 처리함.
