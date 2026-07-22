# Continuity Canon

후속편, 콜백, 반복 캐릭터·소품, 시간·위치 상태가 중요한 경우에만 ContinuityAgent의 입력 범위를 좁힌다. 전체 연재를 다시 요약하지 않는다.

## 입력

- 현재 `script.json`
- 현재 화에 등장하는 캐릭터 항목만 추린 `character-bible.json`
- 필요한 스타일 상태만 추린 `visual-style.json`
- 관련 에피소드 ID만 골라 읽은 `episode-history.json`
- 사용자가 명시한 콜백과 변경 금지 사실

## 추출 순서

1. `locked_facts`: 이름, 관계, 이미 확정된 사건처럼 바꿀 수 없는 사실.
2. `current_state`: 현재 위치, 소유한 소품, 감정, 알고 있는 정보.
3. `mutable_state`: 이번 화 안에서 바뀌어도 되는 목표·감정·소품 상태.
4. `open_callbacks`: 이번 화가 회수하기로 한 약속이나 이전 장면의 질문.
5. `panel_corrections`: 충돌이 있는 패널 번호와 가장 작은 수정만 기록.

## 적용 규칙

- 현재 화에 등장하지 않는 인물과 사건은 읽거나 전달하지 않는다.
- 추측을 정전으로 승격하지 않는다. 근거 경로가 없는 내용은 `unknown`으로 남긴다.
- 잠금 사실을 바꾸는 대신 장면, 동선, 대사 중 가장 작은 단위를 수정한다.
- 소품의 생성·이동·소멸과 캐릭터가 아는 정보의 시점을 패널 순서대로 확인한다.
- 결과는 ContinuityAgent의 패널별 수정 입력으로만 쓰며 별도 장편 요약 파일을 만들지 않는다.

## 참고 원칙

- [Narcooo/inkos](https://github.com/Narcooo/inkos): story bible, current focus, truth files를 분리하고 현재 작업에 필요한 문맥만 컴파일하는 원칙.
- [RhythmicWave/NovelForge](https://github.com/RhythmicWave/NovelForge): 지식 그래프와 동적 상태를 다음 생성에 선택적으로 주입하는 원칙.
- [NousResearch/autonovel](https://github.com/NousResearch/autonovel): 세계·인물·목소리·canon을 초안 전에 고정하는 foundation 원칙.

외부 프로젝트의 코드나 프롬프트는 사용하지 않고 정전과 현재 상태를 분리하는 설계만 적용했다.
