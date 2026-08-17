---
# 프로젝트 기본 전역 설정
language: ko                       # 출력 언어 (ko, en 등)
default_profile: digest            # 기본 출력 프로필 (digest, blog, study, obsidian)
depth: detailed                    # 기본 요약 강도: quick (초간단/핵심), detailed (상세), deep (심층/꽉찬)
runtime: auto                      # AI 런타임 (auto, antigravity, codex, claude, gemini, ollama)
whisper_fallback: false            # 자막 미제공 시 로컬 Whisper 음성인식 사용 여부
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
