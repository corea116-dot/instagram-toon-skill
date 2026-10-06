import { chromium, expect, type Page } from "@playwright/test";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { createApp } from "../server/app";
import { defaults, defaultWorkflow } from "../shared/workflow";
import type { Run } from "../shared/types";

const data = await mkdtemp(join(tmpdir(), "toon-browser-"));
const port = 19432;
const service = await createApp({
  project: resolve(".."),
  appRoot: resolve("."),
  dataDir: data,
  port,
  startEngine: false,
});
// This fixture never runs production or publishes. All mutations are confined to its temporary database.
service.engine.tick = async () => {};
const server = service.app.listen(port, "127.0.0.1");
await new Promise<void>((r) => server.once("listening", r));
const browser = await chromium.launch({ channel: "chrome", headless: true });
const errors: string[] = [];
const checks: string[] = [];
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  locale: "ko-KR",
});
const page = await context.newPage();
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});
const base = `http://127.0.0.1:${port}`;
await mkdir("evidence", { recursive: true });
async function noOverflow(p: Page) {
  expect(
    await p.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
}
async function shot(name: string, p = page) {
  for (const img of await p.locator("img").all()) {
    await img.scrollIntoViewIfNeeded();
    await expect
      .poll(() =>
        img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0),
      )
      .toBe(true);
  }
  await p.evaluate(() => window.scrollTo(0, 0));
  await p.screenshot({
    path: resolve("evidence", name + ".png"),
    fullPage: !name.includes("viewer"),
  });
}
try {
  await page.goto(base);
  await page
    .getByLabel("비밀번호", { exact: true })
    .fill("browser-qa-only-2026");
  await page.getByLabel("비밀번호 한 번 더").fill("browser-qa-only-2026");
  await page.getByRole("button", { name: "작업실 열기", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "나의 작업실", exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".episode-card").first().locator("img"),
  ).toBeVisible();
  await noOverflow(page);
  await shot("desktop-home");
  checks.push("First setup and existing episode library render");
  await page.getByRole("button", { name: "연결과 알림", exact: true }).click();
  await page
    .getByRole("button", { name: "Codex 연결하기", exact: true })
    .click();
  await expect(page.getByText("도우미와 연결되어 있어요")).toBeVisible({
    timeout: 60000,
  });
  checks.push(
    "Live Codex transport and model catalog connect without a production turn",
  );
  await page.getByRole("button", { name: "작업 흐름", exact: true }).click();
  await page.getByLabel("단계 이름", { exact: true }).fill("자료 찾아보기");
  await page.getByLabel("생각하는 깊이").selectOption("high");
  await page.getByRole("button", { name: "변경 저장", exact: true }).click();
  await expect(page.getByText("작업 설정을 저장했어요.")).toBeVisible();
  expect(service.store.state().settings.workflow.nodes[0].effort).toBe("high");
  await page.getByRole("button", { name: "단계 추가", exact: true }).click();
  await page.getByRole("button", { name: "변경 저장", exact: true }).click();
  await expect
    .poll(() => service.store.state().settings.workflow.nodes.length)
    .toBe(8);
  await noOverflow(page);
  await shot("desktop-workflow");
  checks.push("Individual effort edit and additional workflow stage persist");
  await page.getByRole("button", { name: "예약", exact: true }).click();
  await page.getByRole("button", { name: "예약 추가", exact: true }).click();
  await page.getByLabel("예약 이름", { exact: true }).fill("화면 검증용 예약");
  await page.getByLabel("전체 컷 수", { exact: true }).selectOption("8");
  await page.getByLabel("결과 이미지 수", { exact: true }).selectOption("5");
  await page.getByRole("switch", { name: "이 예약 사용하기" }).uncheck();
  await page.getByRole("button", { name: "예약 저장", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "화면 검증용 예약" }),
  ).toBeVisible();
  expect(service.store.state().schedules[0].enabled).toBe(false);
  expect(service.store.state().schedules[0].options.panelCount).toBe(8);
  expect(service.store.state().schedules[0].options.imageCount).toBe(5);
  checks.push("Disabled recurring schedule creation persists safely");
  await page
    .getByRole("button", { name: "결과 모아보기", exact: true })
    .click();
  await page.locator(".episode-card").first().click();
  await expect(page.locator(".image-markup img")).toBeVisible();
  await page.getByRole("button", { name: "다음 이미지", exact: true }).click();
  await expect(page.getByText("2 / 5", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "대본", exact: true }).click();
  await expect(page.locator(".script-reader article").first()).toBeVisible();
  await page.getByRole("button", { name: "닫기", exact: true }).click();
  checks.push("Existing image pagination and script reader");
  const library = await (await context.request.get(base + "/api/state")).json();
  const episode = library.library.find((e: any) => e.pages.length === 5).id;
  const now = new Date().toISOString();
  const workflow = structuredClone(defaultWorkflow);
  const run: Run = {
    ...defaults,
    id: crypto.randomUUID(),
    title: "화면 검증용 · 기존 결과 읽기",
    episode,
    createdAt: now,
    updatedAt: now,
    status: "ready",
    workflow,
    stages: Object.fromEntries(
      workflow.nodes.map((n) => [
        n.id,
        { status: n.kind === "publish" ? "waiting" : "done", attempts: 0 },
      ]),
    ),
    annotations: [],
    approvals: {},
    publication: { phase: "none", children: [] },
  };
  service.store.update((s) => s.runs.push(run));
  await page.reload();
  await page
    .getByRole("button", { name: "대본·그림 보기", exact: true })
    .click();
  await page.locator(".image-markup").click({ position: { x: 140, y: 170 } });
  await page
    .getByLabel("수정 메모", { exact: true })
    .fill("화면 검증용 메모: 이 부분을 더 잘 보이게");
  await page.getByRole("button", { name: "메모 남기기", exact: true }).click();
  await expect
    .poll(() => service.store.state().runs[0].annotations.length)
    .toBe(1);
  await expect(
    page
      .locator(".notes-list")
      .getByText("화면 검증용 메모: 이 부분을 더 잘 보이게", { exact: true }),
  ).toBeVisible();
  expect(service.store.state().runs[0].annotations[0].point!.x).toBeGreaterThan(
    0,
  );
  await shot("desktop-annotation");
  await page.getByRole("button", { name: "닫기", exact: true }).click();
  checks.push("Image position annotation persists with revision fingerprint");
  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    locale: "ko-KR",
    storageState: await context.storageState(),
  });
  const phone = await mobile.newPage();
  phone.on("pageerror", (e) => errors.push(e.message));
  await phone.goto(base);
  await expect(
    phone.getByRole("heading", { name: "나의 작업실", exact: true }),
  ).toBeVisible();
  await noOverflow(phone);
  await shot("mobile-home", phone);
  await phone
    .getByRole("button", { name: "새 인스타툰 만들기", exact: true })
    .last()
    .click();
  await expect(phone.getByLabel("전체 컷 수", { exact: true })).toHaveValue(
    "auto",
  );
  await expect(phone.getByLabel("결과 이미지 수", { exact: true })).toHaveValue(
    "auto",
  );
  await phone.getByLabel("전체 컷 수", { exact: true }).selectOption("8");
  await phone.getByLabel("결과 이미지 수", { exact: true }).selectOption("5");
  await noOverflow(phone);
  await shot("mobile-count-selection", phone);
  await phone.getByLabel("결과 이미지 수", { exact: true }).selectOption("9");
  await expect(phone.getByRole("alert")).toContainText("전체 9~36컷");
  await phone.getByRole("button", { name: "취소", exact: true }).click();
  checks.push(
    "Mobile count choices default to automatic 5–9, manual counts and invalid pairs are visible; scheduled counts persist",
  );
  await phone.getByRole("button", { name: "메뉴 열기", exact: true }).click();
  await phone.getByRole("button", { name: "작업 흐름", exact: true }).click();
  await expect(
    phone.getByRole("heading", { name: "작업 흐름", exact: true }),
  ).toBeVisible();
  await noOverflow(phone);
  await shot("mobile-workflow", phone);
  await phone.getByRole("button", { name: "메뉴 열기", exact: true }).click();
  await phone
    .getByRole("button", { name: "결과 모아보기", exact: true })
    .click();
  await phone.locator(".episode-card").first().click();
  await expect(phone.locator(".image-markup img")).toBeVisible();
  await noOverflow(phone);
  await shot("mobile-viewer", phone);
  checks.push(
    "390px mobile home, workflow, menu and result viewer without horizontal overflow",
  );
  await mobile.close();
  expect(errors).toEqual([]);
  checks.push("No browser runtime or console errors");
  await writeFile(
    "evidence/browser-checks.json",
    JSON.stringify(
      {
        checkedAt: new Date().toISOString(),
        browser:
          "Installed Chrome, desktop 1440x1000 and mobile viewport 390x844",
        checks,
        errors,
        productionRun: false,
        instagramPost: false,
        realIPhonePush: false,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(JSON.stringify({ passed: checks.length, checks }, null, 2));
} finally {
  await browser.close();
  await service.close();
  await new Promise<void>((r) => server.close(() => r()));
  await rm(data, { recursive: true, force: true });
}
