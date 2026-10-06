import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  MessageSquarePlus,
  Send,
  Pin,
  FileText,
  Images,
  Film,
} from "lucide-react";
import type { EpisodeDetail, Run } from "../shared/types";
import { api, imageUrl } from "./api";
import { Modal } from "./components";

export function Viewer({
  episode,
  run,
  onClose,
  onChange,
  notify,
  onMotion,
}: {
  episode: string;
  run?: Run;
  onClose: () => void;
  onChange: () => void;
  notify: (s: string) => void;
  onMotion?: () => void;
}) {
  const [detail, setDetail] = useState<EpisodeDetail | null>(null);
  const [tab, setTab] = useState<"images" | "script">(
    run?.workflow.nodes.find((n) => n.id === run.currentStage)?.kind ===
      "content_review"
      ? "script"
      : "images",
  );
  const [page, setPage] = useState(0);
  const [note, setNote] = useState("");
  const [quote, setQuote] = useState("");
  const [point, setPoint] = useState<{ x: number; y: number } | undefined>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api<EpisodeDetail>("/episodes/" + encodeURIComponent(episode))
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [episode, run?.updatedAt]);
  const editable =
    !!run &&
    !["completed", "publishing", "publish_unknown"].includes(run.status);
  const panels = Array.isArray(detail?.script?.panels)
    ? (detail!.script!.panels as any[])
    : [];
  const file =
    tab === "script" ? "script.json" : "final/" + (detail?.pages[page] ?? "");
  const notes = run?.annotations.filter((a) => a.file === file) ?? [];
  async function addNote() {
    if (!run || !detail) return;
    setBusy(true);
    try {
      await api(`/runs/${run.id}/annotations`, {
        file,
        note,
        revision: detail.fingerprint,
        ...(tab === "script" ? { quote } : { point }),
      });
      setNote("");
      setQuote("");
      setPoint(undefined);
      onChange();
      notify("수정 메모를 남겼어요.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function approve() {
    if (!run || !detail) return;
    setBusy(true);
    try {
      await api(`/runs/${run.id}/approve`, { fingerprint: detail.fingerprint });
      onChange();
      onClose();
      notify("확인했어요. 다음 단계로 이어갑니다.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function revise() {
    if (!run) return;
    setBusy(true);
    try {
      await api(`/runs/${run.id}/revise`, {});
      onChange();
      onClose();
      notify("수정 메모를 Codex에게 전달했어요.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={detail?.title ?? "결과물 불러오는 중…"}
      onClose={onClose}
      wide
    >
      {error && (
        <div className="error-note" role="alert">
          {error}
        </div>
      )}
      {detail && (
        <>
          {onMotion && (
            <button className="secondary" onClick={onMotion}>
              <Film size={17} />이 에피소드로 모션그래픽 만들기
            </button>
          )}
          <div className="viewer-tabs">
            <button
              className={tab === "images" ? "active" : ""}
              onClick={() => {
                setTab("images");
                setPoint(undefined);
              }}
            >
              <Images size={17} />
              완성된 그림 <span>{detail.pages.length}</span>
            </button>
            <button
              className={tab === "script" ? "active" : ""}
              onClick={() => setTab("script")}
            >
              <FileText size={17} />
              대본
            </button>
          </div>
          <div className="viewer-layout">
            <div className="viewer-stage">
              {tab === "images" ? (
                detail.pages.length ? (
                  <>
                    <div
                      className={`image-markup ${editable ? "editable" : ""}`}
                      onClick={(e) => {
                        if (!editable) return;
                        const rect = e.currentTarget.getBoundingClientRect();
                        setPoint({
                          x: (e.clientX - rect.left) / rect.width,
                          y: (e.clientY - rect.top) / rect.height,
                        });
                      }}
                    >
                      <img
                        src={imageUrl(episode, detail.pages[page])}
                        alt={`${detail.title} ${page + 1}번째 이미지`}
                      />
                      {notes
                        .filter((n) => n.point)
                        .map((n, i) => (
                          <span
                            key={n.id}
                            className="annotation-pin"
                            style={{
                              left: `${n.point!.x * 100}%`,
                              top: `${n.point!.y * 100}%`,
                            }}
                            title={n.note}
                          >
                            {i + 1}
                          </span>
                        ))}
                      {point && (
                        <span
                          className="annotation-pin new"
                          style={{
                            left: `${point.x * 100}%`,
                            top: `${point.y * 100}%`,
                          }}
                        >
                          <Pin size={14} />
                        </span>
                      )}
                    </div>
                    <div className="page-controls">
                      <button
                        className="icon-button"
                        aria-label="이전 이미지"
                        disabled={page === 0}
                        onClick={() => {
                          setPage(page - 1);
                          setPoint(undefined);
                        }}
                      >
                        <ArrowLeft size={19} />
                      </button>
                      <span>
                        {page + 1} / {detail.pages.length}
                      </span>
                      <button
                        className="icon-button"
                        aria-label="다음 이미지"
                        disabled={page === detail.pages.length - 1}
                        onClick={() => {
                          setPage(page + 1);
                          setPoint(undefined);
                        }}
                      >
                        <ArrowRight size={19} />
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="empty-view">
                    <Images size={35} />
                    <h3>그림이 아직 준비되지 않았어요</h3>
                    <p>대본이 완성되면 다음 단계에서 만들어요.</p>
                  </div>
                )
              ) : (
                <div
                  className="script-reader"
                  onMouseUp={() => {
                    const selection = window.getSelection()?.toString();
                    if (selection) setQuote(selection.slice(0, 3000));
                  }}
                  onTouchEnd={() => {
                    const selection = window.getSelection()?.toString();
                    if (selection) setQuote(selection.slice(0, 3000));
                  }}
                >
                  {panels.length ? (
                    panels.map((panel, i) => (
                      <article key={i}>
                        <span className="eyebrow">
                          {panel.panel ?? i + 1}번째 컷
                        </span>
                        {panel.scene && <p className="scene">{panel.scene}</p>}
                        {(panel.dialogue ?? []).map((line: any, j: number) => (
                          <p className="dialogue-line" key={j}>
                            {line.text ?? String(line)}
                          </p>
                        ))}
                        {panel.card && <p>{JSON.stringify(panel.card)}</p>}
                        <button
                          className="text-button"
                          onClick={() =>
                            setQuote(
                              (panel.dialogue ?? [])
                                .map((x: any) => x.text)
                                .join("\n") || `${panel.panel ?? i + 1}번째 컷`,
                            )
                          }
                        >
                          <MessageSquarePlus size={14} />이 컷에 메모
                        </button>
                      </article>
                    ))
                  ) : (
                    <p>아직 대본이 없어요.</p>
                  )}
                </div>
              )}
            </div>
            <aside className="annotation-panel">
              <h3>
                <MessageSquarePlus size={19} />
                고칠 부분 남기기
              </h3>
              <p>
                {editable
                  ? tab === "images"
                    ? "그림에서 고칠 위치를 누르고, 원하는 내용을 적어주세요."
                    : "고칠 글을 선택하거나 컷 아래 메모 버튼을 눌러주세요."
                  : "저장된 결과물을 보고 있어요. 진행 중인 제작에서 수정 메모를 전달할 수 있어요."}
              </p>
              {editable && (
                <>
                  <div className="selection-note">
                    {quote
                      ? `선택한 글: ${quote}`
                      : point
                        ? "그림에서 수정할 위치를 선택했어요."
                        : "결과물 전체에 대한 메모도 남길 수 있어요."}
                  </div>
                  <textarea
                    aria-label="수정 메모"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="예: 이 말풍선의 글씨를 조금 더 크게 해줘"
                    rows={4}
                  />
                  <button
                    className="secondary full"
                    onClick={() => void addNote()}
                    disabled={busy || !note.trim()}
                  >
                    메모 남기기
                  </button>
                </>
              )}
              <div className="notes-list">
                {notes.map((n, i) => (
                  <div className="note" key={n.id}>
                    <span>{i + 1}</span>
                    <div>
                      {n.quote && <blockquote>{n.quote}</blockquote>}
                      <p>{n.note}</p>
                      <small>
                        {n.resolved ? "수정 반영됨" : "수정 요청 대기"}
                      </small>
                    </div>
                  </div>
                ))}
              </div>
              {detail.caption && (
                <details>
                  <summary>게시글 보기</summary>
                  <p className="caption-text">{detail.caption}</p>
                </details>
              )}
              <details>
                <summary>검사 기록 보기</summary>
                <pre className="report">
                  {detail.report || "아직 검사 기록이 없습니다."}
                </pre>
              </details>
            </aside>
          </div>
          {run && (
            <div className="modal-actions">
              <span className="subtle">
                수정하면 필요한 검사와 확인을 다시 거쳐요.
              </span>
              {editable && run.annotations.some((a) => !a.resolved) && (
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => void revise()}
                >
                  <Send size={16} />
                  메모대로 수정 요청
                </button>
              )}
              {run.status === "approval" && (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void approve()}
                >
                  <Check size={17} />
                  확인했어요, 계속하기
                </button>
              )}
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
