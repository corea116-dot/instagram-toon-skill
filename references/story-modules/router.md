# Story Module Router

이 라우터는 `instagram-toon` 내부의 작은 참고 모듈만 조건부로 선택한다. 외부 저장소를 설치하거나 실행하지 않는다.

## 모듈 ID

| ID | 담당 |
| --- | --- |
| `story-architecture` | 로그라인부터 6비트 인과 구조까지 정리 |
| `continuity-canon` | 이번 화에 필요한 정전과 상태만 추출 |
| `dialogue-persona` | 다화자 의도와 말투 충돌 정리 |
| `branch-payoff-lab` | 실패한 인과·반전의 대안 비교 |
| `storyboard-shot-plan` | 승인된 6비트를 촬영 가능한 콘티로 변환 |

## 라우팅 순서

1. 실행 모드를 정한다: `new_episode`, `story_rewrite`, `panel_regeneration`, `recompose`, `validate`.
2. 요청에서 정확한 모듈 ID와 함께 “꼭 사용”, “활성화”, `enable`로 표현한 항목을 `overrides.enable`에 넣는다.
3. “사용하지 마”, “제외”, “비활성화”, `disable`로 표현한 항목을 `overrides.disable`에 넣는다. 같은 ID가 양쪽에 있으면 비활성화가 이긴다.
4. 아래 자동 신호를 적용한다.
5. 예산을 확인하고 다섯 모듈 모두를 `active` 또는 `skipped`로 기록한다.
6. `active` 모듈 파일만 읽는다. 같은 초안 패스에서는 다시 읽지 않는다.

`recompose`와 `validate`, 스토리가 바뀌지 않은 `panel_regeneration`은 항상 모듈을 0개 읽는다. 이 모드에서 강제 활성화가 들어와도 `mode_has_no_story_work`로 생략한다. StoryCritic, 안전 검사, 언어 정책, 결정적 검증은 스토리 모듈이 아니므로 사용자가 끌 수 없다.

## 자동 신호

| 조건 | 자동 활성화 |
| --- | --- |
| 새 에피소드 | `story-architecture`, `storyboard-shot-plan` |
| 스토리 재작성 | `story-architecture`; 스토리가 바뀌면 `storyboard-shot-plan` |
| 후속편, 콜백, 반복 소품·상태, 이전 화 참조 | `continuity-canon` |
| 대사 화자 2명 이상 또는 명시적 보이스 충돌 | `dialogue-persona` |
| StoryCritic 실패가 `mechanism`, `beats`, `payoff`, `duplicate` | `branch-payoff-lab` |

## 예산

- 기본 새 에피소드는 라우터를 포함해 참고 문서 3개만 읽는다.
- `continuity-canon`과 `dialogue-persona`는 합계 최대 2개다.
- `branch-payoff-lab`은 한 에피소드 시도에서 최대 1회다.
- 기존 스크립트 재작성 상한은 총 2회이며 모듈 때문에 늘어나지 않는다.
- 같은 패스에서 이미 읽은 모듈은 결과만 다음 역할에 전달한다.

## 기록

새 정책으로 만드는 에피소드는 `brief.json`에 다음 값을 넣는다.

```json
"story_module_policy": "auto_with_overrides"
```

IdeaAgent 전에 `module-routing.json`을 작성하고 `scripts/story_module_models.py`의 `StoryModuleRoutingModel`로 검증한다. 기록에는 정책, 모드, 원래 오버라이드, 다섯 모듈의 상태·이유·실행 횟수, 예산만 둔다. 창작 본문, 프롬프트 전문, 내부 추론은 복제하지 않는다.

허용되는 이유 코드는 `new_episode`, `story_rewrite`, `story_changed`, `serial_signal`, `multi_speaker`, `story_critic_<failure>`, `user_enabled`, `user_disabled`, `mode_has_no_story_work`, `no_signal`이다.
