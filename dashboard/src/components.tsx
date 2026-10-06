import { useEffect, useRef, type ReactNode } from "react";
import { X, LoaderCircle, Check, Clock, CircleAlert } from "lucide-react";
import { labels } from "../shared/types";
import type { RunStatus, StageStatus, Options } from "../shared/types";
import { localInput } from "./api";
import { countError } from "../shared/layout";

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    const element = ref.current;
    return () => element?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "modal wide" : "modal"}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="닫기">
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Badge({
  status,
  online = true,
}: {
  status: RunStatus | StageStatus;
  online?: boolean;
}) {
  const Icon =
    status === "running" && online
      ? LoaderCircle
      : ["done", "completed", "motion_ready"].includes(status)
        ? Check
        : ["error", "publish_unknown"].includes(status)
          ? CircleAlert
          : Clock;
  return (
    <span
      className={`badge ${status === "running" && !online ? "paused" : status}`}
    >
      <Icon
        size={13}
        className={status === "running" && online ? "spin" : ""}
      />
      {status === "running" && !online ? "연결 확인 중" : labels[status]}
    </span>
  );
}
export function Toggle({
  checked,
  onChange,
  label,
  detail,
  disabled = false,
}: {
  checked: boolean;
  onChange: (b: boolean) => void;
  label: string;
  detail?: string;
  disabled?: boolean;
}) {
  return (
    <label className="toggle-row">
      <span>
        <strong>{label}</strong>
        {detail && <small>{detail}</small>}
      </span>
      <input
        type="checkbox"
        role="switch"
        aria-label={label}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className="toggle" aria-hidden="true" />
    </label>
  );
}
export function OptionsFields({
  value,
  onChange,
  includeTime = true,
}: {
  value: Options;
  onChange: (value: Options) => void;
  includeTime?: boolean;
}) {
  return (
    <div className="form-stack">
      <fieldset>
        <legend>어떤 이야기를 만들까요?</legend>
        <div className="choice-row">
          <button
            type="button"
            className={
              value.topicMode === "auto" ? "choice selected" : "choice"
            }
            onClick={() => onChange({ ...value, topicMode: "auto" })}
          >
            <strong>주제 자동으로 고르기</strong>
            <small>기존 방식으로 자료와 검색 수요를 확인해요.</small>
          </button>
          <button
            type="button"
            className={
              value.topicMode === "manual" ? "choice selected" : "choice"
            }
            onClick={() => onChange({ ...value, topicMode: "manual" })}
          >
            <strong>내가 주제 정하기</strong>
            <small>만들고 싶은 이야기를 적어주세요.</small>
          </button>
        </div>
      </fieldset>
      {value.topicMode === "manual" && (
        <label>
          만들 주제
          <textarea
            value={value.topic}
            onChange={(e) => onChange({ ...value, topic: e.target.value })}
            placeholder="예: 내일배움카드가 있어도 학원비를 내야 할까?"
            required
            maxLength={500}
          />
        </label>
      )}
      <fieldset>
        <legend>몇 컷, 몇 장으로 만들까요?</legend>
        <div className="form-grid">
          <label>
            전체 컷 수
            <select
              aria-label="전체 컷 수"
              value={value.panelCount ?? "auto"}
              onChange={(e) =>
                onChange({
                  ...value,
                  panelCount:
                    e.target.value === "auto" ? null : Number(e.target.value),
                })
              }
            >
              <option value="auto">내용에 맞춰 자동</option>
              {Array.from({ length: 38 }, (_, i) => i + 3).map((n) => (
                <option key={n} value={n}>
                  {n}컷
                </option>
              ))}
            </select>
          </label>
          <label>
            결과 이미지 수
            <select
              aria-label="결과 이미지 수"
              value={value.imageCount ?? "auto"}
              onChange={(e) =>
                onChange({
                  ...value,
                  imageCount:
                    e.target.value === "auto" ? null : Number(e.target.value),
                })
              }
            >
              <option value="auto">자동 · 5~9장</option>
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n}장
                </option>
              ))}
            </select>
          </label>
        </div>
        <small>
          컷은 이야기 속 장면, 이미지는 게시할 그림 파일이에요. 이미지 한 장에
          1~4컷을 담아요. 둘 다 자동이면 내용에 맞춰 5~9장을 만들어요.
        </small>
        {countError(value) && (
          <p className="error-note" role="alert">
            {countError(value)}
          </p>
        )}
      </fieldset>
      <Toggle
        checked={value.humanReview}
        onChange={(humanReview) => onChange({ ...value, humanReview })}
        label="중간에 내가 확인하기"
        detail={
          value.humanReview
            ? "대본과 완성된 그림, 두 번 멈춰서 확인해요."
            : "자동 검사를 통과하면 다음 단계로 계속 진행해요."
        }
      />
      <label>
        완성된 인스타툰 게시하기
        <select
          value={value.publishMode}
          onChange={(e) =>
            onChange({
              ...value,
              publishMode: e.target.value as Options["publishMode"],
            })
          }
        >
          <option value="manual">내가 게시 버튼 누르기</option>
          <option value="auto">정한 시간에 자동으로 게시하기</option>
        </select>
      </label>
      {includeTime && value.publishMode === "auto" && (
        <label>
          게시할 날짜와 시간
          <input
            type="datetime-local"
            required
            value={localInput(value.publishAt)}
            onChange={(e) =>
              onChange({
                ...value,
                publishAt: e.target.value
                  ? new Date(e.target.value).toISOString()
                  : null,
              })
            }
          />
          <small>
            예약 시간이 지났다면, 완성과 필요한 확인이 끝나는 즉시 올려요.
          </small>
        </label>
      )}
    </div>
  );
}
