import { test } from "node:test";
import assert from "node:assert/strict";
import { Codex } from "../server/codex";
import { defaultWorkflow } from "../shared/workflow";

test("resumed dashboard threads and turns explicitly use automatic review", async () => {
  const c = new Codex("/tmp/toon-policy-test");
  const stage = defaultWorkflow.nodes.find((n) => n.kind === "topic")!;
  c.connect = async () => {};
  c.models = [{ model: stage.model, displayName: stage.model, supportedReasoningEfforts: [{ reasoningEffort: stage.effort, description: "test" }] }];
  const calls: {method: string; params: any}[] = [];
  c.call = async (method, params) => {
    calls.push({ method, params });
    if (method === "thread/resume") return { thread: { id: "existing-thread" } };
    if (method === "turn/start") {
      setImmediate(() => (c as any).onMessage({ method: "turn/completed", params: { threadId: "existing-thread", turn: { status: "completed" } } }));
      return { turn: { id: "new-turn" } };
    }
    throw new Error(method);
  };
  const id = await c.thread(stage, "Keep episode scope", "existing-thread");
  await c.run(id, stage, "Continue", "existing-run");
  assert.equal(calls[0].params.approvalsReviewer, "auto_review");
  assert.equal(calls[0].params.approvalPolicy, "on-request");
  assert.equal(calls[0].params.sandbox, "workspace-write");
  assert.equal(calls[1].params.approvalsReviewer, "auto_review");
});
