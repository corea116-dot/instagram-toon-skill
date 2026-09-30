# Storyboard Shot Plan

StoryCritic과 DialogueNaturalnessAgent를 통과한 레이아웃 기반 비트를 ArtDirectorAgent가 그릴 수 있는 사건과 카메라 계획으로 바꾼다. 스토리를 다시 쓰거나 이미지를 직접 생성하지 않는다.

## 입력

정보형은 StoryCritic/DialogueNaturalness 대신 최신 통합 ContentReview를 통과한 대본을 받는다. 마지막 컷의 역할은 질문에 대한 답 또는 다음 확인 행동이며 반전을 강제하지 않는다.

- 승인된 `script.json`
- `visual-rules.md`
- 현재 화에 필요한 캐릭터·스타일 reference 경로
- continuity-canon 결과가 있을 때 그 잠금 상태

## 패널별 변환

각 패널에 다음 항목을 확정한다.

- 한눈에 보이는 사건 한 가지
- 캐릭터의 그릴 수 있는 행동과 표정
- 실제 출연자와 서로의 위치·시선·행동 관계
- 시작 상태와 끝 상태가 분명한 핵심 소품, 상황을 이해시키는 공간 요소
- 이전 패널과 이어지는 배경·시간·위치
- 감정과 정보 공개에 맞는 카메라 거리와 각도
- 기존 대사를 가리지 않는 말풍선 안전영역

## 레이아웃 기반 점검

- 패널 1: 모바일 피드에서 즉시 읽히는 단일 초점과 질문.
- 내부 패널: 직전 패널과 구별되는 상태 변화, 행동, 또는 정보를 한 가지씩 보인다.
- 마지막 패널: 유머는 payoff, 정보형은 질문의 답과 다음 확인 행동을 보여주는 최종 상태.

## 경계

- raw 이미지에는 글자, 숫자, 말풍선, 자막, 로고, 워터마크를 넣지 않는다.
- `prompts/panel-N.json -> raw/panel-N.png` 공급자 경계를 유지한다.
- primary reference image 순서와 1080×1350을 유지하며 배경·조연·소품은 `visual-rules.md`의 Scene policy를 따른다. 단색 배경이나 고정 소품 수를 별도로 강제하지 않는다.
- 스토리가 바뀌지 않은 단일 패널 재생성에서는 이 모듈을 다시 읽지 않는다.

## 참고 원칙

- [HBAI-Ltd/Toonflow-app](https://github.com/HBAI-Ltd/Toonflow-app): 사건 그래프에서 스크립트와 분镜 단계로 내려가는 제작 원칙.
- [LingyiChen-AI/AIComicBuilder](https://github.com/LingyiChen-AI/AIComicBuilder): 대본 분석, 캐릭터 추출, 스마트 스토리보드, 프레임 생성의 단계 분리 원칙.
- [ArcReel/ArcReel](https://github.com/ArcReel/ArcReel): screenplay부터 이미지·영상까지 공급자 경계와 단계별 작업을 분리하는 원칙.

외부 코드, 워크플로 정의, 프롬프트는 복제하지 않았으며 사건을 촬영 가능한 샷으로 바꾸는 경계만 적용했다.
