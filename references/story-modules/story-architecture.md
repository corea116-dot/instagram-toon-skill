# Story Architecture

새 에피소드와 스토리 재작성에서 IdeaAgent와 WriterAgent가 공유할 최소 인과 구조를 만든다. 기존 `RichDirectionModel`과 6컷 계약을 그대로 사용하며 별도 스토리 스키마를 만들지 않는다.

## 입력

- 확정된 주제, 독자, 톤, 등장인물
- `story-rules.md`의 하드 게이트
- 중복 확인에 필요한 에피소드 이력
- 사용자가 고정한 사건, 결말, 금지 요소

## 작업

1. 한 문장 로그라인으로 주인공의 즉시 목표와 방해를 고정한다.
2. 독자가 아는 `human_truth`와 인물이 반대로 행동하는 `behavioral_contradiction`을 분리한다.
3. 하나의 주 유머 엔진을 고르고, 매 비트가 같은 엔진을 다른 상태로 밀어 올리게 한다.
4. 오프닝이 남기는 구체적 질문을 `hook_promise`로 쓴다.
5. 서로 다른 네 개의 보이는 상태 변화를 원인 → 반응 → 악화 → 전환 순서로 만든다.
6. 결말이 오프닝을 새롭게 읽게 하는 `payoff_reversal`을 고정한다.
7. 위 결과를 기존 `RichDirectionModel` 필드에만 넣고 StoryCritic premise mode로 넘긴다.

## 출력 제한

- 완성 대사나 패널 프롬프트를 쓰지 않는다.
- 네 변화는 표현만 다른 동일 행동이 아니어야 한다.
- 결말을 정한 뒤 앞부분을 억지로 맞추지 말고, 오프닝부터 인과 씨앗을 심는다.
- 6컷의 opening 1, development 4, ending 1 순서를 바꾸지 않는다.

## 참고 원칙

- [google-deepmind/dramatron](https://github.com/google-deepmind/dramatron): 로그라인에서 인물·장소·플롯·대사로 내려가는 계층형 생성 원칙.
- [RhythmicWave/NovelForge](https://github.com/RhythmicWave/NovelForge): 구조화 카드와 스키마 기반 생성, 상위 개요에서 세부 카드로 내려가는 원칙.

코드, 프롬프트, 데이터는 가져오지 않았으며 위 구조 원칙만 인스타툰 6비트에 맞게 재서술했다.
