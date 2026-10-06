import type { Options } from "./types";

export function countError(
  o: Pick<Options, "panelCount" | "imageCount">,
): string | null {
  const panels = o.panelCount;
  const images = o.imageCount;
  const minImages = images ?? 5;
  const maxImages = images ?? 9;
  if (panels != null && (panels < minImages || panels > maxImages * 4))
    return images == null
      ? "이미지 자동 선택(5~9장)은 전체 5~36컷으로 만들 수 있어요. 컷 수나 이미지 수를 바꿔주세요."
      : `이미지 ${images}장에는 전체 ${Math.max(3, images)}~${images * 4}컷을 담을 수 있어요.`;
  return null;
}

export function layoutInstructions(o: Options): string {
  if (o.panelCount === undefined && o.imageCount === undefined)
    return "Legacy run: preserve the existing agreed script/output_layout and completed images. If no layout exists yet, select 5–9 final images based on the story.";
  return [
    "The following dashboard count choices override skill defaults and generic five-page instructions.",
    o.imageCount == null
      ? "Choose between 5 and 9 final images (inclusive) based on the content. Do not always choose five. Use enough pages for a clear story without padding or repetition."
      : `Produce exactly ${o.imageCount} final images.`,
    o.panelCount == null
      ? "Choose the total panel count based on the content and selected image count, with at least 3 panels."
      : `Write exactly ${o.panelCount} total panels (not panels per image).`,
    "Each image contains 1–4 panels. Write script.json output_layout as the panel count for each final image; its length equals the image count and its sum equals panels.length. Record the selected layout in brief.json production notes as supported by its schema. Preserve this layout through all reviews, art and composition. Verify exact final page count before reporting completion.",
  ].join("\n");
}

export function validateOutputCounts(
  o: Options,
  script: any,
  files?: string[],
) {
  // Existing runs have already agreed their layout; do not retroactively change it.
  if (o.panelCount === undefined && o.imageCount === undefined) return;
  const layout = script?.output_layout;
  const panels = script?.panels;
  if (
    !Array.isArray(layout) ||
    !layout.length ||
    layout.some(
      (n: unknown) => !Number.isInteger(n) || Number(n) < 1 || Number(n) > 4,
    ) ||
    !Array.isArray(panels) ||
    panels.length < 3 ||
    layout.reduce((a: number, b: number) => a + b, 0) !== panels.length
  )
    throw new Error(
      "대본의 컷 수와 이미지별 컷 배치가 맞지 않아요. output_layout을 확인해주세요.",
    );
  if (
    o.imageCount != null
      ? layout.length !== o.imageCount
      : layout.length < 5 || layout.length > 9
  )
    throw new Error(
      `결과 이미지는 ${o.imageCount == null ? "내용에 맞춰 5~9장" : `${o.imageCount}장`}이어야 합니다. 현재 대본은 ${layout.length}장입니다.`,
    );
  if (o.panelCount != null && panels.length !== o.panelCount)
    throw new Error(
      `전체 ${o.panelCount}컷을 선택했지만 대본에는 ${panels.length}컷이 있습니다.`,
    );
  if (files && files.length !== layout.length)
    throw new Error(
      `완성 이미지는 ${layout.length}장이어야 합니다. 현재 ${files.length}장입니다.`,
    );
  if (
    files &&
    files.some((file, index) => Number(file.match(/\d+/)?.[0]) !== index + 1)
  )
    throw new Error(
      "완성 이미지 번호가 빠지거나 겹쳤어요. 1번부터 순서대로 저장해주세요.",
    );
}
