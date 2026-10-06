import type { Episode, Run, Workflow } from "./types";

export function motionUnavailable(
  episode: Episode,
  runs: Run[],
): string | null {
  if (!episode.motionReady)
    return "대본·최종 이미지·검수가 완료된 에피소드만 선택할 수 있어요.";
  if (
    runs.some(
      (r) =>
        r.episode === episode.id &&
        r.mode !== "motion" &&
        !["ready", "scheduled", "completed"].includes(r.status),
    )
  )
    return "이 에피소드의 인스타툰 작업을 먼저 마쳐주세요.";
  return null;
}
export const motionWorkflow: Workflow = {
  version: 1,
  nodes: [
    {
      id: "motion_plan",
      label: "장면·연출 기획",
      role: "toon_motion_planner",
      model: "gpt-6-astra",
      effort: "low",
      kind: "custom",
    },
    {
      id: "motion_content",
      label: "각색 대본 검수",
      role: "toon_content_review",
      model: "gpt-6-astra",
      effort: "high",
      kind: "custom",
    },
    {
      id: "motion_produce",
      label: "모션그래픽 제작",
      role: "toon_motion_producer",
      model: "gpt-6.1-sol",
      effort: "high",
      kind: "custom",
    },
    {
      id: "motion_visual",
      label: "영상 화면 검수",
      role: "toon_visual_review",
      model: "gpt-6.1-sol",
      effort: "medium",
      kind: "custom",
    },
    {
      id: "motion_quality",
      label: "영상 파일 검사",
      role: "파일 검사",
      model: "local",
      effort: "none",
      kind: "quality",
    },
  ].map((n, i) => ({
    ...n,
    instructions: "",
    position: { x: i * 260, y: 0 },
  })) as Workflow["nodes"],
  edges: [
    "motion_plan",
    "motion_content",
    "motion_produce",
    "motion_visual",
    "motion_quality",
  ]
    .slice(1)
    .map((target, i, a) => ({
      id: `motion-edge-${i}`,
      source: ["motion_plan", ...a][i],
      target,
    })),
};
