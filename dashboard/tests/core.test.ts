import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtemp,
  mkdir,
  writeFile,
  readFile,
  symlink,
  rm,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { EventEmitter } from "node:events";
import { request as httpRequest } from "node:http";
import sharp from "sharp";
import { Store } from "../server/store";
import { Artifacts } from "../server/artifacts";
import { Instagram, PublishUncertain } from "../server/instagram";
import { Engine } from "../server/engine";
import { Interrupted } from "../server/codex";
import { latestDue, nextSlot, publishForSlot } from "../server/scheduler";
import {
  validateWorkflow,
  defaultWorkflow,
  defaults,
} from "../shared/workflow";
import { createApp } from "../server/app";
import type { Run, Schedule } from "../shared/types";

async function fixture(t: any) {
  const dir = await mkdtemp(join(tmpdir(), "toon-test-"));
  const store = new Store(join(dir, "data"));
  const artifacts = new Artifacts(dir);
  t.after(async () => {
    store.close();
    await rm(dir, { recursive: true, force: true });
  });
  const episode = "EP-001-fixture";
  await mkdir(join(dir, "episodes", episode, "final"), { recursive: true });
  await writeFile(
    join(dir, "episodes", episode, "script.json"),
    JSON.stringify({ title: "시험용 이야기", panels: [{ id: 1 }] }),
  );
  await writeFile(
    join(dir, "episodes", episode, "caption.txt"),
    "테스트 게시글",
  );
  await sharp({
    create: { width: 1080, height: 1080, channels: 3, background: "#ccddee" },
  })
    .png()
    .toFile(join(dir, "episodes", episode, "final", "page-01.png"));
  const workflow = structuredClone(defaultWorkflow);
  const run: Run = {
    ...defaults,
    id: crypto.randomUUID(),
    title: "시험용 이야기",
    episode,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    status: "ready",
    workflow,
    stages: Object.fromEntries(
      workflow.nodes.map((n) => [
        n.id,
        { status: n.kind === "publish" ? "waiting" : "done", attempts: 0 },
      ]),
    ),
    annotations: [],
    approvals: {
      script: await artifacts.fingerprint(episode, "script"),
      images: await artifacts.fingerprint(episode, "images"),
      quality: await artifacts.fingerprint(episode),
    },
    publication: { phase: "none", children: [] },
  };
  store.update((s) => {
    s.runs.push(run);
    s.settings.publicUrl = "https://desk.example.test";
  });
  store.setSecret("instagram", {
    id: "12345",
    username: "test_account",
    token: "TEST_ONLY_TOKEN",
    connectedAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 86400_000).toISOString(),
  });
  return { dir, store, artifacts, run };
}
const schedule: Schedule = {
  id: "schedule",
  enabled: true,
  label: "시험",
  time: "09:00",
  publishTime: "18:00",
  days: [0, 1, 2, 3, 4, 5, 6],
  options: defaults,
  createdAt: "2026-09-01T00:00:00.000Z",
  lastSlot: null,
};

test("newest missed Korean schedule only, persisted slot deduplicates", () => {
  const now = new Date("2026-10-01T03:00:00Z");
  const due = latestDue(schedule, now);
  assert.equal(due, "2026-10-01T00:00:00.000Z");
  assert.equal(latestDue({ ...schedule, lastSlot: due }, now), null);
  assert.equal(
    latestDue({ ...schedule, days: [0] }, now),
    "2026-09-27T00:00:00.000Z",
  );
  assert.equal(
    nextSlot({ ...schedule, days: [0] }, now),
    "2026-10-04T00:00:00.000Z",
  );
  assert.equal(
    latestDue({ ...schedule, createdAt: "2026-10-01T02:00:00.000Z" }, now),
    null,
  );
  assert.equal(
    publishForSlot({ ...schedule, publishTime: "08:00" }, due!),
    "2026-10-01T23:00:00.000Z",
  );
});

