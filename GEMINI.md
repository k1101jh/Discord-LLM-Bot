# Discord-LLM-Bot 프로젝트 가이드라인 (GEMINI.md)

이 문서는 Discord-LLM-Bot 프로젝트 진행 시 준수해야 하는 개발 규칙 및 가이드라인을 정의합니다.

---

## 1. 기본 대화 및 작업 원칙
- **언어 설정**: 모든 대답, 문서, 주석, 아티팩트는 **한국어**를 기반으로 작성합니다.
- **변경 사항 확인**: 코드 수정 및 Git 커밋 등의 주요 작업 진행 전에는 사용자 승인을 받아야 합니다.

---

## 2. Python 코딩 및 가이드라인
- **Type Hinting (타입 힌팅)**:
  - 모든 함수 및 클래스 메서드에 정확한 type hint를 지정해야 합니다 (`typing` 모듈 활용).
- **Docstring (독스트링)**:
  - 함수 및 클래스에는 한글 베이스의 docstring을 작성합니다.
  - docstring에는 함수의 역할, 매개변수(`Args`) 타입 및 설명, 반환값(`Returns`) 타입 및 설명이 명확히 포함되어야 합니다.
- **주석 (Comments)**:
  - 코드 내 설명 및 주석은 한글로 작성하며, 복잡한 로직이나 핵심 처리 부분에 명확하게 기술합니다.

- **테스트 작성 (Pytest)**:
  - 새로운 기능 및 주요 모듈 수정 시 `tests/` 디렉토리 내에 `pytest` 기반 단위/통합 테스트를 작성합니다.
  - 비동기 디스코드 봇 및 LLM 호출 테스트 시 `pytest-asyncio` 및 모킹(`unittest.mock` / `pytest-mock`)을 적극 활용합니다.

---

## 3. Git 커밋 및 변경 승인 규칙
- 커밋 전 스테이징 파일 및 커밋 메시지를 사용자에게 보여주고 승인을 얻은 후 작업을 수행합니다.
- **커밋 메시지 컨벤션 (Conventional Commits)**:
  - `feat`: 새로운 기능 추가
  - `fix`: 버그 수정
  - `docs`: 문서 수정 (예: GEMINI.md, README.md 등)
  - `refactor`: 코드 리팩토링 (기능 변화 없음)
  - `style`: 코드 포맷팅, 세미콜론 누락 등 (코드 변경 없음)
  - `test`: 테스트 코드 추가 및 수정
  - `chore`: 빌드 업무 수정, 패키지 매니저 수정 등

---

## 4. 주요 기술 스택 및 환경
- **Language**: Python
- **Environment & Package Manager**: `uv` (빠르고 가벼운 파이썬 패키지 및 가상환경 관리)
- **Configuration Management**: `hydra-core` & `omegaconf` (계층적 봇 설정 및 파라미터 관리)
- **Container**: Docker
- **Database**: 
  - Document DB: MongoDB
  - Vector DB: ChromaDB / Qdrant (RAG 임베딩 및 벡터 검색용, Docker 및 Python 연동 용이)
- **LLM Engine**: Ollama (로컬 실행)
- **Test Framework**: Pytest (`pytest-asyncio` 포함)

---

## 5. 테스트 및 검증 규칙
- 코드 작성 및 수정 완료 후 `pytest`를 통한 기능 검증을 진행합니다.
- `uv` 가상환경 내 테스트 실행 명령:
  ```bash
  uv run pytest
  ```
  또는 `run_test.sh`를 활용합니다.

