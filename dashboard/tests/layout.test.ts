import { test } from "node:test";
import assert from "node:assert/strict";
import { defaults, optionsSchema } from "../shared/workflow";
import {
  countError,
  layoutInstructions,
  validateOutputCounts,
} from "../shared/layout";

const script = (layout: number[]) => ({
  output_layout: layout,
  panels: Array.from({ length: layout.reduce((a, b) => a + b, 0) }, (_, i) => ({
    panel: i + 1,
  })),
});

test("new and old saved schedule inputs default to content-based 5–9 images", () => {
  const { panelCount, imageCount, ...oldInput } = defaults;
  const parsed = optionsSchema.parse(oldInput);
  assert.equal(parsed.imageCount, null);
  assert.equal(parsed.panelCount, null);
  assert.match(layoutInstructions(parsed), /5 and 9/);
  assert.match(layoutInstructions(parsed), /Do not always choose five/);
});

test("manual counts are independent of topic selection and reject impossible layouts", () => {
  for (const topicMode of ["manual", "auto"] as const) {
    const parsed = optionsSchema.parse({
      ...defaults,
      topicMode,
      topic: "사용자 주제",
      panelCount: 8,
      imageCount: 5,
    });
    assert.equal(parsed.panelCount, 8);
    assert.equal(parsed.imageCount, 5);
    assert.match(layoutInstructions(parsed), /exactly 8 total panels/);
    assert.match(layoutInstructions(parsed), /exactly 5 final images/);
  }
  for (const [panelCount, imageCount] of [
    [3, 5],
    [21, 5],
    [37, null],
    [4, null],
    [3.5, 1],
    [8, 11],
    [2, 1],
  ])
    assert.equal(
      optionsSchema.safeParse({ ...defaults, panelCount, imageCount }).success,
      false,
    );
  assert.equal(countError({ panelCount: 8, imageCount: 5 }), null);
  assert.equal(
    optionsSchema.safeParse({ ...defaults, panelCount: 3, imageCount: 1 })
      .success,
    true,
  );
});

test("generated script and final image counts enforce chosen and automatic limits", () => {
  for (let n = 5; n <= 9; n++)
    validateOutputCounts(defaults, script(Array(n).fill(1)));
  for (const n of [4, 10])
    assert.throws(
      () => validateOutputCounts(defaults, script(Array(n).fill(1))),
      /5~9/,
    );
  const chosen = { ...defaults, panelCount: 8, imageCount: 5 };
  const s = script([1, 2, 1, 3, 1]);
  const pages = Array.from({ length: 5 }, (_, i) => `page-0${i + 1}.png`);
  validateOutputCounts(chosen, s, pages);
  assert.throws(
    () => validateOutputCounts(chosen, script([1, 1, 1, 1, 1])),
    /8컷/,
  );
  assert.throws(
    () => validateOutputCounts(chosen, s, pages.slice(1)),
    /현재 4장/,
  );
  assert.throws(
    () =>
      validateOutputCounts(chosen, s, [...pages.slice(0, 4), "page-06.png"]),
    /번호/,
  );
  assert.throws(
    () => validateOutputCounts(chosen, { ...s, output_layout: [8] }),
    /배치/,
  );
  const { panelCount, imageCount, ...legacy } = defaults;
  assert.doesNotThrow(() =>
    validateOutputCounts(legacy, { panels: [{ panel: 1 }] }, []),
  );
});