test("workflow rejects cycles, removed QA, disconnected custom and bypassed required order", () => {
  assert.equal(validateWorkflow(defaultWorkflow).nodes.length, 7);
  const cycle = structuredClone(defaultWorkflow);
  cycle.edges.push({ id: "cycle", source: "art", target: "script" });
  assert.throws(() => validateWorkflow(cycle));
  const missing = structuredClone(defaultWorkflow);
  missing.nodes = missing.nodes.filter((n) => n.id !== "visual");
  assert.throws(() => validateWorkflow(missing));
  const custom = structuredClone(defaultWorkflow);
  custom.nodes.push({ ...custom.nodes[0], id: "extra", kind: "custom" });
  assert.throws(() => validateWorkflow(custom));
  const bypass = structuredClone(defaultWorkflow);
  bypass.edges = bypass.edges.filter((e) => e.target !== "art");
  bypass.edges.push({ id: "bypass", source: "script", target: "art" });
  assert.throws(() => validateWorkflow(bypass));
});

test("credentials are encrypted in SQLite and state survives reopening", async (t) => {
  const { dir, store } = await fixture(t);
  store.setSecret("example", "TEST_SECRET_UNIQUE_791");
  assert.equal(store.secret("example"), "TEST_SECRET_UNIQUE_791");
  assert.ok(
    !JSON.stringify(store.get("secret:example")).includes(
      "TEST_SECRET_UNIQUE_791",
    ),
  );
  const reopened = new Store(join(dir, "data"));
  assert.equal(reopened.secret("example"), "TEST_SECRET_UNIQUE_791");
  assert.equal(reopened.state().runs.length, 1);
  reopened.close();
});

test("artifact access rejects traversal and symlink escape", async (t) => {
  const { dir, artifacts, run } = await fixture(t);
  await writeFile(join(dir, "outside.txt"), "outside");
  await symlink(
    join(dir, "outside.txt"),
    join(dir, "episodes", run.episode, "escape.txt"),
  );
  await assert.rejects(artifacts.path("../outside.txt"));
  await assert.rejects(artifacts.path(run.episode, "../../outside.txt"));
  await assert.rejects(artifacts.path(run.episode, "escape.txt"));
  assert.equal((await artifacts.pages(run.episode)).length, 1);
});

function metaMock(ambiguous = false) {
  let publishes = 0;
  const request = async (url: any, options: any) => {
    const path = new URL(url).pathname;
    if (path.endsWith("/media_publish")) {
      publishes++;
      if (ambiguous) throw new Error("timeout");
      return Response.json({ id: "777777" });
    }
    if (path.endsWith("/media")) return Response.json({ id: "555555" });
    if (path.endsWith("/555555"))
      return Response.json({
        status_code: publishes ? "PUBLISHED" : "FINISHED",
      });
    if (path.endsWith("/777777"))
      return Response.json({
        id: "777777",
        username: "test_account",
        permalink: "https://www.instagram.com/p/TEST_ONLY/",
      });
    throw new Error(`Unexpected test URL ${path}`);
  };
  return { request: request as typeof fetch, count: () => publishes };
}

test("posting requires current approvals and verified permalink", async (t) => {
  const { store, artifacts, run } = await fixture(t);
  const mock = metaMock();
  const instagram = new Instagram(store, artifacts, mock.request);
  await instagram.publish(run.id);
  assert.equal(mock.count(), 1);
  assert.equal(store.state().runs[0].status, "completed");
  assert.equal(store.state().runs[0].publication.phase, "verified");
  await instagram.publish(run.id);
  assert.equal(mock.count(), 1);
});

test("ambiguous posting timeout is not replayed, including after service recreation", async (t) => {
  const { store, artifacts, run } = await fixture(t);
  const mock = metaMock(true);
  const instagram = new Instagram(store, artifacts, mock.request);
  await assert.rejects(instagram.publish(run.id), PublishUncertain);
  assert.equal(store.state().runs[0].status, "publish_unknown");
  await instagram.publish(run.id);
  await new Instagram(store, artifacts, mock.request).publish(run.id);
  assert.equal(mock.count(), 1);
  assert.equal(store.state().runs[0].publication.permalink, undefined);
});

