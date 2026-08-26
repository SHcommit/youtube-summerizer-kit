# Contributing

Python 3.12 이상에서 개발합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[youtube,dev]'
ruff check .
mypy src/chew
pytest -q
```

## External Contribution & Git Workflow

We follow the Gitflow workflow. If you wish to contribute:

1. **Fork & Branch**: Fork this repository and create a topic branch (`feature/123-your-feature`, `fix/123-your-bugfix`, `docs/123-topic`, `refactor/123-topic`, `bench/123-topic`, `ci/123-topic`, or `spike/topic`).
2. **Pull Request Target**: Submit your Pull Request targeting the **`develop`** branch, not `master`.
3. **Verification**: Ensure all tests pass (`uv run --extra dev pytest`, `ruff check .`, `mypy src/chew`).
4. **Changelog**: Add a summary of your changes to `CHANGELOG.md` under `## [Unreleased]`.

Release branches use `release/vX.Y.Z` and target `master` after `develop` has been verified.

## Testing and Verification Guidelines

기능과 버그 수정은 실패하는 테스트를 먼저 추가한 뒤 최소 구현으로 통과시키세요. 기본 테스트는
네트워크, 로그인 계정, 유료 API에 의존하면 안 됩니다. 외부 CLI 출력은 기록된 fixture로 계약을
검증하고 비밀값, 전체 자막, 사용자 경로를 커밋하지 않습니다.

라이브 확인은 명시적으로만 실행합니다.

```bash
CHEW_LIVE_YOUTUBE_URL='https://youtu.be/...' pytest tests/live/test_youtube_transcript.py
CHEW_LIVE_HARNESS=codex pytest tests/live/test_harnesses.py
```

릴리스 전에는 `uv run python scripts/check_release_consistency.py --tag vX.Y.Z`로
`pyproject.toml`, tag, release branch, `CHANGELOG.md` heading의 버전 일치를 확인합니다.
그 뒤 wheel과 sdist를 만든 뒤 깨끗한 가상환경에 wheel을 설치하여 `chew --help`,
`chew 진단 --json`을 확인합니다. 라이브 벤치마크 결과에는 실행기·모델·입력 방식·프롬프트
fingerprint·시간을 기록하고 각 조건을 같은 횟수로 반복해야 합니다.
