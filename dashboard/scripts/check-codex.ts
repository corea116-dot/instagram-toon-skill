import { resolve } from "node:path";
import { Codex } from "../server/codex";
const codex = new Codex(resolve(".."));
try {
  await codex.connect();
  const skills = await codex.call("skills/list", {
    cwds: [resolve("..")],
    forceReload: true,
  });
  const found = skills.data?.some((group: any) =>
    group.skills?.some(
      (s: any) => s.name === "instagram-toon" && s.enabled !== false,
    ),
  );
  console.log(
    JSON.stringify(
      {
        connected: codex.ready,
        models: codex.models.map((m) => ({
          model: m.model,
          efforts: m.supportedReasoningEfforts.map((e) => e.reasoningEffort),
        })),
        instagramToonSkillVisible: !!found,
        productionTurnStarted: false,
      },
      null,
      2,
    ),
  );
} finally {
  codex.close();
}
