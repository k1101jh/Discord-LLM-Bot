# 공식 uv 파이썬 3.12 슬림 이미지 사용
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV TZ=Asia/Seoul
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 패키지 명세 파일 복사 및 설치 (docker 캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 프로젝트 전체 소스 코드 복사 및 동기화
COPY . .
RUN uv sync --frozen

# 실행 권한 부여
RUN chmod +x scripts/start.sh

CMD ["uv", "run", "bash", "scripts/start.sh"]