# Discord LLM Bot 🤖

로컬 **Ollama (`gemma4:26b`)**, **MongoDB**, **RAG (Retrieval-Augmented Generation)** 기반의 디스코드 챗봇 프로젝트입니다.  
디스코드 채널 및 스레드에서 대화 맥락을 유지하는 연속 대화 기능과 문서 기반 검색 질의응답 기능을 제공합니다.

---

## 🛠️ 주요 기술 스택

- **Language & Runtime**: Python 3.12, `uv` (빠른 패키지 & 가상환경 관리)
- **Configuration Management**: `hydra-core` & `omegaconf`
- **Bot Framework**: `py-cord` (Cog 구조화 패턴 적용)
- **LLM Engine**: Ollama (로컬 실행, 메인 모델: `gemma4:26b`)
- **Database**:
  - **Document DB**: MongoDB (채팅 세션 & 대화 이력 관리)
  - **Database GUI**: Mongo Express (웹 대시보드)
  - **Vector DB**: ChromaDB / Qdrant (RAG 임베딩 인덱스)
- **Container**: Docker & Docker Compose
- **Test Framework**: Pytest (`pytest-asyncio`, `mongomock` 단위 테스트)

---

## 🚀 빠른 시작 (Quick Start)

### 1. 사전 준비 (Prerequisites)

