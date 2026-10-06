import { z } from "zod";
import type { Workflow, Options } from "./types";
import { countError } from "./layout";

const node = z.object({
  id: z.string().regex(/^[a-zA-Z0-9_-]{1,60}$/),
  label: z.string().min(1).max(60),
  kind: z.enum([
    "topic",
    "script",
    "content_review",
    "art",
    "visual_review",
    "quality",
    "publish",
    "custom",
  ]),
  role: z.string().min(1).max(80),
  model: z.string().min(1).max(100),
  effort: z.enum([
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
    "ultra",
  ]),
  instructions: z.string().max(12000),
  position: z.object({ x: z.number().finite(), y: z.number().finite() }),
});
export const workflowSchema = z.object({
  version: z.number().int().nonnegative(),
  nodes: z.array(node).min(7).max(30),
  edges: z
    .array(
      z.object({
        id: z.string().max(100),
        source: z.string(),
        target: z.string(),
      }),
    )
    .max(100),
});
export const optionsSchema = z
  .object({
    panelCount: z.number().int().min(3).max(40).nullable().default(null),
    imageCount: z.number().int().min(1).max(10).nullable().default(null),
    topicMode: z.enum(["manual", "auto"]),
    topic: z.string().trim().max(500),
    humanReview: z.boolean(),
    publishMode: z.enum(["manual", "auto"]),
    publishAt: z.string().datetime().nullable(),
  })
  .refine(
    (o) => o.topicMode === "auto" || o.topic.length > 0,
    "직접 정할 주제를 적어주세요.",
  )
  .superRefine((o, ctx) => {
    const message = countError(o);
    if (message) ctx.addIssue({ code: z.ZodIssueCode.custom, message });
  });
export const defaults: Options = {
  panelCount: null,
  imageCount: null,
  topicMode: "auto",
  topic: "",
  humanReview: true,
  publishMode: "manual",
  publishAt: null,
};
export const defaultWorkflow: Workflow = {
  version: 1,
  nodes: [
    {
      id: "topic",
      label: "주제와 자료 찾기",
      kind: "topic",
      role: "자료 찾는 도우미",
      model: "gpt-6.1-sol",
      effort: "low",
      instructions: "",
      position: { x: 0, y: 0 },
    },
    {
      id: "script",
      label: "대본 쓰기",
      kind: "script",
      role: "제작 도우미",
      model: "gpt-6.1-sol",
      effort: "high",
      instructions: "",
      position: { x: 260, y: 0 },
    },
    {
      id: "content",
      label: "내용 살펴보기",
      kind: "content_review",
      role: "내용 검토 도우미",
      model: "gpt-6-astra",
      effort: "high",
      instructions: "",
      position: { x: 520, y: 0 },
    },
    {
      id: "art",
      label: "그림 만들기",
      kind: "art",
      role: "제작 도우미",
      model: "gpt-6.1-sol",
      effort: "high",
      instructions: "",
      position: { x: 0, y: 170 },
    },
    {
      id: "visual",
      label: "그림 살펴보기",
      kind: "visual_review",
      role: "그림 검토 도우미",
      model: "gpt-6.1-sol",
      effort: "medium",
      instructions: "",
      position: { x: 260, y: 170 },
    },
    {
      id: "quality",
      label: "마지막 검사",
      kind: "quality",
      role: "파일 검사",
      model: "local",
      effort: "none",
      instructions: "",
      position: { x: 520, y: 170 },
    },
    {
      id: "publish",
      label: "인스타그램 게시",
      kind: "publish",
      role: "게시 확인",
      model: "local",
      effort: "none",
      instructions: "",
      position: { x: 260, y: 340 },
    },
  ],
  edges: ["topic", "script", "content", "art", "visual", "quality", "publish"]
    .slice(1)
    .map((target, i, a) => ({
      id: `edge-${i}`,
      source: ["topic", ...a][i],
      target,
    })),
};
export function orderedStages(workflow: Workflow) {
  const ids = new Set(workflow.nodes.map((n) => n.id));
  if (ids.size !== workflow.nodes.length)
    throw new Error("같은 이름의 단계가 두 번 들어 있습니다.");
  const remaining = new Set(ids);
  const result = [] as Workflow["nodes"];
  for (const e of workflow.edges)
    if (!ids.has(e.source) || !ids.has(e.target) || e.source === e.target)
      throw new Error("연결선을 다시 확인해주세요.");
  while (remaining.size) {
    const next = workflow.nodes.find(
      (n) =>
        remaining.has(n.id) &&
        workflow.edges
          .filter((e) => e.target === n.id)
          .every((e) => !remaining.has(e.source)),
    );
    if (!next) throw new Error("단계가 서로 되돌아가도록 연결되어 있습니다.");
    remaining.delete(next.id);
    result.push(next);
  }
  return result;
}
export function validateWorkflow(input: unknown): Workflow {
  const w = workflowSchema.parse(input);
  orderedStages(w);
  const required = [
    "topic",
    "script",
    "content_review",
    "art",
    "visual_review",
    "quality",
    "publish",
  ];
  for (const kind of required)
    if (w.nodes.filter((n) => n.kind === kind).length !== 1)
      throw new Error("기본 제작·검사·게시 단계는 하나씩 있어야 합니다.");
  const ancestors = (id: string, seen = new Set<string>()): Set<string> => {
    for (const edge of w.edges.filter((e) => e.target === id))
      if (!seen.has(edge.source)) {
        seen.add(edge.source);
        ancestors(edge.source, seen);
      }
    return seen;
  };
  const chain = required.map((kind) => w.nodes.find((n) => n.kind === kind)!);
  for (let i = 1; i < chain.length; i++)
    if (!ancestors(chain[i].id).has(chain[i - 1].id))
      throw new Error(
        "내용 검사 → 그림 제작 → 그림 검사 → 마지막 검사 → 게시 순서를 유지해주세요.",
      );
  const last = chain.at(-1)!;
  for (const n of w.nodes)
    if (n.id !== last.id && !ancestors(last.id).has(n.id))
      throw new Error("모든 단계는 게시 전에 끝나도록 연결해주세요.");
  if (w.edges.some((e) => e.source === last.id))
    throw new Error("게시는 마지막 단계여야 합니다.");
  for (const n of w.nodes)
    if (
      ["quality", "publish"].includes(n.kind) &&
      (n.model !== "local" || n.instructions.trim())
    )
      throw new Error(
        "파일 검사와 게시에는 모델이나 추가 지시를 넣을 수 없습니다.",
      );
  return w;
}
