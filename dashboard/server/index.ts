import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";
import { createApp } from "./app";
const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const project = process.env.TOON_PROJECT
  ? resolve(process.env.TOON_PROJECT)
  : resolve(appRoot, "..");
const port = Number(process.env.TOON_PORT ?? 4318);
if (!Number.isInteger(port) || port < 1024 || port > 65535)
  throw new Error("TOON_PORT 번호를 확인해주세요.");
const service = await createApp({
  appRoot,
  project,
  port,
  dataDir: process.env.TOON_DATA
    ? resolve(process.env.TOON_DATA)
    : join(appRoot, ".data"),
  development:
    process.env.NODE_ENV !== "production" && process.argv.includes("--dev"),
  startEngine: false,
  allowStartup: process.env.TOON_TEST !== "1",
});
const server = service.app.listen(port, "127.0.0.1", () => {
  if (process.env.TOON_TEST !== "1") service.engine.start();
  console.log(`툰 작업실: http://localhost:${port}`);
});
server.on("error", async (e: any) => {
  console.error(
    e.code === "EADDRINUSE"
      ? "이 주소를 다른 프로그램이 사용 중입니다. TOON_PORT로 다른 번호를 정해주세요."
      : e.message,
  );
  await service.close();
  process.exitCode = 1;
});
let closing = false;
for (const signal of ["SIGTERM", "SIGINT"] as const)
  process.on(signal, async () => {
    if (closing) return;
    closing = true;
    server.close();
    await service.close();
  });
