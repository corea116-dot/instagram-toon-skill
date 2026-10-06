import { motionFile } from "./motion";
import express from "express";
import { readFile, access } from "node:fs/promises";
import { join } from "node:path";
import sharp from "sharp";
import { z } from "zod";
import { Store, event } from "./store";
import { Artifacts } from "./artifacts";
import { Codex, safeMessage } from "./codex";
import { Instagram } from "./instagram";
import { Push } from "./push";
import { Auth } from "./auth";
import { Engine } from "./engine";
import { Startup } from "./startup";
import { optionsSchema, validateWorkflow } from "../shared/workflow";
import type { Snapshot, Stage, Schedule } from "../shared/types";

export async function createApp(config: {
  project: string;
  appRoot: string;
  dataDir: string;
  port: number;
  development?: boolean;
  startEngine?: boolean;
  allowStartup?: boolean;
  codex?: Codex;
  request?: typeof fetch;
}) {
  const store = new Store(config.dataDir);
  const artifacts = new Artifacts(config.project);
  const codex = config.codex ?? new Codex(config.project);
  const instagram = new Instagram(store, artifacts, config.request);
  const push = new Push(store);
  const auth = new Auth(store);
  const clients = new Set<express.Response>();
  let revision = 0;
  const changed = () => {
    revision++;
    for (const client of clients)
      client.write(`event: change\ndata: ${revision}\n\n`);
  };
  const engine = new Engine(
    config.project,
    store,
    codex,
    artifacts,
    instagram,
    push,
    changed,
  );
  const startup = new Startup(
    config,
    config.allowStartup ?? config.startEngine !== false,
  );
  const app = express();
  app.disable("x-powered-by");
  app.set("trust proxy", "loopback");
  app.use((req, res, next) => {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "no-referrer");
    res.setHeader("X-Frame-Options", "DENY");
    res.setHeader(
      "Content-Security-Policy",
      `default-src 'self'; script-src 'self' ${config.development ? "'unsafe-inline'" : ""}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ${config.development ? "ws:" : ""}; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`,
    );
    const { publicUrl, privateUrl } = store.state().settings;
    const remoteOrigins = [publicUrl, privateUrl].filter(Boolean) as string[];
    const host = req.headers.host ?? "";
    const allowed = new Set([
      `localhost:${config.port}`,
      `127.0.0.1:${config.port}`,
      ...remoteOrigins.map((url) => new URL(url).host),
    ]);
    if (!allowed.has(host)) {
      res.status(403).json({ error: "허용되지 않은 접속 주소입니다." });
      return;
    }
    if (req.path.startsWith("/api/"))
      res.setHeader("Cache-Control", "no-store");
    if (!["GET", "HEAD", "OPTIONS"].includes(req.method)) {
      const origin = req.headers.origin;
      const origins = new Set([
        `http://localhost:${config.port}`,
        `http://127.0.0.1:${config.port}`,
        ...remoteOrigins,
      ]);
      if (
        req.headers["x-toon-desk"] !== "1" ||
        (origin && !origins.has(origin)) ||
        !req.is("application/json")
      ) {
        res.status(403).json({ error: "작업실 화면에서 다시 시도해주세요." });
        return;
      }
    }
    next();
  });
  app.use(express.json({ limit: "250kb" }));
  app.get("/health", (_req, res) => res.json({ ok: true }));
  app.get("/api/auth", (req, res) =>
    res.json({
      setupRequired: !auth.configured(),
      authenticated: !!auth.session(req),
    }),
  );
  app.post("/api/setup", (req, res) => {
    if (auth.configured())
      throw new Error("이미 비밀번호가 설정되어 있습니다.");
    if (
      req.headers["x-forwarded-for"] ||
      req.headers["x-forwarded-host"] ||
      !/^(localhost|127\.0\.0\.1):/.test(req.headers.host ?? "") ||
      !["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(
        req.socket.remoteAddress ?? "",
      )
    )
      throw new Error("처음 비밀번호는 Mac에서 설정해주세요.");
    const { password } = z.object({ password: z.string() }).parse(req.body);
    auth.password(password);
    auth.login(req, res);
    res.json({ ok: true });
  });
  app.post("/api/login", (req, res) => {
    const { password } = z
      .object({ password: z.string().max(200) })
      .parse(req.body);
    auth.verify(password, req.ip ?? "local");
    auth.login(req, res);
    res.json({ ok: true });
  });
  app.post("/api/logout", (req, res) => {
    auth.logout(req, res);
    res.json({ ok: true });
  });
  app.get("/media/:run/:file", async (req, res) => {
    const run = String(req.params.run),
      file = String(req.params.file);
    if (
      !instagram.verifyMedia(
        run,
        file,
        String(req.query.expires ?? ""),
        String(req.query.sig ?? ""),
      )
    ) {
      res.status(403).end();
      return;
    }
    res.setHeader("Cache-Control", "private, max-age=600");
    res.sendFile(instagram.mediaPath(run, file));
  });
  app.get("/privacy", (_req, res) =>
    res
      .type("html")
      .send(
        '<!doctype html><html lang="ko"><meta charset="utf-8"><title>툰 작업실 개인정보 안내</title><h1>개인용 툰 작업실</h1><p>연결된 인스타그램 계정 정보와 게시 권한은 이 Mac에 암호화해 보관합니다. 사용자가 선택한 결과물만 인스타그램에 전송합니다. 휴대폰 알림을 허용하면 Apple 등 브라우저의 알림 서비스를 사용합니다.</p><p>대시보드의 계정 연결 해제를 누르면 저장된 계정 연결 정보가 제거됩니다. 인스타그램의 앱 및 웹사이트 설정에서 권한도 철회할 수 있습니다.</p></html>',
      ),
  );
  app.use("/api", (req, res, next) => {
    if (!auth.session(req)) {
      res.status(401).json({ error: "먼저 로그인해주세요." });
      return;
    }
    next();
  });
  app.get("/api/state", async (_req, res) => {
    const state = store.state();
    state.settings.autoStart = await startup.enabled();
    const snapshot: Snapshot = {
      ...state,
      library: await artifacts.list(),
      account: instagram.account(),
      connection: {
        codex: codex.ready,
        checking: false,
        message: codex.message,
        models: codex.models,
        instagramReady: instagram.ready(),
        remoteReady: !!(state.settings.publicUrl || state.settings.privateUrl),
        pushReady: !!state.settings.publicUrl,
      },
      pendingRequests: codex.pendingRequests(),
      now: new Date().toISOString(),
    };
    res.json(snapshot);
  });
  app.get("/api/events", (req, res) => {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });
    res.write("event: change\ndata: connected\n\n");
    clients.add(res);
    const timer = setInterval(() => res.write(": heartbeat\n\n"), 20_000);
    req.on("close", () => {
      clearInterval(timer);
      clients.delete(res);
    });
  });
  app.post("/api/codex/connect", async (_req, res) => {
    await codex.connect();
    res.json({ ok: true });
    changed();
  });
  app.post("/api/requests/:id", (req, res) => {
    const input = z
      .object({ allow: z.boolean(), answers: z.record(z.string()).optional() })
      .parse(req.body);
    codex.answer(String(req.params.id), input.allow, input.answers);
    res.json({ ok: true });
  });
  app.get("/api/episodes/:id", async (req, res) =>
    res.json(await artifacts.detail(String(req.params.id))),
  );
  app.get("/api/episodes/:id/image", async (req, res) => {
    const file = String(req.query.file ?? "");
    if (!/^page[-_]?\d+\.(png|jpe?g)$/i.test(file))
      throw new Error("이미지 파일 이름을 확인해주세요.");
    const path = await artifacts.path(String(req.params.id), "final/" + file);
    res.setHeader("Cache-Control", "private, max-age=30");
    if (req.query.thumb === "1") {
      res
        .type("image/webp")
        .send(
          await sharp(path)
            .resize({ width: 480, withoutEnlargement: true })
            .webp({ quality: 75 })
            .toBuffer(),
        );
    } else res.sendFile(path);
  });
  app.post("/api/motion-runs", async (req, res) => {
    const { episode } = z
      .object({ episode: z.string().regex(/^EP-[\p{L}\p{N}_-]+$/u) })
      .parse(req.body);
    res.json(await engine.createMotion(episode));
  });
  app.get("/api/runs/:id/video", async (req, res) => {
    const run = engine.get(String(req.params.id));
    if (run.mode !== "motion" || run.status !== "motion_ready")
      throw new Error("완성된 영상을 기다려주세요.");
    const file = await artifacts.path(
      run.episode,
      motionFile(run, "output/video.mp4"),
    );
    res.setHeader("Cache-Control", "private, no-store");
    if (req.query.download === "1")
      res.download(file, `${run.episode}-motion.mp4`);
    else res.sendFile(file);
  });
  app.post("/api/runs", async (req, res) =>
    res.json(await engine.create(optionsSchema.parse(req.body))),
  );
  app.post("/api/runs/:id/pause", async (req, res) => {
    await engine.pause(String(req.params.id));
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/resume", (req, res) => {
    engine.resume(String(req.params.id));
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/approve", async (req, res) => {
    const { fingerprint } = z
      .object({ fingerprint: z.string().length(64) })
      .parse(req.body);
    await engine.approve(String(req.params.id), fingerprint);
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/publish", async (req, res) => {
    await engine.publish(String(req.params.id));
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/verify", async (req, res) => {
    await instagram.verify(String(req.params.id));
    changed();
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/reconcile", async (req, res) => {
    await instagram.reconcile(
      String(req.params.id),
      z.object({ mediaId: z.string() }).parse(req.body).mediaId,
    );
    changed();
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/preferences", async (req, res) => {
    const input = z
      .object({
        humanReview: z.boolean(),
        publishMode: z.enum(["manual", "auto"]),
        publishAt: z.string().datetime().nullable(),
      })
      .parse(req.body);
    await engine.preferences(
      String(req.params.id),
      input.humanReview,
      input.publishMode,
      input.publishAt,
    );
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/annotations", async (req, res) => {
    const input = z
      .object({
        file: z.string(),
        quote: z.string().max(3000).optional(),
        point: z
          .object({ x: z.number().min(0).max(1), y: z.number().min(0).max(1) })
          .optional(),
        note: z.string().trim().min(1).max(3000),
        revision: z.string().length(64),
      })
      .parse(req.body);
    await engine.addAnnotation(String(req.params.id), input);
    res.json({ ok: true });
  });
  app.post("/api/runs/:id/revise", async (req, res) => {
    await engine.revise(String(req.params.id));
    res.json({ ok: true });
  });
  app.put("/api/workflow", async (req, res) => {
    const w = validateWorkflow(req.body);
    if (codex.ready)
      for (const n of w.nodes.filter((n) => n.model !== "local"))
        if (
          !codex.models.some(
            (m) =>
              m.model === n.model &&
              m.supportedReasoningEfforts.some(
                (e) => e.reasoningEffort === n.effort,
              ),
          )
        )
          throw new Error(
            "현재 사용할 수 있는 모델과 생각하는 깊이를 선택해주세요.",
          );
    await engine.changeWorkflow(w);
    res.json({ ok: true });
  });
  let suggesting = false;
  app.post("/api/workflow/suggest", async (req, res) => {
    if (suggesting) throw new Error("앞서 요청한 변경안을 만들고 있어요.");
    const { message } = z
      .object({ message: z.string().trim().min(1).max(3000) })
      .parse(req.body);
    suggesting = true;
    try {
      const state = store.state();
      const stage: Stage = {
        ...state.settings.workflow.nodes[0],
        role: "작업 설정 도우미",
        model: "gpt-6.1-sol",
        effort: "medium",
      };
      const thread = await codex.thread(
        stage,
        "Return a JSON workflow configuration only. Do not use tools, read files, alter files, contact external services, or publish. You are a configuration assistant. Preserve all required QA stages and order. The request is to propose a reviewable configuration.",
        undefined,
        true,
      );
      const text = await codex.run(
        thread,
        stage,
        `Current workflow: ${JSON.stringify(state.settings.workflow)}\nAvailable models: ${JSON.stringify(codex.models)}\nUser request: ${message}\nReturn only the entire workflow JSON object. Keep version unchanged, node property names and required stages. Stage kinds: topic,script,content_review,art,visual_review,quality,publish,custom. Local quality/publish nodes must remain local with no instructions.`,
        "configuration",
      );
      res.json({ workflow: validateWorkflow(JSON.parse(text)) });
    } finally {
      suggesting = false;
    }
  });
  app.put("/api/defaults", (req, res) => {
    const options = optionsSchema.parse(req.body);
    store.update((s) => {
      s.settings.defaults = options;
    });
    changed();
    res.json({ ok: true });
  });
  const scheduleSchema = z.object({
    label: z.string().trim().min(1).max(60),
    enabled: z.boolean(),
    time: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/),
    publishTime: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/),
    days: z.array(z.number().int().min(0).max(6)).min(1).max(7),
    options: z
      .preprocess(
        (value) =>
          value && typeof value === "object" && !Array.isArray(value)
            ? { ...value, publishAt: null }
            : value,
        optionsSchema,
      )
      .transform(({ publishAt, ...options }) => options),
  });
  app.post("/api/schedules", (req, res) => {
    const input = scheduleSchema.parse(req.body);
    const schedule: Schedule = {
      ...input,
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      lastSlot: null,
    };
    store.update((s) => {
      s.schedules.push(schedule);
      event(s, "제작 예약을 저장했습니다.");
    });
    changed();
    res.json(schedule);
  });
  app.put("/api/schedules/:id", (req, res) => {
    const input = scheduleSchema.parse(req.body);
    store.update((s) => {
      const saved = s.schedules.find((x) => x.id === req.params.id);
      if (!saved) throw new Error("예약을 찾지 못했습니다.");
      Object.assign(saved, input);
      event(s, "제작 예약을 바꿨습니다.");
    });
    changed();
    res.json({ ok: true });
  });
  app.delete("/api/schedules/:id", (req, res) => {
    store.update((s) => {
      s.schedules = s.schedules.filter((x) => x.id !== req.params.id);
    });
    changed();
    res.json({ ok: true });
  });
  app.post("/api/settings/connection", (req, res) => {
    const input = z
      .object({
        publicUrl: z.string().max(500),
        appId: z.string().max(100).optional(),
        appSecret: z.string().max(1000).optional(),
        graphVersion: z
          .string()
          .regex(/^v\d{2}\.0$/)
          .optional(),
      })
      .parse(req.body);
    let base = "";
    if (input.publicUrl) {
      const url = new URL(input.publicUrl);
      if (
        url.protocol !== "https:" ||
        url.username ||
        url.password ||
        url.pathname !== "/" ||
        url.search ||
        url.hash
      )
        throw new Error("https로 시작하는 대시보드 주소만 입력해주세요.");
      base = url.origin;
    }
    if (input.appId && input.appSecret)
      store.setSecret("instagram-app", {
        appId: input.appId,
        appSecret: input.appSecret,
      });
    store.update((s) => {
      s.settings.publicUrl = base;
      if (input.graphVersion) s.settings.graphVersion = input.graphVersion;
    });
    changed();
    res.json({ ok: true });
  });
  app.post("/api/settings/startup", async (req, res) => {
    const { enabled } = z.object({ enabled: z.boolean() }).parse(req.body);
    await startup.set(enabled);
    store.update((s) => {
      s.settings.autoStart = enabled;
    });
    changed();
    res.json({ ok: true });
  });
  app.post("/api/instagram/connect", (req, res) =>
    res.json({ url: instagram.beginConnect(auth.session(req)!) }),
  );
  app.get("/api/instagram/callback", async (req, res) => {
    try {
      await instagram.callback(
        String(req.query.code ?? ""),
        String(req.query.state ?? ""),
        auth.session(req)!,
      );
      changed();
      res.redirect("/?connected=instagram");
    } catch {
      res.redirect("/?connectionError=1");
    }
  });
  app.post("/api/instagram/disconnect", (_req, res) => {
    if (
      store
        .state()
        .runs.some((r) => ["publishing", "publish_unknown"].includes(r.status))
    )
      throw new Error("게시 여부를 확인한 뒤 연결을 해제해주세요.");
    store.remove("secret:instagram");
    store.update((s) => {
      for (const r of s.runs)
        if (
          ["ready", "scheduled"].includes(r.status) &&
          r.publishMode === "auto"
        )
          r.error = "계정 연결을 해제해 자동 게시가 멈췄습니다.";
    });
    changed();
    res.json({ ok: true });
  });
  app.get("/api/push/key", (_req, res) => res.json({ key: push.publicKey() }));
  app.post("/api/push/subscribe", (req, res) => {
    const sub = z
      .object({
        endpoint: z.string().url(),
        keys: z.object({
          p256dh: z.string().max(200),
          auth: z.string().max(100),
        }),
      })
      .parse(req.body);
    push.subscribe(sub);
    res.json({ ok: true });
  });
  app.post("/api/push/test", async (_req, res) => {
    const result = await push.send(
      "툰 작업실 알림",
      "휴대폰 알림 연결을 확인하고 있어요.",
    );
    if (!result.sent)
      throw new Error(
        "알림을 보내지 못했어요. 외부 접속 주소와 이 기기의 알림 허용을 확인해주세요.",
      );
    res.json({ ok: true, ...result });
  });
  app.use("/api", (_req, res) =>
    res.status(404).json({ error: "해당 기능을 찾지 못했습니다." }),
  );
  app.use(express.static(join(config.appRoot, "public")));
  if (config.development) {
    const { createServer } = await import("vite");
    const vite = await createServer({
      root: config.appRoot,
      server: { middlewareMode: true },
      appType: "custom",
    });
    app.use(vite.middlewares);
    app.get("/{*path}", async (req, res) => {
      const html = await vite.transformIndexHtml(
        req.originalUrl,
        await readFile(join(config.appRoot, "index.html"), "utf8"),
      );
      res.type("html").send(html);
    });
  } else {
    await access(join(config.appRoot, "dist", "index.html"));
    app.use(express.static(join(config.appRoot, "dist")));
    app.get("/{*path}", (_req, res) =>
      res.sendFile(join(config.appRoot, "dist", "index.html")),
    );
  }
  app.use(
    (
      err: any,
      _req: express.Request,
      res: express.Response,
      _next: express.NextFunction,
    ) => {
      if (res.headersSent) return;
      const error =
        err instanceof z.ZodError
          ? (err.issues[0]?.message ?? "입력값을 확인해주세요.")
          : safeMessage(err);
      res.status(400).json({ error });
    },
  );
  if (config.startEngine !== false) engine.start();
  return {
    app,
    store,
    engine,
    codex,
    instagram,
    close: async () => {
      push.stop();
      await engine.stop();
      for (const client of clients) client.end();
      store.close();
    },
  };
}