test("changed files or account cannot reuse an earlier prepared container", async (t) => {
  const { dir, store, artifacts, run } = await fixture(t);
  const mock = metaMock();
  const instagram = new Instagram(store, artifacts, mock.request);
  store.update((s) => {
    s.runs[0].publication = {
      phase: "prepared",
      children: [],
      fingerprint: run.approvals.quality,
      containerId: "old",
    };
  });
  await writeFile(join(dir, "episodes", run.episode, "caption.txt"), "수정됨");
  const hash = await artifacts.fingerprint(run.episode);
  const imageHash = await artifacts.fingerprint(run.episode, "images");
  store.update((s) => {
    s.runs[0].approvals.quality = hash;
    s.runs[0].approvals.images = imageHash;
  });
  await assert.rejects(instagram.publish(run.id), /게시 준비 후/);
  assert.equal(mock.count(), 0);
  store.update((s) => {
    s.runs[0].publication = {
      phase: "unknown",
      children: [],
      accountId: "OTHER",
      mediaId: "777777",
    };
  });
  await assert.rejects(instagram.verify(run.id), /계정/);
});

test("missing script approval blocks publishing even when image approval exists", async (t) => {
  const { store, artifacts, run } = await fixture(t);
  store.update((s) => {
    delete s.runs[0].approvals.script;
  });
  const mock = metaMock();
  await assert.rejects(
    new Instagram(store, artifacts, mock.request).publish(run.id),
    /대본/,
  );
  assert.equal(mock.count(), 0);
});

class FakeCodex extends EventEmitter {
  ready = true;
  models = defaultWorkflow.nodes
    .filter((n) => n.model !== "local")
    .map((n) => ({
      model: n.model,
      supportedReasoningEfforts: [{ reasoningEffort: n.effort }],
    }));
  message = "테스트 연결";
  calls = 0;
  interrupts = 0;
  onRun: () => Promise<string> = async () => {
    throw new Error("도구 연결 실패");
  };
  pendingRequests() {
    return [];
  }
  async thread() {
    return "test-thread";
  }
  async run() {
    this.calls++;
    return this.onRun();
  }
  async interrupt() {
    this.interrupts++;
  }
  close() {}
}
function engineFixture(f: any, codex = new FakeCodex()) {
  const push = { send: async () => ({ sent: 0, failed: 0 }) };
  const engine = new Engine(
    f.dir,
    f.store,
    codex as any,
    f.artifacts,
    new Instagram(f.store, f.artifacts, metaMock().request),
    push as any,
    () => {},
  );
  return { engine, codex };
}
async function settle(engine: any) {
  for (let i = 0; i < 100 && engine.current; i++)
    await new Promise((r) => setTimeout(r, 5));
  assert.equal(engine.current, undefined);
}

test("new production stores count choices and rejects a mismatched script before art", async (t) => {
  const f = await fixture(t);
  const { engine } = engineFixture(f);
  engine.tick = async () => {};
  const run = await engine.create({
    ...defaults,
    panelCount: 8,
    imageCount: 5,
  });
  const saved = f.store.state().runs.find((r) => r.id === run.id)!;
  assert.equal(saved.panelCount, 8);
  assert.equal(saved.imageCount, 5);
  const stage = saved.workflow.nodes.find((n) => n.kind === "script")!;
  assert.match((engine as any).task(saved, stage), /exactly 8 total panels/);
  const file = join(f.dir, "episodes", saved.episode, "script.json");
  await writeFile(
    file,
    JSON.stringify({
      output_layout: [1, 1, 1, 1, 1],
      panels: Array(5).fill({ panel: 1 }),
    }),
  );
  await assert.rejects((engine as any).ensureOutputs(saved, stage), /8컷/);
  await writeFile(
    file,
    JSON.stringify({
      output_layout: [1, 2, 1, 3, 1],
      panels: Array(8).fill({ panel: 1 }),
    }),
  );
  await (engine as any).ensureOutputs(saved, stage);
  await engine.stop();
});

