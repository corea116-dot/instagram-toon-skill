# Dialogue Persona

화자가 두 명 이상이거나 캐릭터 말투가 충돌할 때만 WriterAgent와 DialogueNaturalnessAgent 사이에 짧은 화자 카드를 제공한다. 일반 문장 다듬기는 기존 `dialogue-naturalness.md`가 담당한다.

## 입력

- 말하는 캐릭터의 bible 항목
- `memory/dialogue-style.md`
- StoryCritic을 통과한 현재 대사
- 사용자가 지정한 말투, 호칭, 금지 표현

## 화자 카드

각 화자마다 다음 네 항목만 만든다.

- `scene_intent`: 이 장면에서 얻으려는 것 한 가지.
- `voice_anchors`: 문장 길이, 어미, 반응 속도 등 관찰 가능한 특징 최대 세 가지.
- `avoid`: 캐릭터답지 않은 설명체·호칭·유행어 최대 세 가지.
- `short_alternatives`: 의미를 보존한 짧은 대사 대안 최대 두 개.

## 보존 규칙

- 화자, 말풍선 수, 말풍선 좌표, 사실, 숫자, 시간, 고유명사를 바꾸지 않는다.
- 장면의 유머 엔진, 비트, 반전, 정보 공개 시점을 바꾸지 않는다.
- 보이는 행동을 대사로 다시 설명하지 않는다.
- 모든 화자를 같은 인터넷 말투나 같은 존댓말 강도로 평준화하지 않는다.
- 안전하게 바꿀 수 있는 문구만 한 차례 적용하고, 의미가 달라지면 StoryCritic 재검토를 요청한다.

## 참고 원칙

- [SillyTavern/SillyTavern](https://github.com/SillyTavern/SillyTavern): 캐릭터 카드, 페르소나, lorebook을 분리해 대화 문맥에 선택적으로 넣는 원칙.

SillyTavern을 설치하거나 캐릭터 카드 형식을 복제하지 않았으며, 화자별 의도와 목소리를 분리하는 원칙만 사용했다.