1. **Discord 개발자 포털 설정**:
   - [Discord Developer Portal](https://discord.com/developers/applications)에서 신규 앱 및 봇 생성 후 **Bot Token** 발급.
   - **Privileged Gateway Intents** 설정에서 **Message Content Intent**, **Server Members Intent** 활성화.
   - `OAuth2 URL Generator`를 통해 `bot`, `applications.commands` 권한을 선택하여 디스코드 서버에 봇 초대.

2. **로컬 Ollama 구동 및 모델 다운로드**:
   - 로컬 호스트 PC에서 Ollama 실행 (`OLLAMA_HOST=0.0.0.0`)
   - 모델 다운로드:
     ```bash
     ollama pull gemma4:26b
     ollama pull bge-m3
     ```

3. **환경 변수 파일 (`.env`) 설정**:
   프로젝트 루트에 `.env` 파일(또는 `.env copy` 참조)을 생성하고 다음 항목을 입력합니다.
   ```env
   APP_ID=YOUR_DISCORD_APP_ID
   DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
   PUBLIC_KEY=YOUR_DISCORD_PUBLIC_KEY
   LLM_PROVIDER=openai

   # Ollama API 설정 (기본 포트: 11434)
   OPENAI_API_BASE=http://host.docker.internal:11434/v1
   OPENAI_API_KEY=ollama
   OLLAMA_MODEL=gemma4:26b

   # MongoDB 인증 설정
   MONGO_INITDB_ROOT_USERNAME=root
   MONGO_INITDB_ROOT_PASSWORD=examplepassword
   DATABASE_NAME=discord_chat_bot
   MONGO_URI=mongodb://root:examplepassword@mongodb:27017/discord_chat_bot?authSource=admin

   # Mongo Express 웹 UI 설정 (http://localhost:8081)
   MONGO_EXPRESS_USER=admin
   MONGO_EXPRESS_PASSWORD=pass
   ```

---

### 2. 실행 방법 (How to Run)

#### 방법 A: Docker Compose 서비스 구동 (추천 ⭐)

MongoDB, Mongo Express, Discord Bot 전체 컨테이너를 한 번에 구동합니다.

- **Windows 실행**:
  `scripts/docker_run.bat` 더블 클릭 또는 실행
- **Linux/Mac/Terminal 실행**:
  ```bash
  docker compose -f docker/docker-compose.yml up --build -d
  ```

- **상태 확인**:
  ```bash
  bash scripts/docker_status.sh
  # 또는 Windows: scripts/docker_status.bat
  ```

#### 방법 B: 로컬 개발 환경 직접 실행 (`uv` 기반)

1. `uv` 가상환경 및 패키지 동기화:
   ```bash
   uv sync
   ```
2. 봇 구동:
   ```bash
   uv run python src/run.py
   # 또는
   bash scripts/start.sh
   ```

---

### 3. 데이터베이스 및 GUI 관리 (Mongo Express)

Docker 환경 실행 시 웹 브라우저에서 MongoDB 대화 히스토리 및 컬렉션 데이터를 시각적으로 확인할 수 있습니다.

- **URL**: `http://localhost:8081`
- **로그인 ID**: `admin` (또는 `.env` 설정값)
- **비밀번호**: `pass` (또는 `.env` 설정값)

---

### 4. 서버 및 서비스 종료 방법 (How to Stop)

- **Docker Compose 서비스 정지**:
  - **Windows**: `scripts/docker_stop.bat` 실행
  - **Linux/Mac/Terminal**:
    ```bash
    bash scripts/docker_stop.sh
    # 또는
    docker compose -f docker/docker-compose.yml down
    ```


- **Docker 데이터까지 완전 삭제 후 초기화 시**:
  ```bash
  docker compose -f docker/docker-compose.yml down -v
  ```

---

### 5. 테스트 수행 (Testing)

`mongomock`을 기반으로 외부 서버 연동 없이 단위 테스트를 0.5초 내에 수행합니다.

```bash
uv run pytest
# 또는
bash scripts/run_test.sh
```

---

## 📜 주요 디스코드 슬래시 명령어 (`/llm`)

| 명령어 | 설명 |
| :--- | :--- |
| `/llm prompt` | 현재 채널 세션의 시스템 프롬프트를 출력합니다. |
| `/llm set_prompt <prompt>` | 채널의 시스템 프롬프트를 변경하고 새 세션을 시작합니다. |
| `/llm toggle_chat` | 현재 채널의 챗봇 자동 응답 기능을 ON/OFF 토글합니다. |
| `/llm regenerate` | 마지막 AI 답변을 삭제하고 LLM 응답을 다시 생성합니다. |
| `/llm delete_last_message` | 마지막 질문과 답변 메시지 쌍을 세션 이력에서 삭제합니다. |
| `/llm new_chat` | 현재 채널의 대화 이력을 초기화하고 새 대화를 시작합니다. |
| `/llm history` | 대화 기록을 Paginator 버튼 페이지 형태로 조회합니다. |

---

## 📁 주요 디렉토리 구조

```text
Discord-LLM-Bot/
├── GEMINI.md                  # 파이썬 코딩 및 Git 커밋 가이드라인
├── README.md                  # 프로젝트 안내 및 실행 문서
├── pyproject.toml             # uv 및 pytest 프로젝트 설정
├── docs/
│   └── architecture_plan.md   # Ollama 모델 및 RAG 시스템 아키텍처 설계
├── docker/
│   ├── Dockerfile             # ghcr.io/astral-sh/uv 기반 Dockerfile
│   └── docker-compose.yml     # Bot, MongoDB, Mongo Express 오케스트레이션
├── scripts/
│   ├── start.sh               # 로컬 봇 실행 스크립트
│   ├── run_test.sh            # Pytest 실행 스크립트
│   ├── docker_run.sh          # Linux/Mac Docker 구동 스크립트
│   ├── docker_stop.sh         # Linux/Mac Docker 정지 스크립트
│   ├── docker_status.sh       # Linux/Mac Docker 상태 확인 스크립트
│   ├── docker_run.bat         # Windows Docker 구동 스크립트
│   ├── docker_stop.bat        # Windows Docker 정지 스크립트
│   └── docker_status.bat      # Windows Docker 상태 확인 스크립트

├── src/
│   ├── run.py                 # 메인 엔트리포인트
│   ├── constants.py           # 기본 프롬프트 및 LLM 파라미터
│   ├── help_command.py        # 커스텀 도움말 핸들러
│   ├── cogs/                  # Discord Bot Cog 모듈
│   ├── database/              # MongoDB 대화 이력 핸들러
│   ├── llm/                   # Ollama / OpenAI API 연동 모듈
│   └── util/                  # 타임스탬프 로거 및 유틸리티
├── tests/                     # Pytest 단위 테스트
└── logs/                      # 실행 시간별 타임스탬프 로그 파일 저장소
```