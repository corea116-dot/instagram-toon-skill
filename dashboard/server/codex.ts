import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";
import { EventEmitter } from "node:events";
import type { Model, Stage, PendingRequest } from "../shared/types";

type Rpc = {
  id?: number | string;
  method?: string;
  params?: any;
  result?: any;
  error?: { code?: number; message: string };
};
export class Interrupted extends Error {
  constructor() {
    super("작업을 잠시 멈췄습니다.");
  }
}
export function safeMessage(error: unknown) {
  return String(error instanceof Error ? error.message : error)
    .replace(
      /(access_token|client_secret|authorization|api[_-]?key)(["'\s:=]+)[^\s&,"'}]+/gi,
      "$1$2[숨김]",
    )
    .slice(0, 1000);
}

export class Codex extends EventEmitter {
  private process?: ChildProcessWithoutNullStreams;
  private opening?: Promise<void>;
  private sequence = 0;
  private pending = new Map<
    number,
    {
      resolve: (v: any) => void;
      reject: (e: Error) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  >();
  private turns = new Map<
    string,
    {
      resolve: (v: string) => void;
      reject: (e: Error) => void;
      text: string;
      id?: string;
      runId: string;
    }
  >();
  private requests = new Map<string, { rpc: Rpc; runId: string }>();
  private loaded = new Set<string>();
  models: Model[] = [];
  ready = false;
  message = "Codex 연결을 확인해주세요.";
  constructor(
    readonly cwd: string,
    readonly binary = "codex",
  ) {
    super();
  }
  async connect() {
    if (this.ready) return;
    if (this.opening) return this.opening;
    this.opening = this.open().finally(() => {
      this.opening = undefined;
    });
    return this.opening;
  }
  private async open() {
    if (this.process) this.process.kill();
    // Review ordinary tool approvals automatically for dashboard-owned sessions.
    // Keep sandbox boundaries and human artifact reviews intact.
    const proc = spawn(this.binary, ["app-server", "--stdio", "-c", 'approvals_reviewer="auto_review"'], {
      cwd: this.cwd,
      stdio: "pipe",
    });
    this.process = proc;
    proc.stderr.on("data", () => {}); // Server diagnostics can contain private paths; never forward raw stderr.
    proc.on("error", (e) => this.disconnected(safeMessage(e)));
    proc.on("exit", () => {
      if (this.process === proc) {
        this.process = undefined;
        this.disconnected("Codex 연결이 끊겼습니다. 다시 연결해주세요.");
      }
    });
    createInterface({ input: proc.stdout }).on("line", (line) => {
      try {
        this.onMessage(JSON.parse(line));
      } catch {
        /* ignore non-protocol lines */
      }
    });
    try {
      await this.call("initialize", {
        clientInfo: { name: "toon_desk", title: "툰 작업실", version: "0.1.0" },
        capabilities: { experimentalApi: true },
      });
      this.send({ method: "initialized", params: {} });
      const catalog = await this.call("model/list", { limit: 100 });
      this.models = (catalog.data ?? [])
        .filter((m: any) => !m.hidden)
        .map((m: any) => ({
          model: m.model,
          displayName: m.displayName,
          supportedReasoningEfforts: m.supportedReasoningEfforts,
        }));
      this.ready = true;
      this.message = "이 Mac의 Codex에 연결됐습니다.";
      this.emit("status");
    } catch (e) {
      this.disconnected(safeMessage(e));
      proc.kill();
      throw e;
    }
  }
  private disconnected(message: string) {
    this.ready = false;
    this.message = message;
    this.loaded.clear();
    for (const entry of this.pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(new Error(message));
    }
    this.pending.clear();
    for (const entry of this.turns.values()) entry.reject(new Error(message));
    this.turns.clear();
    this.requests.clear();
    this.emit("status");
  }
  private send(value: Rpc) {
    if (!this.process?.stdin.writable)
      throw new Error("Codex에 연결되어 있지 않습니다.");
    this.process.stdin.write(`${JSON.stringify(value)}\n`);
  }
  call(method: string, params: any = {}): Promise<any> {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Codex 응답이 늦습니다. (${method})`));
      }, 60_000);
      this.pending.set(id, { resolve, reject, timer });
      try {
        this.send({ id, method, params });
      } catch (e) {
        clearTimeout(timer);
        this.pending.delete(id);
        reject(e);
      }
    });
  }
  private onMessage(msg: Rpc) {
    if (msg.id !== undefined && !msg.method) {
      const pending = this.pending.get(Number(msg.id));
      if (pending) {
        clearTimeout(pending.timer);
        this.pending.delete(Number(msg.id));
        msg.error
          ? pending.reject(new Error(safeMessage(msg.error.message)))
          : pending.resolve(msg.result);
      }
      return;
    }
    const p = msg.params ?? {};
    const active = this.turns.get(p.threadId);
    if (msg.id !== undefined && msg.method) {
      if (!active) {
        this.send({
          id: msg.id,
          error: {
            code: -32601,
            message: "이 대시보드에서 시작한 작업이 아닙니다.",
          },
        });
        return;
      }
      const id = String(msg.id);
      this.requests.set(id, { rpc: msg, runId: active.runId });
      this.emit("request");
      return;
    }
    if (!active) return;
    if (msg.method === "turn/started") {
      active.id = p.turn.id;
      this.emit("turn", {
        runId: active.runId,
        threadId: p.threadId,
        turnId: p.turn.id,
      });
    }
    if (msg.method === "item/completed" && p.item?.type === "agentMessage")
      active.text = p.item.text ?? active.text;
    if (msg.method === "item/started") {
      const words: Record<string, string> = {
        commandExecution: "필요한 파일과 자료를 처리하고 있어요.",
        fileChange: "결과 파일을 저장하고 있어요.",
        mcpToolCall: "연결된 도구로 작업하고 있어요.",
        webSearch: "자료를 확인하고 있어요.",
        imageGeneration: "그림을 만들고 있어요.",
        agentMessage: "작업 내용을 정리하고 있어요.",
      };
      if (words[p.item?.type])
        this.emit("progress", {
          runId: active.runId,
          message: words[p.item.type],
        });
    }
    if (msg.method === "turn/completed") {
      this.turns.delete(p.threadId);
      for (const [id, req] of this.requests)
        if (req.rpc.params?.threadId === p.threadId) this.requests.delete(id);
      this.emit("request");
      if (p.turn.status === "completed") active.resolve(active.text);
      else if (p.turn.status === "interrupted")
        active.reject(new Interrupted());
      else
        active.reject(
          new Error(
            safeMessage(
              p.turn.error?.message ?? "Codex 작업을 마치지 못했습니다.",
            ),
          ),
        );
    }
  }
  async thread(
    stage: Stage,
    instructions: string,
    id?: string,
    readOnly = false,
  ): Promise<string> {
    await this.connect();
    if (
      !this.models.some(
        (m) =>
          m.model === stage.model &&
          m.supportedReasoningEfforts.some(
            (e) => e.reasoningEffort === stage.effort,
          ),
      )
    )
      throw new Error(
        "선택한 모델과 생각하는 깊이를 현재 Codex에서 사용할 수 없습니다. 도우미 설정을 바꿔주세요.",
      );
    if (id && this.loaded.has(id)) return id;
    const params = {
      cwd: this.cwd,
      model: stage.model,
      approvalPolicy: "on-request",
      approvalsReviewer: "auto_review",
      sandbox: readOnly ? "read-only" : "workspace-write",
      developerInstructions: instructions,
    };
    const result = id
      ? await this.call("thread/resume", {
          ...params,
          threadId: id,
          excludeTurns: true,
        })
      : await this.call("thread/start", params);
    const threadId = result.thread.id;
    this.loaded.add(threadId);
    return threadId;
  }
  async run(
    threadId: string,
    stage: Stage,
    prompt: string,
    runId: string,
    schema?: object,
  ): Promise<string> {
    if (this.turns.has(threadId))
      throw new Error("같은 도우미가 이미 작업하고 있습니다.");
    let resolve!: (v: string) => void;
    let reject!: (e: Error) => void;
    const done = new Promise<string>((yes, no) => {
      resolve = yes;
      reject = no;
    });
    // Attach a handler before the RPC returns: the turn may fail before turn/start resolves.
    done.catch(() => {});
    this.turns.set(threadId, { resolve, reject, text: "", runId });
    try {
      const result = await this.call("turn/start", {
        threadId,
        approvalsReviewer: "auto_review",
        model: stage.model,
        effort: stage.effort,
        input: [{ type: "text", text: prompt, text_elements: [] }],
        ...(schema ? { outputSchema: schema } : {}),
      });
      const current = this.turns.get(threadId);
      if (current) {
        current.id = result.turn.id;
        this.emit("turn", { runId, threadId, turnId: result.turn.id });
      }
    } catch (e) {
      this.turns.delete(threadId);
      reject(e as Error);
    }
    return done;
  }
  async interrupt(runId: string) {
    for (const [threadId, turn] of this.turns)
      if (turn.runId === runId) {
        // turn/started can arrive just after a stop click; wait for the accepted turn id.
        for (let i = 0; !turn.id && this.turns.has(threadId) && i < 100; i++)
          await new Promise((r) => setTimeout(r, 50));
        if (turn.id && this.turns.has(threadId))
          await this.call("turn/interrupt", { threadId, turnId: turn.id });
      }
  }
  pendingRequests(): PendingRequest[] {
    return [...this.requests].map(([id, { rpc, runId }]) => ({
      id,
      runId,
      method: rpc.method!,
      title: rpc.method?.includes("requestUserInput")
        ? "도우미가 답변을 기다려요"
        : "진행에 확인이 필요해요",
      detail: safeMessage(
        rpc.params?.reason ??
          rpc.params?.message ??
          rpc.params?.command ??
          "이 작업을 허용할지 확인해주세요.",
      ),
      questions: rpc.params?.questions,
    }));
  }
  answer(id: string, allow: boolean, answers?: Record<string, string>) {
    const entry = this.requests.get(id);
    if (!entry) throw new Error("이미 처리됐거나 끝난 요청입니다.");
    const { rpc } = entry;
    let result: unknown;
    if (rpc.method?.includes("requestUserInput"))
      result = {
        answers: Object.fromEntries(
          (rpc.params?.questions ?? []).map((q: any) => [
            q.id,
            {
              answers: [
                answers?.[q.id] ?? (allow ? "진행해주세요." : "취소해주세요."),
              ],
            },
          ]),
        ),
      };
    else if (rpc.method?.includes("permissions/requestApproval")) {
      if (allow)
        throw new Error(
          "추가 권한의 범위를 여기서 확인할 수 없어 허용하지 않았어요. 거절 후 Codex에서 확인해주세요.",
        );
      // Permission-profile elevation is never granted by a generic Yes button.
      result = { permissions: {}, scope: "turn" };
    } else if (rpc.method?.includes("elicitation")) {
      if (allow)
        throw new Error(
          "이 추가 입력은 대시보드에서 처리할 수 없습니다. 거절 후 Codex에서 확인해주세요.",
        );
      result = { action: "decline", content: null };
    } else if (rpc.method?.includes("requestApproval"))
      result = { decision: allow ? "accept" : "decline" };
    else
      throw new Error(
        "이 요청은 대시보드에서 처리할 수 없습니다. 작업을 멈추고 Codex에서 확인해주세요.",
      );
    this.send({ id: rpc.id, result });
    this.requests.delete(id);
    this.emit("request");
  }
  close() {
    this.process?.kill();
  }
}
