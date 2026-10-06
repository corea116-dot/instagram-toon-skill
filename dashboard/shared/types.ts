export type Effort =
  | "none"
  | "minimal"
  | "low"
  | "medium"
  | "high"
  | "xhigh"
  | "max"
  | "ultra";
export type Kind =
  | "topic"
  | "script"
  | "content_review"
  | "art"
  | "visual_review"
  | "quality"
  | "publish"
  | "custom";
export type StageStatus =
  | "waiting"
  | "running"
  | "done"
  | "approval"
  | "paused"
  | "error";
export type RunStatus =
  | "queued"
  | "running"
  | "approval"
  | "paused"
  | "error"
  | "ready"
  | "scheduled"
  | "publishing"
  | "publish_unknown"
  | "completed"
  | "motion_ready";
export interface Stage {
  id: string;
  label: string;
  kind: Kind;
  role: string;
  model: string;
  effort: Effort;
  instructions: string;
  position: { x: number; y: number };
}
export interface Workflow {
  version: number;
  nodes: Stage[];
  edges: { id: string; source: string; target: string }[];
}
export interface Options {
  /** null: choose from the story; absent: legacy run before count selection. */
  panelCount?: number | null;
  imageCount?: number | null;
  topicMode: "manual" | "auto";
  topic: string;
  humanReview: boolean;
  publishMode: "manual" | "auto";
  publishAt: string | null;
}
export interface StageState {
  status: StageStatus;
  attempts: number;
  threadId?: string;
  turnId?: string;
  message?: string;
  startedAt?: string;
  finishedAt?: string;
  model?: string;
  effort?: string;
}
export interface Annotation {
  id: string;
  file: string;
  quote?: string;
  point?: { x: number; y: number };
  note: string;
  createdAt: string;
  revision: string;
  resolved: boolean;
}
export interface Publication {
  phase: "none" | "prepared" | "sending" | "verifying" | "unknown" | "verified";
  fingerprint?: string;
  accountId?: string;
  children: string[];
  containerId?: string;
  mediaId?: string;
  permalink?: string;
  attemptedAt?: string;
  verifiedAt?: string;
  reason?: string;
}
export interface Run extends Options {
  mode?: "comic" | "motion";
  motionDirectory?: string;
  sourceFingerprint?: string;
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  episode: string;
  workflow: Workflow;
  stages: Record<string, StageState>;
  status: RunStatus;
  currentStage?: string;
  error?: string;
  annotations: Annotation[];
  approvals: Record<string, string>;
  publication: Publication;
  revisionRequest?: string;
  scheduleId?: string;
  scheduledFor?: string;
}
export interface Schedule {
  id: string;
  enabled: boolean;
  label: string;
  time: string;
  publishTime: string;
  days: number[];
  options: Omit<Options, "publishAt">;
  createdAt: string;
  lastSlot: string | null;
}
export interface Event {
  id: string;
  at: string;
  runId?: string;
  type: string;
  message: string;
}
export interface Settings {
  workflow: Workflow;
  defaults: Options;
  publicUrl: string;
  privateUrl?: string;
  graphVersion: string;
  autoStart: boolean;
}
export interface State {
  settings: Settings;
  runs: Run[];
  schedules: Schedule[];
  events: Event[];
}
export interface Episode {
  id: string;
  title: string;
  pages: string[];
  modifiedAt: string;
  scriptReady: boolean;
  qaRecorded: boolean;
  motionReady?: boolean;
}
export interface EpisodeDetail extends Episode {
  script: Record<string, unknown> | null;
  caption: string;
  report: string;
  fingerprint: string;
}
export interface Model {
  model: string;
  displayName: string;
  supportedReasoningEfforts: { reasoningEffort: Effort; description: string }[];
}
export interface Account {
  id: string;
  username: string;
  connectedAt: string;
  expiresAt: string;
}
export interface PendingRequest {
  id: string;
  runId: string;
  title: string;
  detail: string;
  method: string;
  questions?: {
    id: string;
    question: string;
    options?: { label: string; description: string }[];
  }[];
}
export interface Snapshot extends State {
  library: Episode[];
  account: Account | null;
  connection: {
    codex: boolean;
    checking: boolean;
    message: string;
    models: Model[];
    instagramReady: boolean;
    remoteReady: boolean;
    pushReady: boolean;
  };
  pendingRequests: PendingRequest[];
  now: string;
}
export const labels: Record<RunStatus | StageStatus, string> = {
  queued: "시작 기다림",
  running: "작업 중",
  approval: "확인 필요",
  paused: "잠시 멈춤",
  error: "도움 필요",
  ready: "게시 준비 완료",
  scheduled: "게시 시간 기다림",
  publishing: "인스타그램에 올리는 중",
  publish_unknown: "게시 여부 확인 필요",
  completed: "게시 완료",
  motion_ready: "영상 완성",
  waiting: "기다림",
  done: "완료",
};
export const effortLabels: Record<Effort, string> = {
  none: "사용 안 함",
  minimal: "아주 가볍게",
  low: "가볍게",
  medium: "보통",
  high: "깊게",
  xhigh: "더 깊게",
  max: "매우 깊게",
  ultra: "가장 깊게",
};