test("production failure makes exactly two automatic retries and records reason", async (t) => {
  const f = await fixture(t);
  f.store.update((s) => {
    s.runs[0].status = "queued";
    s.runs[0].stages.topic.status = "waiting";
  });
  const { engine, codex } = engineFixture(f);
  await engine.tick();
  await settle(engine);
  assert.equal(codex.calls, 3);
  assert.equal(f.store.state().runs[0].status, "error");
  assert.match(f.store.state().runs[0].error!, /도구 연결 실패/);
  await engine.stop();
});

test("pause/resume preserves a pending human approval", async (t) => {
  const f = await fixture(t);
  f.store.update((s) => {
    const r = s.runs[0];
    r.status = "approval";
    r.currentStage = "content";
    r.stages.content.status = "approval";
  });
  const { engine, codex } = engineFixture(f);
  await engine.pause(f.run.id);
  engine.resume(f.run.id);
  assert.equal(f.store.state().runs[0].status, "approval");
  assert.equal(codex.calls, 0);
  await engine.stop();
});

test("reenabling review detects stale script approval and later requests image approval", async (t) => {
  const f = await fixture(t);
  f.store.update((s) => {
    const r = s.runs[0];
    r.humanReview = false;
    r.approvals.script = "old";
    delete r.approvals.images;
  });
  const { engine } = engineFixture(f);
  await engine.preferences(f.run.id, true, "manual", null);
  assert.equal(f.store.state().runs[0].currentStage, "content");
  assert.equal(f.store.state().runs[0].status, "approval");
  await engine.approve(f.run.id, await f.artifacts.fingerprint(f.run.episode));
  await settle(engine);
  assert.equal(f.store.state().runs[0].currentStage, "quality");
  assert.equal(f.store.state().runs[0].status, "approval");
  await engine.stop();
});

test("image correction keeps script approval and resets downstream QA and posting", async (t) => {
  const f = await fixture(t);
  const { engine } = engineFixture(f);
  (engine as any).tick = async () => {};
  await engine.addAnnotation(f.run.id, {
    file: "final/page-01.png",
    point: { x: 0.3, y: 0.4 },
    note: "손 모양 수정",
    revision: await f.artifacts.fingerprint(f.run.episode),
  });
  await engine.revise(f.run.id);
  const r = f.store.state().runs[0];
  assert.equal(r.approvals.script, f.run.approvals.script);
  assert.equal(r.approvals.images, undefined);
  assert.equal(r.stages.art.status, "waiting");
  assert.equal(r.stages.visual.status, "waiting");
  assert.equal(r.publication.phase, "none");
  await engine.stop();
});

test("active model change waits for interruption then resumes same thread", async (t) => {
  const f = await fixture(t);
  f.store.update((s) => {
    s.runs[0].status = "queued";
    s.runs[0].stages.topic.status = "waiting";
  });
  const { engine, codex } = engineFixture(f);
  let reject!: (e: Error) => void;
  codex.onRun = () =>
    new Promise((_, no) => {
      reject = no;
    });
  codex.interrupt = async () => {
    codex.interrupts++;
    reject(new Interrupted());
  };
  await engine.tick();
  for (let i = 0; !codex.calls && i < 100; i++)
    await new Promise((r) => setTimeout(r, 5));
  const workflow = structuredClone(defaultWorkflow);
  workflow.nodes[0].effort = "high";
  (engine as any).tick = async () => {};
  await engine.changeWorkflow(workflow);
  const r = f.store.state().runs[0];
  assert.equal(codex.interrupts, 1);
  assert.equal(r.workflow.nodes[0].effort, "high");
  assert.equal(r.stages.topic.threadId, "test-thread");
  assert.equal(r.status, "queued");
  await engine.stop();
});

