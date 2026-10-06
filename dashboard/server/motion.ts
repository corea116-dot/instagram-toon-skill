import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import { readFile, stat, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { promisify } from "node:util";
import type { Run, Stage } from "../shared/types";
import { Artifacts } from "./artifacts";
const exec = promisify(execFile);
export const sha256 = (data: Buffer) =>
  createHash("sha256").update(data).digest("hex");
export function motionFile(run: Run, file: string) {
  if (
    run.mode !== "motion" ||
    !/^motion\/desk-[a-f0-9-]+$/.test(run.motionDirectory ?? "")
  )
    throw new Error("영상 작업 경로를 확인해주세요.");
  return `${run.motionDirectory}/${file}`;
}
export function motionTask(
  run: Run,
  stage: Stage,
  root: string,
  skill: string,
): string {
  const folder = join(root, run.episode, motionFile(run, ""));
  const contract = `Read ${skill}/references/motion-workflow.md and ${skill}/references/motion-direction-baseline.md (the user-approved 2026-10-04 15:50 KST direction discussion), plus ${skill}/references/model-routing.md. This dashboard dispatches the configured independent workers; do not spawn duplicates or run later stages. Source comic: ${join(root, run.episode)}. Write only under ${folder}; never change original comic files or episode history. You are not alone: preserve other workers' edits. No external publishing/upload. Use the original comic as image reference, not other episodes. User authorized local end-to-end motion creation with the established 30s vertical game-music/native Korean young male Qwen voice preset. Do not restart an interview. Reuse completed assets unless affected by a defect.\n`;
  const tasks: Record<string, string> = {
    motion_plan: `Plan only: create brief.json and timeline.json with duration, fps and scenes (numeric start/end, dialogue, on-screen text, character action, camera, sound and source claims), plus asset direction. Hook/action first, varied interactions, avoid slow information recital.`,
    motion_content: `Independently review the timed script blind first, then source facts/continuity; apply informational or humor checks as appropriate. Write qa/content-review.json with overall PASS/FAIL, reviewer_id, actual timeline_sha256 and actionable findings. Do not edit the plan. Return completed:false on defects.`,
    motion_produce: `Produce only from the reviewed timeline. First check qa/content-review.json PASS and matching timeline_sha256. Generate new transparent action/interaction assets using the original episode references; local Qwen voice, music/SFX, animation and captions. Save reproducible sources and receipts, output/video.mp4 (H.264 yuv420p + AAC, faststart, 1080x1920, 30fps), and qa/production.json with timeline_sha256, listening/playback checks and honest limitations. Do not change timeline.json; if it needs changes return completed:false with the reason. Prepare ordered actual rendered frames for independent review.`,
    motion_visual: `Independently inspect actual video frames, source identity and approved timeline; inspect playback if available. Write qa/visual-review.json with overall PASS/FAIL, reviewer_id, actual video_sha256 of output/video.mp4, findings and inspection scope/limitations. Do not change the video or source. Return completed:false on defects.`,
  };
  return `${contract}${tasks[stage.id] ?? ""}\nPrevious failure/correction: ${run.revisionRequest ?? ""} ${run.stages[stage.id].message ?? ""}\nSave actual evidence before returning the required completion JSON.`;
}
export async function checkMotion(
  run: Run,
  stage: Stage,
  artifacts: Artifacts,
) {
  if ((await artifacts.fingerprint(run.episode)) !== run.sourceFingerprint)
    throw new Error(
      "원본 에피소드가 변경됐습니다. 변경된 원본으로 새 모션그래픽 작업을 시작해주세요.",
    );
  const path = (f: string) => artifacts.path(run.episode, motionFile(run, f));
  const json = async (f: string) =>
    JSON.parse(await readFile(await path(f), "utf8"));
  const timeline = await json("timeline.json");
  if (
    !Number.isFinite(timeline.duration) ||
    timeline.duration <= 0 ||
    timeline.fps !== 30 ||
    !Array.isArray(timeline.scenes) ||
    !timeline.scenes.length
  )
    throw new Error("장면 시간표와 영상 길이를 확인해주세요.");
  let end = 0;
  for (const scene of timeline.scenes) {
    if (
      !Number.isFinite(scene.start) ||
      !Number.isFinite(scene.end) ||
      scene.start < end ||
      scene.end <= scene.start ||
      scene.end > timeline.duration
    )
      throw new Error("장면 시간표의 순서·구간이 올바르지 않습니다.");
    end = scene.end;
  }
  const timelineHash = sha256(await readFile(await path("timeline.json")));
  if (stage.id === "motion_plan") {
    await json("brief.json");
    return;
  }
  const content = await json("qa/content-review.json");
  if (
    content.overall !== "PASS" ||
    !content.reviewer_id ||
    content.timeline_sha256 !== timelineHash
  )
    throw new Error("현재 각색 대본의 독립 검수가 필요합니다.");
  if (stage.id === "motion_content") return;
  const production = await json("qa/production.json");
  if (production.timeline_sha256 !== timelineHash)
    throw new Error("제작한 영상과 검수한 대본의 버전이 다릅니다.");
  const video = await path("output/video.mp4");
  if (!(await stat(video)).isFile() || !(await stat(video)).size)
    throw new Error("완성된 영상 파일이 없습니다.");
  if (stage.id === "motion_produce") return;
  const videoHash = sha256(await readFile(video));
  const visual = await json("qa/visual-review.json");
  if (
    visual.overall !== "PASS" ||
    !visual.reviewer_id ||
    visual.video_sha256 !== videoHash
  )
    throw new Error("현재 영상의 독립 화면 검수가 필요합니다.");
  if (stage.id === "motion_visual") return;
  const { stdout } = await exec(
    "ffprobe",
    ["-v", "error", "-show_streams", "-show_format", "-of", "json", video],
    { timeout: 30_000 },
  );
  const probe = JSON.parse(stdout);
  const picture = probe.streams.find((s: any) => s.codec_type === "video");
  const voice = probe.streams.find((s: any) => s.codec_type === "audio");
  if (
    picture?.codec_name !== "h264" ||
    picture.pix_fmt !== "yuv420p" ||
    picture.width !== 1080 ||
    picture.height !== 1920 ||
    picture.r_frame_rate !== "30/1" ||
    voice?.codec_name !== "aac" ||
    Math.abs(Number(probe.format.duration) - timeline.duration) > 0.25
  )
    throw new Error("영상 규격·음성·길이를 확인해주세요.");
  await exec(
    "ffmpeg",
    ["-v", "error", "-xerror", "-i", video, "-f", "null", "-"],
    { timeout: 120_000, maxBuffer: 1024 * 1024 },
  );
  await writeFile(
    (await path("qa")) + "/final-report.json",
    JSON.stringify(
      {
        result: "technical_checks_passed",
        video_sha256: videoHash,
        timeline_sha256: timelineHash,
        full_decode: "no_errors",
        duration: probe.format.duration,
        production,
        visual,
        checkedAt: new Date().toISOString(),
      },
      null,
      2,
    ),
  );
}
