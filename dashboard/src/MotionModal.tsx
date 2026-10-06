import { useState } from "react";
import { Film, LoaderCircle } from "lucide-react";
import type { Snapshot } from "../shared/types";
import { motionUnavailable } from "../shared/motion";
import { Modal } from "./components";
import { imageUrl } from "./api";

export function MotionModal({
  snapshot,
  initialEpisode,
  onClose,
  onStart,
}: {
  snapshot: Snapshot;
  initialEpisode: string;
  onClose: () => void;
  onStart: (episode: string) => Promise<void>;
}) {
  const [selected, setSelected] = useState(initialEpisode);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const episode = snapshot.library.find((e) => e.id === selected);
  const blocked = episode
    ? motionUnavailable(episode, snapshot.runs)
    : "에피소드를 선택해주세요.";
  const existing = snapshot.runs.find(
    (r) =>
      r.mode === "motion" &&
      r.episode === selected &&
      r.status !== "motion_ready",
  );
  return (
    <Modal
      title="모션그래픽 만들기"
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy || blocked) return;
          setBusy(true);
          setError("");
          try {
            await onStart(selected);
          } catch (e) {
            setError((e as Error).message);
            setBusy(false);
          }
        }}
      >
        <p>완성된 인스타툰을 골라 캐릭터가 움직이는 세로 영상으로 만들어요.</p>
        <label>
          원본 에피소드
          <select
            aria-label="원본 에피소드"
            value={selected}
            disabled={busy}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">에피소드를 선택해주세요</option>
            {snapshot.library.map((e) => (
              <option
                key={e.id}
                value={e.id}
                disabled={!!motionUnavailable(e, snapshot.runs)}
              >
                {e.id.match(/^EP-\d+/)?.[0]} · {e.title}
                {motionUnavailable(e, snapshot.runs)
                  ? " (제작·검수 미완료)"
                  : ""}
              </option>
            ))}
          </select>
        </label>
        {episode?.pages[0] && (
          <img
            className="motion-source-preview"
            src={imageUrl(episode.id, episode.pages[0], true)}
            alt={`${episode.title} 원본 미리보기`}
          />
        )}
        <p className="gentle-note">
          약 30초 · 세로 9:16 · 상황극 중심 연출 · 게임풍 음악
          <br />
          원본은 보존하고 영상용 동작 이미지를 새로 만들어요.
        </p>
        {!snapshot.library.some(
          (e) => !motionUnavailable(e, snapshot.runs),
        ) && <p>대본·최종 이미지·검수가 완료된 에피소드가 아직 없어요.</p>}
        {episode && blocked && (
          <p role="alert" className="error-note">
            {blocked}
          </p>
        )}
        {existing && (
          <p>이미 영상 작업이 있어요. 새로 만들지 않고 해당 작업을 엽니다.</p>
        )}
        {error && (
          <p role="alert" className="error-note">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button
            type="button"
            className="secondary"
            onClick={onClose}
            disabled={busy}
          >
            취소
          </button>
          <button className="primary" disabled={busy || !!blocked}>
            {busy ? (
              <LoaderCircle size={17} className="spin" />
            ) : (
              <Film size={17} />
            )}{" "}
            {existing ? "기존 영상 작업 보기" : "모션그래픽 제작 시작"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