test("HTTP login, CSRF, Host checks, secret redaction and workflow persistence", async (t) => {
  const dir = await mkdtemp(join(tmpdir(), "toon-http-"));
  const port = 19431;
  const service = await createApp({
    project: dir,
    appRoot: resolve("."),
    dataDir: join(dir, "data"),
    port,
    startEngine: false,
    codex: new FakeCodex() as any,
  });
  const server = service.app.listen(port, "127.0.0.1");
  await new Promise<void>((r) => server.once("listening", r));
  t.after(async () => {
    await service.close();
    await new Promise<void>((r) => server.close(() => r()));
    await rm(dir, { recursive: true, force: true });
  });
  const base = `http://127.0.0.1:${port}`;
  const headers = { "Content-Type": "application/json", "X-Toon-Desk": "1" };
  service.store.update((s) => {
    s.settings.privateUrl = "https://desk.example.ts.net";
  });
  const privateHeaders = {
    ...headers,
    Host: "desk.example.ts.net",
    Origin: "https://desk.example.ts.net",
    "X-Forwarded-Proto": "https",
    "X-Forwarded-For": "100.64.0.2",
  };
  assert.equal(
    (await fetch(base + "/api/auth", { headers: privateHeaders })).status,
    200,
  );
  assert.equal(
    (await fetch(base + "/api/state", { headers: privateHeaders })).status,
    401,
  );
  assert.equal(
    (
      await fetch(base + "/api/setup", {
        method: "POST",
        headers: privateHeaders,
        body: JSON.stringify({ password: "remote-setup-blocked" }),
      })
    ).status,
    400,
  );
  assert.equal((await fetch(base + "/api/state")).status, 401);
  assert.equal(
    (
      await fetch(base + "/api/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: "local-test-password" }),
      })
    ).status,
    403,
  );
  assert.equal(
    await new Promise<number | undefined>((done, fail) => {
      const req = httpRequest(
        base + "/api/auth",
        { headers: { Host: "evil.example" } },
        (res) => {
          res.resume();
          done(res.statusCode);
        },
      );
      req.on("error", fail);
      req.end();
    }),
    403,
  );
  const setup = await fetch(base + "/api/setup", {
    method: "POST",
    headers,
    body: JSON.stringify({ password: "local-test-password" }),
  });
  assert.equal(setup.status, 200);
  const cookie = setup.headers.get("set-cookie")!.split(";")[0];
  const remoteLogin = await fetch(base + "/api/login", {
    method: "POST",
    headers: privateHeaders,
    body: JSON.stringify({ password: "local-test-password" }),
  });
  assert.equal(remoteLogin.status, 200);
  assert.match(remoteLogin.headers.get("set-cookie")!, /Secure/);
  assert.equal(
    (
      await fetch(base + "/api/state", {
        headers: { ...privateHeaders, Cookie: cookie },
      })
    ).status,
    200,
  );
  assert.equal(service.store.state().settings.publicUrl, "");
  const state = await (
    await fetch(base + "/api/state", { headers: { Cookie: cookie } })
  ).json();
  assert.equal(state.runs.length, 0);
  assert.ok(!JSON.stringify(state).includes("local-test-password"));
  const w = structuredClone(defaultWorkflow);
  w.nodes[0].position.x = 20;
  assert.equal(
    (
      await fetch(base + "/api/workflow", {
        method: "PUT",
        headers: { ...headers, Cookie: cookie },
        body: JSON.stringify(w),
      })
    ).status,
    200,
  );
  assert.equal(
    (
      await fetch(base + "/api/workflow", {
        method: "PUT",
        headers: { ...headers, Cookie: cookie },
        body: JSON.stringify(w),
      })
    ).status,
    400,
  );
  assert.equal(
    (await fetch(base + "/api/missing", { headers: { Cookie: cookie } }))
      .status,
    404,
  );
  assert.equal(
    (
      await fetch(base + "/api/defaults", {
        method: "PUT",
        headers: { ...headers, Cookie: cookie, Origin: "https://evil.example" },
        body: JSON.stringify(defaults),
      })
    ).status,
    403,
  );
});

