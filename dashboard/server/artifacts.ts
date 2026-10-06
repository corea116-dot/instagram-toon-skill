import { readdir, readFile, realpath, stat, mkdir } from "node:fs/promises";
import { join, resolve, sep } from "node:path";
import { createHash } from "node:crypto";
import type { Episode, EpisodeDetail } from "../shared/types";

export class Artifacts {
  readonly root: string;
  constructor(project: string) {
    this.root = join(project, "episodes");
  }
  async path(episode: string, file = "") {
    if (!/^EP-[\p{L}\p{N}_-]+$/u.test(episode))
      throw new Error("결과물 이름을 확인해주세요.");
    const base = await realpath(this.root);
    const target = await realpath(resolve(base, episode, file));
    if (
      !target.startsWith(base + sep) ||
      (file && !target.startsWith(join(base, episode) + sep))
    )
      throw new Error("허용된 결과물 경로가 아닙니다.");
    return target;
  }
  async json(episode: string, file: string): Promise<any | null> {
    try {
      return JSON.parse(await readFile(await this.path(episode, file), "utf8"));
    } catch {
      return null;
    }
  }
  async text(episode: string, file: string): Promise<string> {
    try {
      return await readFile(await this.path(episode, file), "utf8");
    } catch {
      return "";
    }
  }
  async pages(episode: string) {
    try {
      return (await readdir(await this.path(episode, "final")))
        .filter((n) => /^page[-_]?\d+\.(png|jpe?g)$/i.test(n))
        .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    } catch {
      return [];
    }
  }
  async list(): Promise<Episode[]> {
    await mkdir(this.root, { recursive: true });
    const entries = (await readdir(this.root, { withFileTypes: true })).filter(
      (e) => e.isDirectory() && /^EP-[\p{L}\p{N}_-]+$/u.test(e.name),
    );
    const results = await Promise.all(
      entries.map(async (entry) => {
        const script = await this.json(entry.name, "script.json");
        const pages = await this.pages(entry.name);
        const review = await this.json(entry.name, "review-state.json");
        return {
          id: entry.name,
          title: script?.title ?? entry.name,
          pages,
          modifiedAt: (
            await stat(await this.path(entry.name))
          ).mtime.toISOString(),
          scriptReady: !!script,
          motionReady: await this.motionReady(
            entry.name,
            script,
            pages,
            review,
          ),
          qaRecorded:
            review?.visual_qa === "PASS" && review?.content_review === "PASS",
        };
      }),
    );
    return results.sort((a, b) =>
      b.id.localeCompare(a.id, undefined, { numeric: true }),
    );
  }
  async fingerprint(
    episode: string,
    kind: "script" | "images" | "all" = "all",
  ) {
    const hash = createHash("sha256");
    const files =
      kind === "script"
        ? ["script.json"]
        : [
            "script.json",
            "caption.txt",
            ...(await this.pages(episode)).map((n) => "final/" + n),
          ];
    if (kind === "all")
      files.push(
        "content-review.json",
        "content-lock.json",
        "visual-review.json",
        "layout-preflight.json",
      );
    for (const file of files) {
      hash.update(file);
      try {
        hash.update(await readFile(await this.path(episode, file)));
      } catch {
        hash.update("MISSING");
      }
    }
    return hash.digest("hex");
  }
  async detail(episode: string): Promise<EpisodeDetail> {
    const script = await this.json(episode, "script.json");
    const pages = await this.pages(episode);
    const review = await this.json(episode, "review-state.json");
    return {
      id: episode,
      title: script?.title ?? episode,
      pages,
      modifiedAt: (await stat(await this.path(episode))).mtime.toISOString(),
      scriptReady: !!script,
      motionReady: await this.motionReady(episode, script, pages, review),
      qaRecorded:
        review?.visual_qa === "PASS" && review?.content_review === "PASS",
      script,
      caption: await this.text(episode, "caption.txt"),
      report: await this.text(episode, "qa-report.md"),
      fingerprint: await this.fingerprint(episode),
    };
  }
  private async motionReady(
    episode: string,
    script: any,
    pages: string[],
    review: any,
  ): Promise<boolean> {
    if (
      !script?.panels?.length ||
      !pages.length ||
      (Array.isArray(script.output_layout) &&
        script.output_layout.length !== pages.length)
    )
      return false;
    if (review?.visual_qa === "PASS" && review?.content_review === "PASS")
      return true;
    const validated = await this.json(episode, "dashboard-validation.json");
    return (
      !!validated?.visualHashesVerified &&
      validated.fingerprint === (await this.fingerprint(episode))
    );
  }
  async create() {
    await mkdir(this.root, { recursive: true });
    const names = await readdir(this.root);
    let index =
      Math.max(0, ...names.map((n) => Number(n.match(/^EP-(\d+)/)?.[1]) || 0)) +
      1;
    for (;;) {
      const name = `EP-${String(index).padStart(3, "0")}-desk-${crypto.randomUUID().slice(0, 8)}`;
      try {
        await mkdir(join(this.root, name));
        return name;
      } catch (e: any) {
        if (e.code !== "EEXIST") throw e;
        index++;
      }
    }
  }
}
