---
applyTo: "**/*.py"
---

# Python 코드 컨벤션

## 환경 / 실행

- **Python 3.14.x** 사용(실습 검증 버전; MAF 공식 최소 요구는 3.10).
- 프로젝트 루트에서 가상환경을 만들고 의존성을 설치한다:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate      # macOS/Linux (Windows: .venv\Scripts\Activate.ps1)
  pip install -r requirements.txt
  ```
- `.venv/`는 `.gitignore`로 버전 관리에서 제외한다.

## 의존성

- 의존성은 루트 `requirements.txt`에 명시하고, 패키지를 추가하면 갱신한다.
- 메타 패키지 `agent-framework`(foundry·orchestrations 포함)를 사용한다.
- 검증된 SDK 조합은 `==x.y.z`로 고정한다. 프리릴리스 연동 패키지도 정확한 빌드를 고정하고,
  관련 핵심 패키지는 호환 버전으로 함께 갱신한다.

## 코드 스타일

- 모듈 최상단에 한국어 모듈 docstring을 둔다.
- 함수는 Google 스타일 한국어 docstring(설명/Args/Returns; 자명한 헬퍼는 생략 가능)을 작성한다.
- 타입 힌트를 적극 활용한다.
- import 순서: 표준 라이브러리 → 서드파티 → 로컬(그룹 사이 빈 줄).
- 비동기 호출(`async/await`)·진입점(`asyncio.run(main())`)·`load_dotenv()` 규칙은 `copilot-instructions.md`「핵심 제약」을 따른다.