test("auto posting uses an overdue slot immediately, future slot waits", async (t) => {
  const f = await fixture(t);
  const { engine } = engineFixture(f);
  const sent: string[] = [];
  engine.publish = async (id: string) => {
    sent.push(id);
  };
  f.store.update((s) => {
    const r = s.runs[0];
    r.publishMode = "auto";
    r.publishAt = new Date(Date.now() - 60000).toISOString();
    r.status = "scheduled";
  });
  await engine.tick();
  assert.deepEqual(sent, [f.run.id]);
  sent.length = 0;
  f.store.update((s) => {
    s.runs[0].publishAt = new Date(Date.now() + 3600000).toISOString();
  });
  await engine.tick();
  assert.equal(sent.length, 0);
  await engine.stop();
});

test("signed media URL rejects expired and altered URLs", async (t) => {
  const { store, artifacts, run } = await fixture(t);
  const instagram = new Instagram(store, artifacts, metaMock().request);
  const expires = String(Date.now() + 3600000);
  const signature = instagram.mediaSignature(run.id, "page-1.jpg", expires);
  assert.equal(
    instagram.verifyMedia(run.id, "page-1.jpg", expires, signature),
    true,
  );
  assert.equal(
    instagram.verifyMedia(run.id, "page-2.jpg", expires, signature),
    false,
  );
  assert.equal(
    instagram.verifyMedia(
      run.id,
      "page-1.jpg",
      String(Date.now() - 1),
      signature,
    ),
    false,
  );
});

