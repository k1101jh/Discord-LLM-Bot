FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=Asia/Seoul

WORKDIR /usr/src/app

# RUN apt-get update && apt-get upgrade -y && \
#     apt-get install -y python3 python3-pip gcc wget

COPY requirements.txt ./
COPY .env ./
COPY start.sh ./

RUN pip install --no-cache-dir -r requirements.txt
RUN chmod -R 777 start.sh

CMD ["bash", "start.sh"]