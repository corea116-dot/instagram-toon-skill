import webpush from "web-push";
import type { PushSubscription } from "web-push";
import { Store } from "./store";

export class Push {
  private closed = false;
  stop() {
    this.closed = true;
  }
  constructor(readonly store: Store) {
    if (!store.secret("push-keys"))
      store.setSecret("push-keys", webpush.generateVAPIDKeys());
  }
  publicKey() {
    return this.store.secret<{ publicKey: string }>("push-keys")!.publicKey;
  }
  subscribe(subscription: PushSubscription) {
    const url = new URL(subscription.endpoint);
    // Only browser push providers: subscription endpoints must not become an arbitrary SSRF proxy.
    if (
      url.protocol !== "https:" ||
      url.port ||
      url.username ||
      url.password ||
      ![
        "web.push.apple.com",
        "fcm.googleapis.com",
        "updates.push.services.mozilla.com",
      ].some(
        (host) => url.hostname === host || url.hostname.endsWith("." + host),
      )
    )
      throw new Error("지원되는 휴대폰 알림 주소가 아닙니다.");
    const all = this.store.secret<PushSubscription[]>("subscriptions") ?? [];
    this.store.setSecret(
      "subscriptions",
      [
        ...all.filter((s) => s.endpoint !== subscription.endpoint),
        subscription,
      ].slice(-10),
    );
  }
  async send(title: string, body: string, runId?: string) {
    if (this.closed) return { sent: 0, failed: 0 };
    const keys = this.store.secret<{ publicKey: string; privateKey: string }>(
      "push-keys",
    )!;
    const publicUrl = this.store.state().settings.publicUrl;
    if (!publicUrl) return { sent: 0, failed: 0 };
    const subscriptions =
      this.store.secret<PushSubscription[]>("subscriptions") ?? [];
    const stale = new Set<string>();
    let sent = 0,
      failed = 0;
    await Promise.all(
      subscriptions.map(async (subscription) => {
        try {
          await webpush.sendNotification(
            subscription,
            JSON.stringify({
              title,
              body,
              url: runId ? `/?run=${encodeURIComponent(runId)}` : "/",
              tag: runId ?? "toon-desk",
            }),
            {
              TTL: 3600,
              vapidDetails: {
                subject: publicUrl,
                publicKey: keys.publicKey,
                privateKey: keys.privateKey,
              },
              timeout: 10_000,
            },
          );
          sent++;
        } catch (e: any) {
          failed++;
          if ([404, 410].includes(e.statusCode))
            stale.add(subscription.endpoint);
        }
      }),
    );
    if (stale.size && !this.closed)
      this.store.setSecret(
        "subscriptions",
        subscriptions.filter((s) => !stale.has(s.endpoint)),
      );
    return { sent, failed };
  }
}
