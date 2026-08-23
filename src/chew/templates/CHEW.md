---
# 프로젝트 기본 전역 설정
language: ko                       # 출력 언어 (ko, en 등)
default_profile: digest            # 기본 출력 프로필 (digest, blog, study, obsidian)
depth: detailed                    # 기본 요약 강도: quick (초간단/핵심), detailed (상세), deep (심층/꽉찬)
runtime: frontier                  # 기본: BYOK Frontier (codex, claude, gemini)
task_runtimes: {}                  # 선택: task별 BYOK Frontier runtime 지정 (예: {topic_summary: gemini, compose: codex})
local_accelerator: false           # 향후 저위험 보조 작업을 위한 opt-in 의도; 요약·판단 작업에는 사용하지 않음
ollama_model: null                 # 향후 허용된 로컬 보조 작업에 사용할 모델 (예: qwen3:4b)
whisper_fallback: false            # 자막 미제공 시 로컬 Whisper 음성인식 사용 여부
youtube_cookie_file: null          # 고급 설정: 사용자가 지정한 YouTube 전용 Netscape cookies.txt 경로; `chew auth youtube`가 기본 복구 경로
max_input_tokens: null             # 선택: 요약 입력의 보수적 token 상한
reserved_output_tokens: 0          # 선택: 모델 응답에 남겨둘 token 예산
output_verify: true                # blog/study 생성 결과 검증 호출 여부
normalize_transcript: false        # 선택: 공백 정리·인접 중복 자막 병합
preprocess_transcript: false       # 선택: 보수적 필러 제거와 설치된 전처리 전략 적용
storage_policy: compact            # 저장소 정책 (compact, private, archive)
---

# 프로젝트 공통 작성 지침 (LLM Prompt)

<!-- 
[사용자 가이드]
이곳에 원하는 작성 지침을 자유롭게 추가하세요.
AI가 영상 요약 시 아래 지침을 최우선으로 반영합니다.

예시:
- 영상에서 확인되는 순수 사실과 AI의 추가 설명을 엄격히 구분한다.
- 중요한 모든 기술적 주장에는 [MM:SS] 타임스탬프 근거를 연결한다.
- 어려운 전문 용어는 첫 등장 시 한 줄로 명확하게 정의한다.
-->

영상에서 확인되는 내용과 AI의 추가 설명을 구분하고, 중요한 주장에는 타임스탬프 근거를 연결합니다.