async function motionFixture(t: any) {
  const f = await fixture(t);
  await writeFile(
    join(f.dir, "episodes", f.run.episode, "review-state.json"),
    JSON.stringify({ visual_qa: "PASS", content_review: "PASS" }),
  );
  const { engine, codex } = engineFixture(f);
  engine.tick = async () => {};
  t.after(() => engine.stop());
  return { ...f, engine, codex };
}
test("motion concurrent requests reuse one job, preserve source and pin planner/producer models", async (t) => {
  const f = await motionFixture(t);
  const before = await f.artifacts.fingerprint(f.run.episode);
  const [a, b] = await Promise.all([
    f.engine.createMotion(f.run.episode),
    f.engine.createMotion(f.run.episode),
  ]);
  assert.equal(a.id, b.id);
  assert.equal(a.episode, f.run.episode);
  assert.equal(await f.artifacts.fingerprint(f.run.episode), before);
  assert.equal(
    f.store.state().runs.filter((r) => r.mode === "motion").length,
    1,
  );
  assert.deepEqual(
    a.workflow.nodes.slice(0, 3).map((n) => [n.role, n.model, n.effort]),
    [
      ["toon_motion_planner", "gpt-6-astra", "low"],
      ["toon_content_review", "gpt-6-astra", "high"],
      ["toon_motion_producer", "gpt-6.1-sol", "high"],
    ],
  );
  assert.equal(
    a.workflow.nodes.some((n) => n.kind === "publish"),
    false,
  );
  await assert.rejects(f.engine.publish(a.id), /로컬 영상/);
  await assert.rejects(
    f.engine.preferences(a.id, true, "auto", null),
    /게시 설정/,
  );
  assert.match(
    (f.engine as any).task(a, a.workflow.nodes[0]),
    /motion-direction-baseline/,
  );
});
test("motion rejects incomplete or still-working comics and stale source on resume", async (t) => {
  const f = await motionFixture(t);
  await writeFile(
    join(f.dir, "episodes", f.run.episode, "review-state.json"),
    "{}",
  );
  await assert.rejects(f.engine.createMotion(f.run.episode), /검수/);
  await writeFile(
    join(f.dir, "episodes", f.run.episode, "review-state.json"),
    JSON.stringify({ visual_qa: "PASS", content_review: "PASS" }),
  );
  f.store.update((s) => {
    s.runs[0].status = "running";
  });
  await assert.rejects(f.engine.createMotion(f.run.episode), /먼저/);
  f.store.update((s) => {
    s.runs[0].status = "ready";
  });
  const run = await f.engine.createMotion(f.run.episode);
  await writeFile(
    join(f.dir, "episodes", f.run.episode, "caption.txt"),
    "changed",
  );
  const { checkMotion } = await import("../server/motion");
  await assert.rejects(
    checkMotion(run, run.workflow.nodes[0], f.artifacts),
    /원본 에피소드가 변경/,
  );
});
test("motion plans need current independent review; changed timelines invalidate review", async (t) => {
  const f = await motionFixture(t);
  const run = await f.engine.createMotion(f.run.episode);
  const dir = join(f.dir, "episodes", run.episode, run.motionDirectory!);
  await mkdir(join(dir, "qa"), { recursive: true });
  const timeline = JSON.stringify({
    duration: 1,
    fps: 30,
    scenes: [{ start: 0, end: 1 }],
  });
  await writeFile(join(dir, "timeline.json"), timeline);
  await writeFile(join(dir, "brief.json"), "{}");
  const { checkMotion, sha256 } = await import("../server/motion");
  await checkMotion(run, run.workflow.nodes[0], f.artifacts);
  await assert.rejects(checkMotion(run, run.workflow.nodes[1], f.artifacts));
  await writeFile(
    join(dir, "qa/content-review.json"),
    JSON.stringify({
      overall: "PASS",
      reviewer_id: "independent",
      timeline_sha256: sha256(Buffer.from(timeline)),
    }),
  );
  await checkMotion(run, run.workflow.nodes[1], f.artifacts);
  await writeFile(join(dir, "timeline.json"), timeline + " ");
  await assert.rejects(
    checkMotion(run, run.workflow.nodes[1], f.artifacts),
    /독립 검수/,
  );
});
test("motion dispatch completes through four distinct worker threads and real video decode; no publish", async (t) => {
  const f = await motionFixture(t);
  const run = await f.engine.createMotion(f.run.episode);
  const dir = join(f.dir, "episodes", run.episode, run.motionDirectory!);
  const { execFile } = await import("node:child_process");
  const { promisify } = await import("node:util");
  const { sha256 } = await import("../server/motion");
  await mkdir(join(dir, "qa"), { recursive: true });
  await mkdir(join(dir, "output"));
  await promisify(execFile)("ffmpeg", [
    "-v",
    "error",
    "-f",
    "lavfi",
    "-i",
    "color=c=black:s=1080x1920:r=30:d=1",
    "-f",
    "lavfi",
    "-i",
    "anullsrc=r=48000:cl=stereo",
    "-t",
    "1",
    "-c:v",
    "libx264",
    "-preset",
    "ultrafast",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-movflags",
    "+faststart",
    join(dir, "output/video.mp4"),
  ]);
  const timeline = JSON.stringify({
    duration: 1,
    fps: 30,
    scenes: [{ start: 0, end: 1 }],
  });
  const th = sha256(Buffer.from(timeline));
  const vh = sha256(await readFile(join(dir, "output/video.mp4")));
  const calls: string[] = [];
  const threads: string[] = [];
  f.codex.thread = async () => {
    const id = `worker-${threads.length}`;
    threads.push(id);
    return id;
  };
  f.codex.run = async (_thread?: any, stage?: any) => {
    calls.push(stage.id);
    if (stage.id === "motion_plan") {
      await writeFile(join(dir, "brief.json"), "{}");
      await writeFile(join(dir, "timeline.json"), timeline);
    }
    if (stage.id === "motion_content")
      await writeFile(
        join(dir, "qa/content-review.json"),
        JSON.stringify({
          overall: "PASS",
          reviewer_id: "content-worker",
          timeline_sha256: th,
        }),
      );
    if (stage.id === "motion_produce")
      await writeFile(
        join(dir, "qa/production.json"),
        JSON.stringify({
          timeline_sha256: th,
          listening: "not_performed_test_fixture",
        }),
      );
    if (stage.id === "motion_visual")
      await writeFile(
        join(dir, "qa/visual-review.json"),
        JSON.stringify({
          overall: "PASS",
          reviewer_id: "visual-worker",
          video_sha256: vh,
          inspection: "test_fixture",
        }),
      );
    return JSON.stringify({ completed: true, summary: "test", blocker: "" });
  };
  await (f.engine as any).execute(run.id);
  assert.deepEqual(calls, [
    "motion_plan",
    "motion_content",
    "motion_produce",
    "motion_visual",
  ]);
  assert.equal(new Set(threads).size, 4);
  assert.equal(f.engine.get(run.id).status, "motion_ready");
  assert.equal(
    JSON.parse(await readFile(join(dir, "qa/final-report.json"), "utf8"))
      .full_decode,
    "no_errors",
  );
  assert.equal(f.engine.get(run.id).publication.phase, "none");
});

