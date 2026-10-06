import { MotionModal } from "./MotionModal";
import { motionUnavailable } from "../shared/motion";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Bell,
  CalendarClock,
  Check,
  ChevronRight,
  CircleAlert,
  CirclePlay,
  Clock,
  ExternalLink,
  Feather,
  Film,
  FolderHeart,
  GitBranch,
  House,
  Instagram,
  Link,
  LoaderCircle,
  LogOut,
  Menu,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
  WifiOff,
  X,
} from "lucide-react";
import type {
  Snapshot,
  Options,
  Run,
  Episode,
  Schedule,
  PendingRequest,
} from "../shared/types";
import { api, imageUrl, dateText } from "./api";
import { Badge, Modal, OptionsFields, Toggle } from "./components";
import { WorkflowEditor } from "./WorkflowEditor";
import { Viewer } from "./Viewer";

const sections = [
  { id: "home", label: "작업실", icon: House },
  { id: "library", label: "결과 모아보기", icon: FolderHeart },
  { id: "workflow", label: "작업 흐름", icon: GitBranch },
  { id: "schedules", label: "예약", icon: CalendarClock },
  { id: "settings", label: "연결과 알림", icon: Settings2 },
] as const;
type Page = (typeof sections)[number]["id"];

function Login({ setup, onDone }: { setup: boolean; onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <main className="login-page">
      <div className="login-art">
        <span className="logo-mark">
          <Feather size={28} />
        </span>
        <p className="eyebrow">나의 인스타툰 제작 공간</p>
        <h1>
          아이디어부터
          <br />
          게시까지,
          <br />
          <em>한곳에서.</em>
        </h1>
        <div className="login-route">
          <span>대본</span>
          <ArrowRight size={16} />
          <span>그림</span>
          <ArrowRight size={16} />
          <span>게시</span>
        </div>
      </div>
      <form
        className="login-card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            if (setup && password !== repeat)
              throw new Error("두 비밀번호가 같아야 해요.");
            await api(setup ? "/setup" : "/login", { password });
            onDone();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <span className="eyebrow">툰 작업실</span>
        <h2>{setup ? "나만의 작업실을 열어요" : "다시 오셨네요"}</h2>
        <p>
          {setup
            ? "휴대폰에서도 나만 들어올 수 있도록 비밀번호를 정해주세요."
            : "작업실 비밀번호로 이어서 시작하세요."}
        </p>
        <label>
          비밀번호
          <input
            type="password"
            autoComplete={setup ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={setup ? 10 : 1}
            required
            autoFocus
            placeholder={setup ? "10자 이상으로 입력해주세요" : ""}
          />
        </label>
        {setup && (
          <label>
            비밀번호 한 번 더
            <input
              type="password"
              autoComplete="new-password"
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
              required
            />
          </label>
        )}
        {error && (
          <p className="error-note" role="alert">
            {error}
          </p>
        )}
        <button className="primary full" disabled={busy}>
          {busy ? <LoaderCircle className="spin" size={18} /> : null}
          {setup ? "작업실 열기" : "들어가기"}
          <ArrowRight size={17} />
        </button>
        <small>
          <ShieldCheck size={14} />
          작업과 설정은 이 Mac에 저장돼요.
        </small>
      </form>
    </main>
  );
}

export default function App() {
  const [auth, setAuth] = useState<{
    authenticated: boolean;
    setupRequired: boolean;
  } | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [page, setPage] = useState<Page>("home");
  const [online, setOnline] = useState(true);
  const [toast, setToast] = useState("");
  const [menu, setMenu] = useState(false);
  const [start, setStart] = useState(false);
  const [motion, setMotion] = useState<string | null>(null);
  const [viewer, setViewer] = useState<{
    episode: string;
    runId?: string;
  } | null>(null);
  const [selectedRun, setSelectedRun] = useState<string | null>(
    new URLSearchParams(location.search).get("run"),
  );
  const [loading, setLoading] = useState(false);
  const notify = useCallback((s: string) => setToast(s), []);
  const load = useCallback(async () => {
    try {
      setSnapshot(await api<Snapshot>("/state"));
    } catch (e) {
      setToast((e as Error).message);
    }
  }, []);
  const checkAuth = useCallback(() => {
    api("/auth")
      .then(setAuth)
      .catch((e) => setToast(e.message));
  }, []);
  useEffect(checkAuth, [checkAuth]);
  useEffect(() => {
    if (!auth?.authenticated) return;
    void load();
    const stream = new EventSource("/api/events");
    let timer: ReturnType<typeof setTimeout> | undefined;
    stream.addEventListener("change", () => {
      setOnline(true);
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => void load(), 200);
    });
    stream.onopen = () => setOnline(true);
    stream.onerror = () => setOnline(false);
    return () => {
      stream.close();
      if (timer) clearTimeout(timer);
    };
  }, [auth?.authenticated, load]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 6500);
    return () => clearTimeout(t);
  }, [toast]);
  async function action(path: string, body: unknown = {}) {
    setLoading(true);
    try {
      await api(path, body);
      await load();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  const go = (target: Page) => {
    setPage(target);
    setMenu(false);
  };
  if (!auth)
    return (
      <div className="loading-page">
        <Feather size={28} />
        <p>{toast || "작업실을 열고 있어요…"}</p>
      </div>
    );
  if (!auth.authenticated)
    return <Login setup={auth.setupRequired} onDone={checkAuth} />;
  if (!snapshot)
    return (
      <div className="loading-page">
        <LoaderCircle className="spin" />
        <p>{toast || "작업을 불러오고 있어요…"}</p>
      </div>
    );
  const waiting = snapshot.runs.filter((r) => r.status === "approval").length;
  const active = snapshot.runs.find((r) =>
    ["running", "queued"].includes(r.status),
  );
  const run = snapshot.runs.find((r) => r.id === selectedRun);
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menu ? "open" : ""}`}>
        <a
          className="brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            go("home");
          }}
        >
          <span className="logo-mark">
            <Feather size={22} />
          </span>
          <span>
            툰 작업실<small>나의 작은 콘텐츠 스튜디오</small>
          </span>
        </a>
        <button
          className="primary sidebar-start"
          onClick={() => {
            setStart(true);
            setMenu(false);
          }}
        >
          <Plus size={18} />새 인스타툰 만들기
        </button>
        <button
          className="secondary sidebar-motion"
          onClick={() => {
            setMotion("");
            setMenu(false);
          }}
        >
          <Film size={18} />
          모션그래픽 만들기
        </button>
        <nav>
          {sections.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "nav-item active" : "nav-item"}
              onClick={() => go(item.id)}
            >
              <item.icon size={19} />
              {item.label}
              {item.id === "home" && waiting > 0 && (
                <span className="count">{waiting}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="mac-status">
            <span
              className={`live-dot ${snapshot.connection.codex && online ? "" : "off"}`}
            />
            <div>
              <strong>
                {snapshot.connection.codex
                  ? "Mac의 Codex 연결됨"
                  : "Codex 연결 확인 필요"}
              </strong>
              <small>이 Mac에서 제작해요</small>
            </div>
          </div>
          <button className="account-chip" onClick={() => go("settings")}>
            <Instagram size={20} />
            <span>
              {snapshot.account
                ? "@" + snapshot.account.username
                : "게시할 계정 연결하기"}
              <small>
                {snapshot.account ? "인스타그램" : "처음 한 번만 연결하면 돼요"}
              </small>
            </span>
            <ChevronRight size={16} />
          </button>
        </div>
      </aside>
      {menu && (
        <button
          className="sidebar-backdrop"
          aria-label="메뉴 닫기"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="메뉴 열기"
              onClick={() => setMenu(!menu)}
            >
              <Menu size={22} />
            </button>
            <span>나의 작업 공간</span>
            <ChevronRight size={14} />
            <strong>{sections.find((s) => s.id === page)?.label}</strong>
          </div>
          <div className="topbar-actions">
            <span className="date-label">
              {new Intl.DateTimeFormat("ko-KR", {
                month: "long",
                day: "numeric",
                weekday: "short",
              }).format(new Date())}
            </span>
            <button
              className="icon-button"
              aria-label="알림 설정"
              onClick={() => go("settings")}
            >
              <Bell size={19} />
              {waiting > 0 && <span className="notification-dot" />}
            </button>
            <button
              className="avatar"
              onClick={() => go("settings")}
              aria-label="내 작업실 설정"
            >
              나
            </button>
          </div>
        </header>
        {!online && (
          <div className="offline-banner">
            <WifiOff size={17} />
            Mac과 연결이 끊겼어요. 다시 연결되면 진행 상황을 확인합니다.
          </div>
        )}
        <main className="main-content">
          {page === "home" && (
            <>
              <div className="section-title">
                <div>
                  <p className="eyebrow">오늘도 한 편씩</p>
                  <h1>나의 작업실</h1>
                  <p>만들고 있는 이야기와 확인할 일을 한눈에 살펴보세요.</p>
                </div>
                <button className="secondary" onClick={() => go("schedules")}>
                  <CalendarClock size={17} />
                  예약 살펴보기
                </button>
              </div>
              <button
                className="secondary motion-home-button"
                onClick={() => setMotion("")}
              >
                <Film size={17} />
                모션그래픽 만들기
              </button>
              <section className="welcome-card">
                <div className="welcome-content">
                  <span className="mini-label">
                    <Sparkles size={14} />
                    인스타툰 제작부터 게시까지
                  </span>
                  <h2>
                    {active
                      ? "이야기가 만들어지고 있어요."
                      : "다음 이야기를 시작해볼까요?"}
                  </h2>
                  <p>
                    주제를 정하고, 필요한 순간에 확인하세요.
                    <br />
                    나머지 흐름은 작업실에서 이어갑니다.
                  </p>
                  <button className="primary" onClick={() => setStart(true)}>
                    <Plus size={17} />새 인스타툰 만들기
                    <ArrowRight size={17} />
                  </button>
                </div>
                <div className="welcome-illustration" aria-hidden="true">
                  <div className="paper paper-back">
                    <div className="paper-top" />
                    <span />
                    <span />
                  </div>
                  <div className="paper paper-front">
                    <Feather size={33} />
                    <div className="bubble-art">
                      새로운
                      <br />
                      이야기!
                    </div>
                    <div className="art-lines">
                      <i />
                      <i />
                      <i />
                    </div>
                    <span className="paper-check">
                      <Check size={20} />
                    </span>
                  </div>
                  <span className="spark-one">✦</span>
                  <span className="spark-two">✧</span>
                </div>
              </section>
              <div className="stats">
                <div>
                  <span className="stat-icon mint">
                    <CirclePlay size={21} />
                  </span>
                  <p>
                    진행 중인 작업
                    <strong>
                      {
                        snapshot.runs.filter((r) =>
                          ["running", "queued"].includes(r.status),
                        ).length
                      }
                      <small>개</small>
                    </strong>
                  </p>
                </div>
                <div>
                  <span className="stat-icon peach">
                    <Clock size={21} />
                  </span>
                  <p>
                    내 확인이 필요한 작업
                    <strong>
                      {waiting}
                      <small>개</small>
                    </strong>
                  </p>
                </div>
                <div>
                  <span className="stat-icon lavender">
                    <FolderHeart size={21} />
                  </span>
                  <p>
                    저장된 인스타툰
                    <strong>
                      {snapshot.library.filter((e) => e.pages.length).length}
                      <small>편</small>
                    </strong>
                  </p>
                </div>
              </div>
              <div className="section-heading">
                <h2>지금의 작업</h2>
                <span className="subtle">
                  {online
                    ? "진행 상황을 연결해서 보여줘요"
                    : "연결이 끊겨 마지막 상태를 보여줘요"}
                </span>
              </div>
              {snapshot.runs.length ? (
                <div className="run-list">
                  {snapshot.runs.slice(0, 4).map((r) => (
                    <RunCard
                      key={r.id}
                      run={r}
                      online={online}
                      onMotion={
                        r.mode !== "motion" &&
                        snapshot.library.some(
                          (e) =>
                            e.id === r.episode &&
                            !motionUnavailable(e, snapshot.runs),
                        )
                          ? () => setMotion(r.episode)
                          : undefined
                      }
                      onOpen={() => setSelectedRun(r.id)}
                      onView={() =>
                        r.mode === "motion"
                          ? setSelectedRun(r.id)
                          : setViewer({ episode: r.episode, runId: r.id })
                      }
                    />
                  ))}
                </div>
              ) : (
                <section className="empty-state">
                  <span className="empty-symbol">
                    <CirclePlay size={28} />
                  </span>
                  <div>
                    <h3>아직 시작한 작업이 없어요</h3>
                    <p>
                      새 인스타툰을 만들면, 일하는 도우미와 진행 단계가 여기에
                      나타나요.
                    </p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setStart(true)}
                  >
                    첫 작업 시작하기
                    <ArrowRight size={16} />
                  </button>
                </section>
              )}
              <div className="section-heading">
                <h2>최근 결과물</h2>
                <button className="text-button" onClick={() => go("library")}>
                  모두 보기
                  <ArrowRight size={16} />
                </button>
              </div>
              <div className="episode-grid">
                {snapshot.library
                  .filter((e) => e.pages.length)
                  .slice(0, 3)
                  .map((e) => (
                    <EpisodeCard
                      key={e.id}
                      episode={e}
                      onMotion={
                        !motionUnavailable(e, snapshot.runs)
                          ? () => setMotion(e.id)
                          : undefined
                      }
                      onOpen={() =>
                        setViewer({
                          episode: e.id,
                          runId: snapshot.runs.find(
                            (r) => r.episode === e.id && r.mode !== "motion",
                          )?.id,
                        })
                      }
                    />
                  ))}
              </div>
            </>
          )}
          {page === "library" && (
            <>
              <div className="section-title">
                <div>
                  <p className="eyebrow">쌓여가는 이야기</p>
                  <h1>결과 모아보기</h1>
                  <p>이 Mac에 저장된 실제 대본과 이미지를 볼 수 있어요.</p>
                </div>
                <span className="soft-pill">
                  총 {snapshot.library.length}편
                </span>
              </div>
              <div className="episode-grid">
                {snapshot.library.map((e) => (
                  <EpisodeCard
                    key={e.id}
                    episode={e}
                    onMotion={
                      !motionUnavailable(e, snapshot.runs)
                        ? () => setMotion(e.id)
                        : undefined
                    }
                    onOpen={() =>
                      setViewer({
                        episode: e.id,
                        runId: snapshot.runs.find(
                          (r) => r.episode === e.id && r.mode !== "motion",
                        )?.id,
                      })
                    }
                  />
                ))}
              </div>
            </>
          )}
          {page === "workflow" && (
            <WorkflowEditor
              snapshot={snapshot}
              online={online}
              onSaved={() => void load()}
              notify={notify}
            />
          )}{" "}
          {page === "schedules" && (
            <Schedules
              snapshot={snapshot}
              onChange={() => void load()}
              notify={notify}
            />
          )}{" "}
          {page === "settings" && (
            <Settings
              snapshot={snapshot}
              action={action}
              notify={notify}
              onLogout={async () => {
                await api("/logout", {});
                setSnapshot(null);
                checkAuth();
              }}
            />
          )}
        </main>
        <footer className="app-footer">
          <Feather size={13} />툰 작업실
          <span>작업은 Mac에서, 확인은 어디서든.</span>
        </footer>
      </div>
      {toast && (
        <div className="toast" role="status">
          <CircleAlert size={18} />
          <span>{toast}</span>
          <button
            aria-label="알림 닫기"
            className="icon-button"
            onClick={() => setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {start && (
        <StartModal
          defaults={snapshot.settings.defaults}
          connected={snapshot.connection.codex}
          onClose={() => setStart(false)}
          onStart={async (options) => {
            await api("/codex/connect", {});
            const r = await api<Run>("/runs", options);
            setStart(false);
            setSelectedRun(r.id);
            await load();
          }}
        />
      )}
      {motion !== null && (
        <MotionModal
          snapshot={snapshot}
          initialEpisode={motion}
          onClose={() => setMotion(null)}
          onStart={async (episode) => {
            await api("/codex/connect", {});
            const created = await api<Run>("/motion-runs", { episode });
            setMotion(null);
            setViewer(null);
            setSelectedRun(created.id);
            go("home");
            await load();
          }}
        />
      )}
      {viewer && motion === null && (
        <Viewer
          episode={viewer.episode}
          run={snapshot.runs.find((r) => r.id === viewer.runId)}
          onClose={() => setViewer(null)}
          onChange={() => void load()}
          notify={notify}
          onMotion={
            snapshot.library.some(
              (e) =>
                e.id === viewer.episode && !motionUnavailable(e, snapshot.runs),
            )
              ? () => setMotion(viewer.episode)
              : undefined
          }
        />
      )}{" "}
      {run && !viewer && motion === null && (
        <RunModal
          run={run}
          snapshot={snapshot}
          online={online}
          busy={loading}
          action={action}
          onClose={() => setSelectedRun(null)}
          onView={() =>
            setViewer({
              episode: run.episode,
              runId: run.mode === "motion" ? undefined : run.id,
            })
          }
          onMotion={
            run.mode !== "motion" &&
            snapshot.library.some(
              (e) =>
                e.id === run.episode && !motionUnavailable(e, snapshot.runs),
            )
              ? () => setMotion(run.episode)
              : undefined
          }
        />
      )}{" "}
      {snapshot.pendingRequests[0] && (
        <RequestModal
          request={snapshot.pendingRequests[0]}
          onAnswer={async (allow, answers) => {
            await action(`/requests/${snapshot.pendingRequests[0].id}`, {
              allow,
              answers,
            });
          }}
        />
      )}
    </div>
  );
}

function EpisodeCard({
  episode,
  onOpen,
  onMotion,
}: {
  episode: Episode;
  onOpen: () => void;
  onMotion?: () => void;
}) {
  return (
    <div className="episode-item">
      <button className="episode-card" onClick={onOpen}>
        <div className="episode-cover">
          {episode.pages.length ? (
            <img
              loading="lazy"
              src={imageUrl(episode.id, episode.pages[0], true)}
              alt={episode.title}
            />
          ) : (
            <FilePlaceholder />
          )}
          <span className="page-count">
            {episode.pages.length ? `${episode.pages.length}장` : "대본"}
          </span>
        </div>
        <div className="episode-info">
          <span className="eyebrow">
            {episode.id.match(/^EP-\d+/)?.[0] ?? "인스타툰"}
          </span>
          <h3>{episode.title}</h3>
          <div>
            <span>{dateText(episode.modifiedAt)}</span>
            <span className="library-status">
              저장된 결과
              <ArrowRight size={14} />
            </span>
          </div>
        </div>
      </button>
      {onMotion && (
        <button className="secondary full episode-motion" onClick={onMotion}>
          <Film size={16} />
          모션그래픽 만들기
        </button>
      )}
    </div>
  );
}
function FilePlaceholder() {
  return (
    <div className="file-placeholder">
      <Feather size={35} />
      <span>이야기를 담는 중</span>
    </div>
  );
}
function RunCard({
  run,
  online,
  onOpen,
  onView,
  onMotion,
}: {
  run: Run;
  online: boolean;
  onOpen: () => void;
  onView: () => void;
  onMotion?: () => void;
}) {
  const done = Object.values(run.stages).filter(
    (s) => s.status === "done",
  ).length;
  return (
    <article className="run-card">
      <div className="run-heading">
        <div>
          <span className="eyebrow">{run.episode.match(/^EP-\d+/)?.[0]}</span>
          <h3>{run.title}</h3>
        </div>
        <Badge status={run.status} online={online} />
      </div>
      <div className="stage-track">
        {run.workflow.nodes.map((n) => (
          <div
            key={n.id}
            className={`track-stage ${online ? run.stages[n.id]?.status : ""}`}
          >
            <span className="track-dot">
              {run.stages[n.id]?.status === "done" ? <Check size={11} /> : null}
            </span>
            <span>{n.label}</span>
          </div>
        ))}
      </div>
      {run.error && <p className="error-note">{run.error}</p>}
      <div className="run-card-foot">
        <span>
          {done} / {run.workflow.nodes.length}단계 완료
        </span>
        <div className="button-row wrap">
          {onMotion && (
            <button className="secondary small" onClick={onMotion}>
              <Film size={16} />
              모션그래픽 만들기
            </button>
          )}
          <button
            className={
              run.status === "approval" ? "primary small" : "secondary small"
            }
            onClick={onView}
          >
            {run.mode === "motion"
              ? "영상 작업 보기"
              : run.status === "approval"
                ? "결과 확인하기"
                : "대본·그림 보기"}
          </button>
          <button
            className="icon-button"
            onClick={onOpen}
            aria-label={`${run.title} 작업 자세히 보기`}
          >
            <MoreHorizontal size={21} />
          </button>
        </div>
      </div>
    </article>
  );
}
function StartModal({
  defaults,
  connected,
  onClose,
  onStart,
}: {
  defaults: Options;
  connected: boolean;
  onClose: () => void;
  onStart: (v: Options) => Promise<void>;
}) {
  const [value, setValue] = useState<Options>({ ...defaults, publishAt: null });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal title="새 인스타툰 만들기" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await onStart(value);
          } catch (e) {
            setError((e as Error).message);
            setBusy(false);
          }
        }}
      >
        <OptionsFields value={value} onChange={setValue} />
        {!connected && (
          <p className="gentle-note">
            시작할 때 이 Mac의 Codex 연결을 확인해요.
          </p>
        )}
        {error && (
          <p className="error-note" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button className="secondary" type="button" onClick={onClose}>
            취소
          </button>
          <button className="primary" disabled={busy}>
            {busy ? (
              <LoaderCircle className="spin" size={16} />
            ) : (
              <Play size={16} />
            )}
            제작 시작
          </button>
        </div>
      </form>
    </Modal>
  );
}
function RunModal({
  run,
  snapshot,
  online,
  busy,
  action,
  onClose,
  onView,
  onMotion,
}: {
  run: Run;
  snapshot: Snapshot;
  online: boolean;
  busy: boolean;
  action: (p: string, b?: unknown) => Promise<void>;
  onClose: () => void;
  onView: () => void;
  onMotion?: () => void;
}) {
  const [mediaId, setMediaId] = useState("");
  return (
    <Modal title={run.title} onClose={onClose}>
      <div className="run-modal-head">
        <Badge status={run.status} online={online} />
        <span>{dateText(run.createdAt)} 시작</span>
      </div>
      {(run.panelCount !== undefined || run.imageCount !== undefined) && (
        <p>
          전체 컷 수:{" "}
          {run.panelCount == null ? "내용에 맞춰 자동" : `${run.panelCount}컷`}{" "}
          · 결과 이미지:{" "}
          {run.imageCount == null ? "자동 5~9장" : `${run.imageCount}장`}
        </p>
      )}
      {run.error && <div className="error-note">{run.error}</div>}
      <div className="run-steps">
        {run.workflow.nodes.map((n) => (
          <div key={n.id}>
            <span className={`step-circle ${run.stages[n.id]?.status}`}>
              {run.stages[n.id]?.status === "done" ? (
                <Check size={15} />
              ) : (
                <span />
              )}
            </span>
            <div>
              <strong>{n.label}</strong>
              <small>
                {run.stages[n.id]?.message ??
                  (n.model === "local" ? "자동 처리" : n.role)}
              </small>
            </div>
            <Badge
              status={run.stages[n.id]?.status ?? "waiting"}
              online={online}
            />
          </div>
        ))}
      </div>
      {run.mode === "motion" && run.status === "motion_ready" && (
        <div className="motion-result">
          <video
            controls
            playsInline
            preload="metadata"
            src={`/api/runs/${run.id}/video`}
            aria-label="완성된 모션그래픽"
          />
          <a className="primary" href={`/api/runs/${run.id}/video?download=1`}>
            <ArrowDownToLine size={16} />
            영상 다운로드
          </a>
        </div>
      )}
      <div className="button-row wrap">
        {onMotion && (
          <button className="primary" onClick={onMotion}>
            <Film size={16} />
            모션그래픽 만들기
          </button>
        )}
        <button className="secondary" onClick={onView}>
          {run.mode === "motion" ? "원본 인스타툰 보기" : "대본·그림 확인"}
        </button>
        {["queued", "running", "approval", "ready", "scheduled"].includes(
          run.status,
        ) && (
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void action(`/runs/${run.id}/pause`)}
          >
            <Pause size={16} />
            잠시 멈추기
          </button>
        )}
        {["paused", "error"].includes(run.status) && (
          <button
            className="primary"
            disabled={busy}
            onClick={() => void action(`/runs/${run.id}/resume`)}
          >
            <Play size={16} />
            이어서 시작
          </button>
        )}
        {["ready", "scheduled"].includes(run.status) && (
          <button
            className="primary"
            disabled={busy || !snapshot.account}
            onClick={() => void action(`/runs/${run.id}/publish`)}
          >
            <Instagram size={16} />
            지금 게시하기
          </button>
        )}
        {run.status === "publish_unknown" && (
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void action(`/runs/${run.id}/verify`)}
          >
            <RefreshCw size={16} />
            게시 여부 다시 확인
          </button>
        )}
        {run.publication.permalink && (
          <a
            className="primary"
            href={run.publication.permalink}
            target="_blank"
            rel="noreferrer"
          >
            실제 게시물 보기
            <ExternalLink size={15} />
          </a>
        )}
      </div>
      {run.status === "publish_unknown" && (
        <details>
          <summary>실제 게시물 번호로 연결하기</summary>
          <p>
            인스타그램에서 이 게시물을 확인했다면 게시물 번호를 입력해 주세요.
            계정·글·게시 시각을 다시 확인합니다.
          </p>
          <div className="input-action">
            <input
              value={mediaId}
              onChange={(e) => setMediaId(e.target.value)}
              placeholder="인스타그램 게시물 번호"
            />
            <button
              className="secondary"
              onClick={() =>
                void action(`/runs/${run.id}/reconcile`, { mediaId })
              }
              disabled={!mediaId || busy}
            >
              확인
            </button>
          </div>
        </details>
      )}
      {run.mode !== "motion" &&
        !["publishing", "publish_unknown", "completed"].includes(
          run.status,
        ) && (
          <div className="run-preferences">
            <Toggle
              checked={run.humanReview}
              onChange={(humanReview) =>
                void action(`/runs/${run.id}/preferences`, {
                  humanReview,
                  publishMode: run.publishMode,
                  publishAt: run.publishAt,
                })
              }
              label="중간에 내가 확인하기"
              detail="대본과 완성된 그림에서 멈춰요."
              disabled={busy}
            />
            <Toggle
              checked={run.publishMode === "auto"}
              onChange={(auto) =>
                void action(`/runs/${run.id}/preferences`, {
                  humanReview: run.humanReview,
                  publishMode: auto ? "auto" : "manual",
                  publishAt: run.publishAt,
                })
              }
              label="자동 게시"
              detail={
                run.publishAt
                  ? `${dateText(run.publishAt)} 게시 예정 · 시간이 지났다면 준비되는 즉시 게시`
                  : "켜면 완성과 필요한 확인이 끝나는 즉시 게시해요."
              }
              disabled={busy}
            />
          </div>
        )}
      <details>
        <summary>지금까지의 작업 기록</summary>
        <div className="activity-list">
          {snapshot.events
            .filter((e) => e.runId === run.id)
            .slice(0, 30)
            .map((e) => (
              <div key={e.id}>
                <time>{dateText(e.at)}</time>
                <p>{e.message}</p>
              </div>
            ))}
        </div>
      </details>
    </Modal>
  );
}

function Schedules({
  snapshot,
  onChange,
  notify,
}: {
  snapshot: Snapshot;
  onChange: () => void;
  notify: (s: string) => void;
}) {
  const [editing, setEditing] = useState<Partial<Schedule> | null>(null);
  const [busy, setBusy] = useState(false);
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  async function save() {
    if (!editing) return;
    setBusy(true);
    try {
      await api(
        "/schedules" + (editing.id ? "/" + editing.id : ""),
        editing,
        editing.id ? "PUT" : "POST",
      );
      setEditing(null);
      onChange();
      notify("예약을 저장했어요.");
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">정해둔 시간에 차근차근</p>
          <h1>제작과 게시 예약</h1>
          <p>
            모든 예약은 한국 시간 기준이에요. Mac과 작업실이 켜져 있어야
            실행돼요.
          </p>
        </div>
        <button
          className="primary"
          onClick={() =>
            setEditing({
              label: "나의 제작 예약",
              enabled: true,
              time: "09:00",
              publishTime: "18:00",
              days: [1, 2, 3, 4, 5],
              options: { ...snapshot.settings.defaults, publishMode: "auto" },
            })
          }
        >
          <Plus size={17} />
          예약 추가
        </button>
      </div>
      <div className="schedule-list">
        {snapshot.schedules.length ? (
          snapshot.schedules.map((s) => (
            <article className="schedule-card" key={s.id}>
              <span className="stat-icon mint">
                <CalendarClock size={26} />
              </span>
              <div>
                <span className="eyebrow">
                  {s.days.map((d) => days[d]).join(" · ")}
                </span>
                <h2>{s.label}</h2>
                <p>
                  {s.time} 제작 시작 <ArrowRight size={14} />{" "}
                  {s.options.publishMode === "auto"
                    ? s.publishTime + " 자동 게시"
                    : "내가 확인 후 게시"}
                </p>
                <small>
                  {s.options.topicMode === "auto"
                    ? "주제 자동 선정"
                    : s.options.topic}{" "}
                  ·{" "}
                  {s.options.humanReview
                    ? "중간 확인 켬"
                    : "자동으로 이어서 제작"}
                </small>
              </div>
              <span className={`soft-pill ${s.enabled ? "" : "muted"}`}>
                {s.enabled ? "예약 켜짐" : "예약 꺼짐"}
              </span>
              <button className="secondary" onClick={() => setEditing(s)}>
                수정
              </button>
            </article>
          ))
        ) : (
          <div className="empty-state">
            <CalendarClock size={32} />
            <div>
              <h3>아직 예약이 없어요</h3>
              <p>원하는 요일과 시간을 정하면 자동으로 제작을 시작해요.</p>
            </div>
          </div>
        )}
      </div>
      <div className="gentle-note">
        <Clock size={22} />
        <p>
          Mac이 꺼져서 밀린 제작은 가장 최근 예약 하나만 실행해요.
          <br />
          게시 시간이 지났다면 완성과 필요한 확인이 끝나는 즉시 올려요.
        </p>
      </div>
      {editing && (
        <Modal
          title={editing.id ? "제작 예약 수정" : "새 제작 예약"}
          onClose={() => setEditing(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <div className="form-stack">
              <label>
                예약 이름
                <input
                  value={editing.label}
                  onChange={(e) =>
                    setEditing({ ...editing, label: e.target.value })
                  }
                  required
                />
              </label>
              <fieldset>
                <legend>제작할 요일</legend>
                <div className="day-picker">
                  {days.map((d, i) => (
                    <button
                      type="button"
                      className={editing.days?.includes(i) ? "selected" : ""}
                      key={d}
                      onClick={() =>
                        setEditing({
                          ...editing,
                          days: editing.days?.includes(i)
                            ? editing.days.filter((x) => x !== i)
                            : [...(editing.days ?? []), i],
                        })
                      }
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </fieldset>
              <div className="form-grid">
                <label>
                  제작 시작 시간
                  <input
                    type="time"
                    required
                    value={editing.time}
                    onChange={(e) =>
                      setEditing({ ...editing, time: e.target.value })
                    }
                  />
                </label>
                <label>
                  게시 시간
                  <input
                    type="time"
                    required
                    value={editing.publishTime}
                    onChange={(e) =>
                      setEditing({ ...editing, publishTime: e.target.value })
                    }
                  />
                </label>
              </div>
              <OptionsFields
                value={{ ...editing.options!, publishAt: null }}
                onChange={(v) => {
                  const { publishAt, ...options } = v;
                  setEditing({ ...editing, options });
                }}
                includeTime={false}
              />
              <Toggle
                checked={!!editing.enabled}
                onChange={(enabled) => setEditing({ ...editing, enabled })}
                label="이 예약 사용하기"
              />
            </div>
            <div className="modal-actions">
              {editing.id && (
                <button
                  type="button"
                  className="text-button danger"
                  onClick={async () => {
                    await api("/schedules/" + editing.id, {}, "DELETE");
                    setEditing(null);
                    onChange();
                  }}
                >
                  예약 삭제
                </button>
              )}
              <button className="primary" disabled={busy}>
                예약 저장
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function Settings({
  snapshot,
  action,
  notify,
  onLogout,
}: {
  snapshot: Snapshot;
  action: (p: string, b?: unknown) => Promise<void>;
  notify: (s: string) => void;
  onLogout: () => void;
}) {
  const [publicUrl, setPublicUrl] = useState(snapshot.settings.publicUrl);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [pushState, setPushState] = useState("");
  async function connect() {
    setBusy(true);
    try {
      const { url } = await api("/instagram/connect", {});
      location.assign(url);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function enablePush() {
    setBusy(true);
    try {
      if (
        !("serviceWorker" in navigator) ||
        !("PushManager" in window) ||
        !("Notification" in window)
      )
        throw new Error(
          "아이폰에서는 Safari에서 작업실을 홈 화면에 추가한 뒤, 홈 화면에서 열어주세요.",
        );
      if (!snapshot.connection.pushReady)
        throw new Error("먼저 아래에서 외부 접속 주소를 연결해주세요.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted")
        throw new Error("휴대폰 설정에서 작업실 알림을 허용해주세요.");
      const registration = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      const { key } = await api("/push/key");
      const bytes = Uint8Array.from(
        atob(key.replace(/-/g, "+").replace(/_/g, "/")),
        (c) => c.charCodeAt(0),
      );
      const subscription =
        (await registration.pushManager.getSubscription()) ??
        (await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: bytes,
        }));
      await api("/push/subscribe", subscription.toJSON());
      setPushState("이 기기의 알림을 등록했어요.");
      notify("알림을 등록했어요. 시험 알림으로 수신을 확인해주세요.");
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">내 작업실에 맞게</p>
          <h1>연결과 알림</h1>
          <p>만드는 도구, 게시할 계정, 휴대폰을 연결하세요.</p>
        </div>
      </div>
      <div className="settings-grid">
        <section className="settings-card">
          <div className="settings-heading">
            <span className="stat-icon mint">
              <Feather size={24} />
            </span>
            <div>
              <h2>Mac의 Codex</h2>
              <p>
                {snapshot.connection.codex
                  ? "도우미와 연결되어 있어요"
                  : "제작을 시작하기 전에 연결해주세요"}
              </p>
            </div>
            <span
              className={`live-dot ${snapshot.connection.codex ? "" : "off"}`}
            />
          </div>
          <p>{snapshot.connection.message}</p>
          <button
            className="secondary"
            onClick={() => void action("/codex/connect")}
          >
            {snapshot.connection.codex ? "연결 다시 확인" : "Codex 연결하기"}
            <RefreshCw size={16} />
          </button>
          <small>모델 목록은 현재 이 Mac의 Codex에서 가져와요.</small>
          <Toggle
            checked={snapshot.settings.autoStart}
            onChange={(enabled) =>
              void action("/settings/startup", { enabled })
            }
            label="Mac 로그인 때 작업실 열어두기"
            detail="다음 로그인부터 자동으로 시작해요. 지금 작업은 계속됩니다."
          />
        </section>
        <section className="settings-card">
          <div className="settings-heading">
            <span className="stat-icon peach">
              <Instagram size={25} />
            </span>
            <div>
              <h2>인스타그램</h2>
              <p>
                {snapshot.account
                  ? "@" + snapshot.account.username
                  : "게시할 계정을 연결해주세요"}
              </p>
            </div>
          </div>
          <p>크리에이터 또는 비즈니스 계정 하나를 연결해서 게시해요.</p>
          <div className="button-row">
            <button
              className="primary"
              onClick={() => void connect()}
              disabled={busy}
            >
              {snapshot.account ? "계정 다시 연결" : "인스타그램 계정 연결"}
              <ExternalLink size={15} />
            </button>
            {snapshot.account && (
              <button
                className="text-button"
                onClick={() => void action("/instagram/disconnect")}
              >
                연결 해제
              </button>
            )}
          </div>
          <small>
            {snapshot.account
              ? `연결 유효기간: ${dateText(snapshot.account.expiresAt)}`
              : snapshot.connection.instagramReady
                ? "연결 정보를 저장했어요. 계정 로그인을 진행해주세요."
                : "아래 ‘처음 연결에 필요한 정보’를 먼저 설정해주세요."}
          </small>
        </section>
        <section className="settings-card">
          <div className="settings-heading">
            <span className="stat-icon lavender">
              <Bell size={24} />
            </span>
            <div>
              <h2>아이폰 알림</h2>
              <p>확인이 필요하거나 작업이 멈추면 알려드려요.</p>
            </div>
          </div>
          <ol className="simple-steps">
            <li>Safari에서 외부 접속 주소를 열어요.</li>
            <li>공유 버튼 → ‘홈 화면에 추가’를 눌러요.</li>
            <li>홈 화면에서 작업실을 열고 알림을 켜요.</li>
          </ol>
          <div className="button-row">
            <button
              className="secondary"
              onClick={() => void enablePush()}
              disabled={busy}
            >
              <Bell size={16} />이 기기에서 알림 켜기
            </button>
            <button
              className="text-button"
              onClick={() => void action("/push/test")}
            >
              시험 알림
            </button>
          </div>
          {pushState && <small>{pushState}</small>}
        </section>
        <section className="settings-card">
          <div className="settings-heading">
            <span className="stat-icon sand">
              <Link size={24} />
            </span>
            <div>
              <h2>밖에서도 작업하기</h2>
              <p>이 Mac으로 연결되는 나만의 주소를 사용해요.</p>
            </div>
          </div>
          <label>
            외부 접속 주소
            <input
              type="url"
              value={publicUrl}
              onChange={(e) => setPublicUrl(e.target.value)}
              placeholder="https://나의-작업실-주소"
            />
          </label>
          <button
            className="secondary"
            onClick={() => void action("/settings/connection", { publicUrl })}
          >
            주소 저장
          </button>
          <small>
            주소 저장 뒤 실제 휴대폰에서 접속을 확인해주세요. Mac이 켜져 있고,
            이 작업실까지 연결되는 HTTPS 설정이 필요해요.
          </small>
        </section>
      </div>
      <details className="advanced-settings">
        <summary>처음 연결에 필요한 정보</summary>
        <p>
          인스타그램 공식 연결을 위해 Meta 개발자 설정에서 받은 앱 번호와
          비밀키가 필요해요. 비밀키는 이 Mac에 암호화해 저장해요.
        </p>
        <div className="form-grid">
          <label>
            연결용 앱 번호
            <input
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              autoComplete="off"
            />
          </label>
          <label>
            연결용 비밀키
            <input
              type="password"
              value={appSecret}
              onChange={(e) => setAppSecret(e.target.value)}
              autoComplete="new-password"
            />
          </label>
        </div>
        <p className="selection-note">
          로그인 후 돌아올 주소:{" "}
          {publicUrl
            ? publicUrl + "/api/instagram/callback"
            : "외부 접속 주소를 먼저 입력해주세요."}
        </p>
        <button
          className="secondary"
          disabled={!appId || !appSecret || !publicUrl}
          onClick={async () => {
            await action("/settings/connection", {
              publicUrl,
              appId,
              appSecret,
            });
            setAppSecret("");
          }}
        >
          연결 정보 저장
        </button>
      </details>
      <div className="gentle-note">
        <ShieldCheck size={22} />
        <p>
          다른 SNS와 영상 제작은 다음에 추가할 수 있도록 별도로 확장합니다.
          <br />첫 버전에서는 인스타툰과 인스타그램 게시를 사용해요.
        </p>
      </div>
      <button className="text-button" onClick={onLogout}>
        <LogOut size={16} />
        작업실에서 로그아웃
      </button>
    </>
  );
}
function RequestModal({
  request,
  onAnswer,
}: {
  request: PendingRequest;
  onAnswer: (allow: boolean, answers: Record<string, string>) => Promise<void>;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  return (
    <Modal title={request.title} onClose={() => {}}>
      <p>{request.detail}</p>
      {request.questions?.map((q) => (
        <label key={q.id}>
          {q.question}
          {q.options?.length ? (
            <select
              onChange={(e) =>
                setAnswers({ ...answers, [q.id]: e.target.value })
              }
              value={answers[q.id] ?? ""}
            >
              <option value="">답을 선택해주세요</option>
              {q.options.map((o) => (
                <option key={o.label} value={o.label}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : (
            <textarea
              value={answers[q.id] ?? ""}
              onChange={(e) =>
                setAnswers({ ...answers, [q.id]: e.target.value })
              }
            />
          )}
        </label>
      ))}
      <div className="modal-actions">
        <button
          className="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            await onAnswer(false, answers);
            setBusy(false);
          }}
        >
          진행하지 않기
        </button>
        <button
          className="primary"
          disabled={
            busy || request.questions?.some((q) => !answers[q.id]?.trim())
          }
          onClick={async () => {
            setBusy(true);
            await onAnswer(true, answers);
            setBusy(false);
          }}
        >
          확인하고 진행
        </button>
      </div>
    </Modal>
  );
}
