import {
  createHash,
  randomBytes,
  scryptSync,
  timingSafeEqual,
} from "node:crypto";
import type { Request, Response } from "express";
import { Store } from "./store";

export class Auth {
  private attempts = new Map<string, { count: number; until: number }>();
  constructor(readonly store: Store) {}
  configured() {
    return !!this.store.secret("password");
  }
  password(value: string) {
    if (value.length < 10 || value.length > 200)
      throw new Error("비밀번호는 10자 이상으로 정해주세요.");
    const salt = randomBytes(16).toString("hex");
    this.store.setSecret("password", {
      salt,
      hash: scryptSync(value, salt, 64).toString("hex"),
    });
  }
  verify(password: string, ip: string) {
    const now = Date.now();
    const rate = this.attempts.get(ip);
    if (rate && rate.until > now && rate.count >= 6)
      throw new Error("잠시 쉬었다가 10분 뒤 다시 로그인해주세요.");
    const record = this.store.secret<{ salt: string; hash: string }>(
      "password",
    );
    const valid =
      !!record &&
      password.length <= 200 &&
      timingSafeEqual(
        scryptSync(password, record.salt, 64),
        Buffer.from(record.hash, "hex"),
      );
    if (!valid) {
      this.attempts.set(ip, {
        count: rate && rate.until > now ? rate.count + 1 : 1,
        until: now + 600_000,
      });
      throw new Error("비밀번호를 다시 확인해주세요.");
    }
    this.attempts.delete(ip);
  }
  session(req: Request) {
    const raw = req.headers.cookie
      ?.split(";")
      .map((s) => s.trim())
      .find((s) => s.startsWith("toon_session="))
      ?.slice("toon_session=".length);
    if (!raw || !/^[a-f0-9]{64}$/.test(raw)) return null;
    const id = createHash("sha256").update(raw).digest("hex");
    const record = this.store.get<{ until: number }>(`session:${id}`);
    if (!record || record.until < Date.now()) return null;
    return id;
  }
  login(req: Request, res: Response) {
    const raw = randomBytes(32).toString("hex");
    const id = createHash("sha256").update(raw).digest("hex");
    this.store.set(`session:${id}`, { until: Date.now() + 30 * 86400_000 });
    res.cookie("toon_session", raw, {
      httpOnly: true,
      sameSite: "lax",
      secure: req.secure,
      path: "/",
      maxAge: 30 * 86400_000,
    });
    return id;
  }
  logout(req: Request, res: Response) {
    const session = this.session(req);
    if (session) this.store.remove(`session:${session}`);
    res.clearCookie("toon_session", { path: "/" });
  }
}