test("motion HTTP requires login, creates selected source and serves authenticated range/download only when ready", async (t) => {
  const dir = await mkdtemp(join(tmpdir(), "toon-motion-http-"));
  const service = await createApp({
    project: dir,
    appRoot: resolve("."),
    dataDir: join(dir, "data"),
    port: 19434,
    startEngine: false,
    codex: new FakeCodex() as any,
  });
  service.engine.tick = async () => {};
  const server = service.app.listen(19434, "127.0.0.1");
  await new Promise<void>((r) => server.once("listening", r));
  t.after(async () => {
    await service.close();
    await new Promise<void>((r) => server.close(() => r()));
    await rm(dir, { recursive: true, force: true });
  });
  const base = "http://127.0.0.1:19434";
  const headers = { "Content-Type": "application/json", "X-Toon-Desk": "1" };
  assert.equal(
    (
      await fetch(base + "/api/motion-runs", {
        method: "POST",
        headers,
        body: JSON.stringify({ episode: "EP-001-test" }),
      })
    ).status,
    401,
  );
  const setup = await fetch(base + "/api/setup", {
    method: "POST",
    headers,
    body: JSON.stringify({ password: "test-only-password" }),
  });
  const auth = {
    ...headers,
    Cookie: setup.headers.get("set-cookie")!.split(";")[0],
  };
  const episode = "EP-001-test";
  const folder = join(dir, "episodes", episode);
  await mkdir(join(folder, "final"), { recursive: true });
  await writeFile(
    join(folder, "script.json"),
    JSON.stringify({ title: "선택한 원본", panels: [{}], output_layout: [1] }),
  );
  await writeFile(join(folder, "final/page-01.png"), "fixture");
  await writeFile(
    join(folder, "review-state.json"),
    JSON.stringify({ content_review: "PASS", visual_qa: "PASS" }),
  );
  const create = () =>
    fetch(base + "/api/motion-runs", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ episode }),
    });
  const run = await (await create()).json();
  assert.equal(run.episode, episode);
  assert.equal(run.mode, "motion");
  assert.equal((await (await create()).json()).id, run.id);
  const videoUrl = base + `/api/runs/${run.id}/video`;
  assert.equal((await fetch(videoUrl)).status, 401);
  assert.equal((await fetch(videoUrl, { headers: auth })).status, 400);
  await mkdir(join(folder, run.motionDirectory, "output"), { recursive: true });
  await writeFile(
    join(folder, run.motionDirectory, "output/video.mp4"),
    "test-video-bytes",
  );
  service.store.update((s) => {
    s.runs[0].status = "motion_ready";
  });
  const range = await fetch(videoUrl, {
    headers: { ...auth, Range: "bytes=0-3" },
  });
  assert.equal(range.status, 206);
  assert.equal(await range.text(), "test");
  const download = await fetch(videoUrl + "?download=1", { headers: auth });
  assert.equal(download.status, 200);
  assert.match(download.headers.get("content-disposition")!, /attachment/);
  assert.equal(
    (
      await fetch(base + `/api/runs/${run.id}/publish`, {
        method: "POST",
        headers: auth,
        body: "{}",
      })
    ).status,
    400,
  );
});
