import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join, dirname } from "node:path";

const label = "local.instagram-toon.dashboard";
const xml = (s: string) =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
export function startupPlist(config: {
  appRoot: string;
  project: string;
  dataDir: string;
  port: number;
}) {
  const entries = {
    PATH: [
      dirname(process.execPath),
      join(homedir(), ".local/bin"),
      "/opt/homebrew/bin",
      "/usr/local/bin",
      "/usr/bin",
      "/bin",
    ].join(":"),
    NODE_ENV: "production",
    TOON_PROJECT: config.project,
    TOON_DATA: config.dataDir,
    TOON_PORT: String(config.port),
  };
  return `<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict><key>Label</key><string>${label}</string><key>ProgramArguments</key><array>${[process.execPath, "--import", "tsx", join(config.appRoot, "server/index.ts")].map((v) => `<string>${xml(v)}</string>`).join("")}</array><key>WorkingDirectory</key><string>${xml(config.appRoot)}</string><key>EnvironmentVariables</key><dict>${Object.entries(
    entries,
  )
    .map(([k, v]) => `<key>${k}</key><string>${xml(v)}</string>`)
    .join(
      "",
    )}</dict><key>RunAtLoad</key><true/><key>StandardOutPath</key><string>${xml(join(config.dataDir, "startup.log"))}</string><key>StandardErrorPath</key><string>${xml(join(config.dataDir, "startup.log"))}</string></dict></plist>\n`;
}
export class Startup {
  readonly file = join(homedir(), "Library", "LaunchAgents", label + ".plist");
  constructor(
    readonly config: {
      appRoot: string;
      project: string;
      dataDir: string;
      port: number;
    },
    readonly allowed = true,
  ) {}
  async enabled() {
    try {
      return (await readFile(this.file, "utf8")) === startupPlist(this.config);
    } catch {
      return false;
    }
  }
  async set(enabled: boolean) {
    if (!this.allowed || process.platform !== "darwin")
      throw new Error(
        "이 실행 환경에서는 Mac 자동 시작 설정을 바꿀 수 없습니다.",
      );
    const text = startupPlist(this.config);
    let existing: string | undefined;
    try {
      existing = await readFile(this.file, "utf8");
    } catch (e: any) {
      if (e.code !== "ENOENT") throw e;
    }
    if (existing && existing !== text)
      throw new Error(
        "다른 작업실의 자동 시작 설정이 있어 덮어쓰지 않았어요. 기존 설정을 먼저 확인해주세요.",
      );
    if (enabled) {
      await mkdir(dirname(this.file), { recursive: true });
      await writeFile(this.file, text, { mode: 0o600 });
    } else if (existing) await unlink(this.file);
    // Only change the next login. Never restart or stop the current service here.
  }
}
