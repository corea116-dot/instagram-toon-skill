# Instagram Toon Skill · 툰 작업실

Codex에서 한국어 인스타툰을 기획·제작·검수하고, 완성된 에피소드를 모션그래픽으로 각색하는 스킬과 로컬 대시보드입니다. 기본 결과물은 로컬 초안이며 외부 게시는 별도 승인과 계정 연결이 필요합니다.

## 설치

macOS·Apple Silicon의 Codex 환경을 기준으로 합니다. Git, Node.js 24 이상, `uv`, 로그인한 Codex CLI를 준비합니다. 스킬 폴더가 이미 있다면 기존 작업을 보존한 뒤 업데이트하세요.

```sh
git clone https://github.com/corea116-dot/instagram-toon-skill.git ~/.codex/skills/instagram-toon
```

에피소드가 저장될 프로젝트의 `.codex/config.toml`에 이 저장소의 `[agents.toon_*]` 설정을 병합하고, `.codex/agents/toon-*.toml`을 같은 상대 경로로 복사합니다. 기존 프로젝트 설정을 통째로 덮어쓰지 마세요. 새 Codex 세션에서 역할이 등록됐는지 확인합니다.

실제 제작에는 Aside 브라우저, 이미지 생성 도구, 로컬 Qwen TTS와 음악·영상 제작 도구 연결이 필요합니다. 모션 영상의 파일 검사는 FFmpeg/ffprobe를 사용합니다. 참조 이미지·음성 모델·완성 에피소드·개인 실행 데이터는 저장소에 포함하지 않습니다.

## 인스타툰과 모션그래픽

```text
$instagram-toon 주제: 퇴근 후 운동을 미루는 이유
$instagram-toon EP-○○를 모션그래픽으로 만들어줘
```

모션 요청은 기존 에피소드의 원본을 참조해 동작에 맞는 새 소스 이미지를 만들고, 대사·음악·효과음을 넣습니다. 장면·연출 기획은 **GPT-6 Astra low (astra-light)**, 제작은 **GPT-6.1 Sol high**의 별도 에이전트가 맡습니다. 독립 대본·화면 검수와 영상 파일 검사도 거칩니다.

대본·연출은 [확정 연출 기준](references/motion-direction-baseline.md)을 따릅니다. 상황과 행동으로 시작하고, 한 질문에 집중해 답에서 다음 궁금증으로 연결하며, 캐릭터의 다양한 동작·반응과 도입을 회수하는 결말을 설계합니다. 원본 에피소드와 이미지는 보존하고 새 영상은 해당 에피소드의 `motion/` 아래에 저장합니다.

## 대시보드 실행

```sh
cd ~/.codex/skills/instagram-toon/dashboard
npm ci
npm run build
TOON_PROJECT='/에피소드를/저장할/프로젝트' npm start
```

[로컬 작업실](http://localhost:4318)을 열고 처음 사용할 때 비밀번호를 직접 정합니다. `TOON_PROJECT`는 기존 `episodes/`와 프로젝트 에이전트 설정이 있는 폴더를 지정합니다. 생략하면 저장소 루트가 프로젝트입니다.

**모션그래픽 만들기**에서 완료된 에피소드를 선택하거나, 완료 작업·결과물·원본 보기 화면의 버튼으로 바로 시작합니다. 검수된 원본만 사용할 수 있고 이미 진행 중인 영상 작업은 기존 작업으로 연결합니다. 완성 영상은 작업 상세에서 재생·다운로드할 수 있습니다. 휴대폰 접속에는 별도의 개인 네트워크나 HTTPS 연결이 필요합니다.

## 설명서

- [인스타툰 사용설명서](INSTAGRAM-TOON-사용설명서.md)
- [대시보드 사용·설정](dashboard/README.md)
- [모션 제작 절차](references/motion-workflow.md)
- [확정 대본·연출 기준](references/motion-direction-baseline.md)
- [에이전트·모델 배정](references/model-routing.md)

## 개발 검증

```sh
uv run --with pytest --with pillow --with pydantic --with typer python -m pytest tests -q
cd dashboard
npm run build
npm test
```

대시보드 테스트는 임시 원본, 모의 Codex 응답과 테스트용 MP4를 사용합니다. 테스트 통과와 실제 이미지 생성·Qwen 음성·완성 영상 제작은 별도로 확인해야 합니다. UI 확인은 Aside를 사용합니다. 실행 데이터와 로그인 정보는 `dashboard/.data/`에 저장되며 Git에서 제외됩니다.
