import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { mkdir, stat } from "node:fs/promises";
import { join } from "node:path";
import sharp from "sharp";
import { Store, event } from "./store";
import { Artifacts } from "./artifacts";
import type { Account, Run } from "../shared/types";

type Credentials = { appId: string; appSecret: string };
type ConnectedAccount = Account & { token: string };
export class PublishUncertain extends Error {}
export class Instagram {
  private busy = new Set<string>();
  constructor(
    readonly store: Store,
    readonly artifacts: Artifacts,
    readonly request: typeof fetch = fetch,
  ) {
    if (!store.secret("media-key"))
      store.setSecret("media-key", randomBytes(32).toString("hex"));
  }
  account(): Account | null {
    const account = this.store.secret<ConnectedAccount>("instagram");
    if (!account) return null;
    const { token, ...publicFields } = account;
    return publicFields;
  }
  ready() {
    return (
      !!this.store.secret<Credentials>("instagram-app") &&
      !!this.store.state().settings.publicUrl
    );
  }
  async requestJson(url: string, options?: RequestInit) {
    let response: Response;
    try {
      response = await this.request(url, {
        ...options,
        signal: AbortSignal.timeout(30_000),
      });
    } catch {
      throw new Error(
        "인스타그램 응답을 받지 못했습니다. 연결 상태를 확인해주세요.",
      );
    }
    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new Error("인스타그램 응답을 읽지 못했습니다.");
    }
    if (!response.ok || data.error) {
      if (data.error?.code === 190 || response.status === 401)
        throw new Error(
          "인스타그램 연결이 만료됐습니다. 계정을 다시 연결해주세요.",
        );
      throw new Error(
        `인스타그램 요청이 거절됐습니다. 계정의 게시 권한과 연결 설정을 확인해주세요. (상태 ${response.status}${data.error?.code ? ", 코드 " + Number(data.error.code) : ""})`,
      );
    }
    return data;
  }
  beginConnect(session: string) {
    const app = this.store.secret<Credentials>("instagram-app");
    const base = this.store.state().settings.publicUrl;
    if (!app || !base)
      throw new Error(
        "먼저 외부 접속 주소와 인스타그램 연결 정보를 설정해주세요.",
      );
    const state = randomBytes(32).toString("hex");
    this.store.setSecret("instagram-oauth", {
      state,
      session,
      until: Date.now() + 600_000,
    });
    const query = new URLSearchParams({
      client_id: app.appId,
      redirect_uri: `${base}/api/instagram/callback`,
      response_type: "code",
      scope: "instagram_business_basic,instagram_business_content_publish",
      state,
      force_reauth: "true",
    });
    return `https://www.instagram.com/oauth/authorize?${query}`;
  }
  async callback(code: string, state: string, session: string) {
    const saved = this.store.secret<{
      state: string;
      session: string;
      until: number;
    }>("instagram-oauth");
    if (
      !saved ||
      saved.state !== state ||
      saved.session !== session ||
      saved.until < Date.now()
    )
      throw new Error(
        "계정 연결 요청이 만료됐습니다. 연결 버튼을 다시 눌러주세요.",
      );
    this.store.remove("secret:instagram-oauth");
    const app = this.store.secret<Credentials>("instagram-app")!;
    const base = this.store.state().settings.publicUrl;
    const short = await this.requestJson(
      "https://api.instagram.com/oauth/access_token",
      {
        method: "POST",
        body: new URLSearchParams({
          client_id: app.appId,
          client_secret: app.appSecret,
          grant_type: "authorization_code",
          redirect_uri: `${base}/api/instagram/callback`,
          code,
        }),
      },
    );
    const token = await this.requestJson(
      `https://graph.instagram.com/access_token?${new URLSearchParams({ grant_type: "ig_exchange_token", client_secret: app.appSecret, access_token: short.access_token })}`,
    );
    const profile = await this.requestJson(
      `https://graph.instagram.com/${this.store.state().settings.graphVersion}/me?fields=user_id,username`,
      { headers: { Authorization: `Bearer ${token.access_token}` } },
    );
    if (!profile.user_id || !profile.username || !token.expires_in)
      throw new Error("연결된 계정을 확인하지 못했습니다.");
    const account: ConnectedAccount = {
      id: String(profile.user_id),
      username: profile.username,
      token: token.access_token,
      connectedAt: new Date().toISOString(),
      expiresAt: new Date(
        Date.now() + Number(token.expires_in) * 1000,
      ).toISOString(),
    };
    this.store.setSecret("instagram", account);
    this.store.update((s) =>
      event(s, `@${account.username} 계정을 연결했습니다.`),
    );
    return this.account();
  }
  private async graph(
    path: string,
    method = "GET",
    values: Record<string, string> = {},
  ) {
    const account = this.store.secret<ConnectedAccount>("instagram");
    if (!account || new Date(account.expiresAt).getTime() < Date.now())
      throw new Error("인스타그램 계정을 연결해주세요.");
    const url = new URL(
      `https://graph.instagram.com/${this.store.state().settings.graphVersion}/${path}`,
    );
    if (method === "GET") url.search = new URLSearchParams(values).toString();
    return this.requestJson(url.href, {
      method,
      headers: { Authorization: `Bearer ${account.token}` },
      ...(method === "POST" ? { body: new URLSearchParams(values) } : {}),
    });
  }
  mediaSignature(run: string, file: string, expires: string) {
    return createHmac("sha256", this.store.secret<string>("media-key")!)
      .update(`${run}/${file}/${expires}`)
      .digest("hex");
  }
  verifyMedia(run: string, file: string, expires: string, signature: string) {
    if (
      !/^[a-f0-9-]{36}$/.test(run) ||
      !/^page-\d+\.jpg$/.test(file) ||
      !/^\d{13}$/.test(expires) ||
      Number(expires) < Date.now() ||
      Number(expires) > Date.now() + 86400_000 ||
      !/^[a-f0-9]{64}$/.test(signature)
    )
      return false;
    return timingSafeEqual(
      Buffer.from(this.mediaSignature(run, file, expires)),
      Buffer.from(signature),
    );
  }
  mediaPath(run: string, file: string) {
    return join(this.store.directory, "outbox", run, file);
  }
  private update(id: string, fn: (r: Run) => void) {
    this.store.update((s) => {
      const run = s.runs.find((r) => r.id === id);
      if (!run) throw new Error("작업을 찾지 못했습니다.");
      fn(run);
      run.updatedAt = new Date().toISOString();
    });
  }
  async publish(id: string) {
    if (this.busy.has(id)) return;
    this.busy.add(id);
    try {
      const run = this.store.state().runs.find((r) => r.id === id);
      if (!run) throw new Error("작업을 찾지 못했습니다.");
      if (
        ["sending", "unknown", "verifying", "verified"].includes(
          run.publication.phase,
        )
      ) {
        await this.verify(id);
        return;
      }
      const account = this.account();
      if (!account)
        throw new Error("인스타그램 계정을 연결하면 게시할 수 있어요.");
      const publicUrl = this.store.state().settings.publicUrl;
      if (!publicUrl)
        throw new Error("외부에서 접근할 수 있는 HTTPS 주소를 연결해주세요.");
      const fingerprint = await this.artifacts.fingerprint(run.episode);
      if (
        run.publication.fingerprint &&
        run.publication.fingerprint !== fingerprint
      )
        throw new Error(
          "게시 준비 후 결과물이 바뀌었습니다. 수정 작업을 거쳐 게시 준비를 다시 해주세요.",
        );
      if (!run.approvals.quality || run.approvals.quality !== fingerprint)
        throw new Error(
          "검사 이후 결과물이 바뀌었습니다. 마지막 검사부터 다시 진행해주세요.",
        );
      if (
        run.humanReview &&
        (!run.approvals.images ||
          run.approvals.images !==
            (await this.artifacts.fingerprint(run.episode, "images")))
      )
        throw new Error("현재 완성된 그림을 먼저 확인해주세요.");
      if (
        run.humanReview &&
        run.approvals.script !==
          (await this.artifacts.fingerprint(run.episode, "script"))
      )
        throw new Error("현재 대본을 먼저 확인해주세요.");
      if (run.publication.accountId && run.publication.accountId !== account.id)
        throw new Error(
          "게시 준비 중 계정이 바뀌었습니다. 기존 작업의 게시 대상을 먼저 확인해주세요.",
        );
      const pages = await this.artifacts.pages(run.episode);
      if (!pages.length || pages.length > 10)
        throw new Error(
          "인스타그램 묶음 게시에는 1~10장의 이미지가 필요합니다.",
        );
      const caption = await this.artifacts.text(run.episode, "caption.txt");
      if ([...caption].length > 2200)
        throw new Error("게시글이 너무 깁니다. 2,200자 이내로 줄여주세요.");
      this.update(id, (r) => {
        r.status = "publishing";
        r.publication.accountId = account.id;
        r.publication.fingerprint = fingerprint;
        r.error = undefined;
      });
      await mkdir(join(this.store.directory, "outbox", id), {
        recursive: true,
        mode: 0o700,
      });
      const expires = String(Date.now() + 23 * 3600_000);
      const urls: string[] = [];
      for (let i = 0; i < pages.length; i++) {
        const file = `page-${i + 1}.jpg`;
        await sharp(await this.artifacts.path(run.episode, `final/${pages[i]}`))
          .flatten({ background: "#ffffff" })
          .jpeg({ quality: 95 })
          .toFile(this.mediaPath(id, file));
        if ((await stat(this.mediaPath(id, file))).size > 8 * 1024 * 1024)
          throw new Error("게시할 이미지 크기가 너무 큽니다.");
        urls.push(
          `${publicUrl}/media/${id}/${file}?expires=${expires}&sig=${this.mediaSignature(id, file, expires)}`,
        );
      }
      let current = this.store.state().runs.find((r) => r.id === id)!;
      if (!current.publication.containerId) {
        if (pages.length === 1) {
          const created = await this.graph(`${account.id}/media`, "POST", {
            image_url: urls[0],
            caption,
          });
          if (!created.id) throw new Error("게시 준비 번호를 받지 못했습니다.");
          this.update(id, (r) => {
            r.publication.containerId = String(created.id);
            r.publication.phase = "prepared";
          });
        } else {
          for (
            let i = current.publication.children.length;
            i < urls.length;
            i++
          ) {
            const child = await this.graph(`${account.id}/media`, "POST", {
              image_url: urls[i],
              is_carousel_item: "true",
            });
            if (!child.id)
              throw new Error("이미지 준비 번호를 받지 못했습니다.");
            this.update(id, (r) =>
              r.publication.children.push(String(child.id)),
            );
          }
          current = this.store.state().runs.find((r) => r.id === id)!;
          for (const child of current.publication.children)
            await this.waitContainer(child);
          const parent = await this.graph(`${account.id}/media`, "POST", {
            media_type: "CAROUSEL",
            children: current.publication.children.join(","),
            caption,
          });
          if (!parent.id)
            throw new Error("묶음 게시 준비 번호를 받지 못했습니다.");
          this.update(id, (r) => {
            r.publication.containerId = String(parent.id);
            r.publication.phase = "prepared";
          });
        }
      }
      const container = this.store.state().runs.find((r) => r.id === id)!
        .publication.containerId!;
      await this.waitContainer(container);
      // Check content again immediately before the irreversible request.
      if ((await this.artifacts.fingerprint(run.episode)) !== fingerprint)
        throw new Error("게시 준비 중 결과물이 바뀌어 멈췄습니다.");
      this.update(id, (r) => {
        r.publication.phase = "sending";
        r.publication.attemptedAt = new Date().toISOString();
      });
      let published: any;
      try {
        published = await this.graph(`${account.id}/media_publish`, "POST", {
          creation_id: container,
        });
      } catch {
        this.update(id, (r) => {
          r.status = "publish_unknown";
          r.publication.phase = "unknown";
          r.error =
            "게시 요청의 결과를 확인하지 못했습니다. 중복 게시를 막기 위해 다시 올리지 않았어요.";
        });
        throw new PublishUncertain(
          "인스타그램에서 실제 게시 여부를 확인해주세요.",
        );
      }
      if (!published.id) {
        this.update(id, (r) => {
          r.status = "publish_unknown";
          r.publication.phase = "unknown";
        });
        throw new PublishUncertain(
          "게시 번호를 받지 못했습니다. 실제 게시 여부를 확인해주세요.",
        );
      }
      this.update(id, (r) => {
        r.publication.mediaId = String(published.id);
        r.publication.phase = "verifying";
      });
      await this.verify(id);
    } finally {
      this.busy.delete(id);
    }
  }
  private async waitContainer(id: string) {
    for (let i = 0; i < 12; i++) {
      const status = await this.graph(id, "GET", { fields: "status_code" });
      if (status.status_code === "FINISHED") return;
      if (["ERROR", "EXPIRED"].includes(status.status_code))
        throw new Error("인스타그램이 이미지 준비를 완료하지 못했습니다.");
      await new Promise((r) => setTimeout(r, 2500));
    }
    throw new Error(
      "인스타그램에서 이미지 준비가 늦어지고 있습니다. 잠시 후 다시 시도해주세요.",
    );
  }
  async verify(id: string) {
    const run = this.store.state().runs.find((r) => r.id === id);
    if (
      !run ||
      !["sending", "unknown", "verifying", "verified"].includes(
        run.publication.phase,
      )
    )
      throw new Error("아직 게시 요청을 보내지 않은 작업입니다.");
    if (
      !run.publication.accountId ||
      run.publication.accountId !== this.account()?.id
    )
      throw new Error("게시 요청을 보낸 계정을 다시 연결해주세요.");
    if (!run.publication.mediaId) {
      if (run.publication.containerId) {
        const container = await this.graph(run.publication.containerId, "GET", {
          fields: "status_code",
        });
        this.update(id, (r) => {
          r.status = "publish_unknown";
          r.publication.phase = "unknown";
          r.error =
            container.status_code === "PUBLISHED"
              ? "인스타그램은 게시 완료로 응답했지만 게시물 링크를 아직 확인하지 못했습니다. 인스타그램에서 링크를 확인해주세요."
              : "게시 여부가 아직 확실하지 않아 다시 올리지 않았어요. 인스타그램에서 확인해주세요.";
        });
      }
      return;
    }
    const media = await this.graph(run.publication.mediaId, "GET", {
      fields: "id,permalink,username",
    });
    const account = this.account();
    if (
      String(media.id) !== run.publication.mediaId ||
      !/^https:\/\/(www\.)?instagram\.com\/(p|reel)\//.test(
        media.permalink ?? "",
      ) ||
      (media.username && media.username !== account?.username)
    )
      throw new Error("게시물 주소 또는 계정을 확인하지 못했습니다.");
    this.update(id, (r) => {
      r.status = "completed";
      r.error = undefined;
      r.publication.phase = "verified";
      r.publication.permalink = media.permalink;
      r.publication.verifiedAt = new Date().toISOString();
      const stage = r.workflow.nodes.find((n) => n.kind === "publish")!;
      r.stages[stage.id] = {
        ...r.stages[stage.id],
        status: "done",
        finishedAt: new Date().toISOString(),
      };
    });
    this.store.update((s) =>
      event(s, "실제 인스타그램 게시물 주소를 확인했습니다.", id, "success"),
    );
  }
  async reconcile(id: string, mediaId: string) {
    if (!/^\d{5,40}$/.test(mediaId))
      throw new Error("인스타그램 게시물 번호를 확인해주세요.");
    const run = this.store.state().runs.find((r) => r.id === id);
    if (!run || run.status !== "publish_unknown")
      throw new Error("게시 여부 확인이 필요한 작업이 아닙니다.");
    const media = await this.graph(mediaId, "GET", {
      fields: "id,permalink,username,caption,timestamp",
    });
    const account = this.account();
    const caption = await this.artifacts.text(run.episode, "caption.txt");
    if (
      !account ||
      media.username !== account.username ||
      media.caption !== caption ||
      !media.timestamp ||
      new Date(media.timestamp).getTime() <
        new Date(run.publication.attemptedAt ?? run.createdAt).getTime() - 60000
    )
      throw new Error(
        "이 작업의 계정·게시글·게시 시각과 일치하는 게시물이 아닙니다.",
      );
    this.update(id, (r) => {
      r.publication.mediaId = mediaId;
      r.publication.phase = "verifying";
    });
    await this.verify(id);
  }
}
