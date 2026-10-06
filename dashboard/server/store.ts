import { DatabaseSync } from "node:sqlite";
import {
  mkdirSync,
  chmodSync,
  existsSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { randomBytes, createCipheriv, createDecipheriv } from "node:crypto";
import type { State, Event } from "../shared/types";
import { defaultWorkflow, defaults } from "../shared/workflow";

export class Store {
  db: DatabaseSync;
  private key: Buffer;
  constructor(readonly directory: string) {
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    chmodSync(directory, 0o700);
    const keyPath = join(directory, "local.key");
    if (!existsSync(keyPath))
      writeFileSync(keyPath, randomBytes(32), { mode: 0o600, flag: "wx" });
    this.key = readFileSync(keyPath);
    this.db = new DatabaseSync(join(directory, "desk.sqlite"));
    chmodSync(join(directory, "desk.sqlite"), 0o600);
    this.db.exec(
      "PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);",
    );
    if (!this.get("state"))
      this.set("state", {
        settings: {
          workflow: defaultWorkflow,
          defaults,
          publicUrl: "",
          graphVersion: "v25.0",
          autoStart: false,
        },
        runs: [],
        schedules: [],
        events: [],
      } satisfies State);
  }
  get<T>(key: string): T | null {
    const row = this.db.prepare("SELECT value FROM kv WHERE key=?").get(key) as
      | { value: string }
      | undefined;
    return row ? JSON.parse(row.value) : null;
  }
  set(key: string, value: unknown) {
    this.db
      .prepare(
        "INSERT INTO kv VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
      )
      .run(key, JSON.stringify(value));
  }
  remove(key: string) {
    this.db.prepare("DELETE FROM kv WHERE key=?").run(key);
  }
  state(): State {
    return this.get<State>("state")!;
  }
  update(fn: (state: State) => void) {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const state = this.state();
      fn(state);
      this.set("state", state);
      this.db.exec("COMMIT");
      return state;
    } catch (error) {
      this.db.exec("ROLLBACK");
      throw error;
    }
  }
  secret<T>(name: string): T | null {
    const value = this.get<{ iv: string; tag: string; data: string }>(
      `secret:${name}`,
    );
    if (!value) return null;
    const decipher = createDecipheriv(
      "aes-256-gcm",
      this.key,
      Buffer.from(value.iv, "base64"),
    );
    decipher.setAuthTag(Buffer.from(value.tag, "base64"));
    return JSON.parse(
      Buffer.concat([
        decipher.update(Buffer.from(value.data, "base64")),
        decipher.final(),
      ]).toString(),
    );
  }
  setSecret(name: string, data: unknown) {
    const iv = randomBytes(12);
    const cipher = createCipheriv("aes-256-gcm", this.key, iv);
    const encrypted = Buffer.concat([
      cipher.update(JSON.stringify(data)),
      cipher.final(),
    ]);
    this.set(`secret:${name}`, {
      iv: iv.toString("base64"),
      tag: cipher.getAuthTag().toString("base64"),
      data: encrypted.toString("base64"),
    });
  }
  close() {
    this.db.close();
  }
}
export function event(
  state: State,
  message: string,
  runId?: string,
  type = "info",
) {
  const value: Event = {
    id: crypto.randomUUID(),
    at: new Date().toISOString(),
    message,
    runId,
    type,
  };
  state.events.unshift(value);
  state.events = state.events.slice(0, 600);
}
