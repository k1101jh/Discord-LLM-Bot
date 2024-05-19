# Discord LLM Bot
 ---------------------------------------------

LLM api와 연동해서 Discord 챗봇을 실행하는 프로그램입니다.

## 사용 방법
채팅 채널에 글을 작성해서 대화를 시작합니다.


## 명령어
|명령어(/)|기능|
|---|---|
|help|사용 가능한 명령어 출력|
|prompt|현재 프롬프트 출력|
|set_prompt prompt|프롬프트 설정|
|new_chat|새로운 채팅 시작|
|toggle_chat|현재 채널에서 채팅 기능 켜기/끄기|
|test|"test" 출력|

## 사용 가능 API

* https://github.com/oobabooga/text-generation-webui
* openai(테스트 필요)

## 설치 방법

1) 리포지토리 복제
2) bot 생성  
2.1 [discord dev potal](https://discord.com/developers/docs/intro)에서 bot 생성  
2.2 OAuth2 탭의 OAuth2 URL Generator 항목에서 "bot", "appllications.commands" 항목 체크  
2.3 BOT PERMISSIONS 항목에서 Administrator 항목 체크  
2.4 GENERATED URL을 주소창에 붙여넣어 채팅방에 bot 초대  
3) [Text generation web UI](https://github.com/oobabooga/text-generation-webui) 복제  
3.1 CMD_FLAGS.txt 파일을 열어서 하단에 다음 명령어 추가  
```--extensions openai```  
3.2 web ui 실행  
3.3 model 불러오기  
4) .env 파일 수정
   - APP_ID, TOKEN, PUBLILC_KEY:  
   [discord dev potal](https://discord.com/developers/docs/intro)에서 봇을 선택하고 해당 항목을 찾아서 .env 파일에 입력
   - OPENAI_API_BASE, OPENAI_API_KEY:  
   openai 사용시: ```https://api.openai.com/v1```, ```<YOUR_API_KEY>```  
   Text generation web UI 사용 시: ```http://host.docker.interanl:5000/v1```, ```EMPTY```
5) docker-compose 수행  
``` docker-compose -f ./docker/docker-compose.yml up  ```


## To Do
 - [ ] !help 명령어 입력 시 Cog에 등록된 commands도 나오도록 수정하기
 - [ ] 채널마다 prompt 저장하기
 - [ ] ollama 추가
 - [ ] 특정 채널에서만 챗봇과 대화할 수 있도록 수정하기
 - [ ] tts 기능 추가하기
 - [ ] chat마다 이름 붙일 수 있도록 하기(modal dialog 사용해서)
 - [ ] ai 이름 지정하기
   - 모델의 instruction template 또는 chat template를 불러오기


참고:
 - https://www.gigo.dev/challenge/1688591240871804928