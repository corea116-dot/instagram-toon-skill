#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=12.0", "pydantic>=2.12", "typer>=0.20"]
# ///
"""Bounded local handoffs; never supplies creative or semantic PASS judgments."""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps
from episode_models import BriefModel, EpisodeScriptModel
from content_review import BlindReadV11Model, file_sha256, semantic_content_sha256, layout_sha256, require_content_review
from information_lock import require_content_lock
from layout_preflight import require_layout_preflight, run_layout_preflight
from rendering import write_text_atomic


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def review_view(script):
    """Lossless visible words and scene context; no intended answer or panel-job leak."""
    lines = [f"페이지 구성: {list(script.output_layout or [])}"]
    for panel in script.panels:
        lines += [f"\n컷 {panel.panel}"]
        for key in ("scene", "expression", "action", "props", "background", "camera"):
            lines += [f"{key}: {getattr(panel, key)}"]
        lines += [f"{item.speaker}: {item.text}" for item in panel.dialogue]
        if panel.information_card:
            lines += ["카드: " + item.text for item in panel.information_card.texts]
            lines += ["설명 행동: " + panel.information_card.presenter.pose]
    return "\n".join(lines) + "\n"


def packet(episode):
    script = EpisodeScriptModel.model_validate(load(episode / "script.json"))
    brief = BriefModel.model_validate(load(episode / "brief.json"))
    text = review_view(script)
    write_text_atomic(episode / "review-visible.txt", text)
    # This manifest is binding metadata, not evidence supplied during blind reading.
    save(episode / "review-input-hashes.json", {
        "content_sha256": semantic_content_sha256(episode / "brief.json", episode / "script.json"),
        "layout_sha256": layout_sha256(episode / "script.json"),
        "visible_sha256": hashlib.sha256(text.encode()).hexdigest(),
    })
    write_text_atomic(episode / "script-preview.md", f"# {script.title}\n\n" + text)
    _, record = run_layout_preflight(episode, draft=True)
    if record.outcome != "pass":
        raise ValueError("draft layout: " + "; ".join(record.issues))
    return episode / "review-visible.txt"


def sources(episode):
    """Release the evidence only after the reviewer persisted a valid blind read."""
    BlindReadV11Model.model_validate(load(episode / "blind-read.json"))
    binding = load(episode / "review-input-hashes.json")
    if binding["content_sha256"] != semantic_content_sha256(episode / "brief.json", episode / "script.json"):
        raise ValueError("review packet is stale; rebuild and read the changed script")
    if binding["layout_sha256"] != layout_sha256(episode / "script.json"):
        raise ValueError("review packet geometry is stale")
    if binding["visible_sha256"] != file_sha256(episode / "review-visible.txt"):
        raise ValueError("visible packet changed")
    brief = BriefModel.model_validate(load(episode / "brief.json"))
    script = EpisodeScriptModel.model_validate(load(episode / "script.json"))
    result = {"episode_id":brief.episode_id, "question_answer":brief.question_answer.model_dump(mode="json"),
              "panels":[{"panel":p.panel,"panel_job":p.panel_job,"new_information":p.new_information,
                         "reader_takeaway":p.reader_takeaway,"scope":p.scope,"text_budget":p.text_budget}
                        for p in script.panels], **binding}
    return result


def prepare_prompts(episode):
    from compose_episode import (_prompt_manifest, _primary_reference_images,
        CHARACTER_BIBLE_PATH, SKILL_ROOT)
    from reference_policy import load_character_policy
    require_content_review(episode); require_content_lock(episode); require_layout_preflight(episode)
    script = EpisodeScriptModel.model_validate(load(episode / "script.json"))
    style = load(SKILL_ROOT / "memory" / "visual-style.json")
    policy = load_character_policy(episode, CHARACTER_BIBLE_PATH, SKILL_ROOT)
    references = tuple(dict.fromkeys(policy.reference_images + _primary_reference_images()))
    save(episode / "reference-snapshot.json", {"reference_images":references,
        "absolute_paths":[str(SKILL_ROOT / x) for x in references]})
    for panel in script.panels:
        path = episode / "prompts" / f"panel-{panel.panel}.json"
        if path.exists():
            raise ValueError(f"provider manifest exists; preserve it: {path}")
    for panel in script.panels:
        prompt = _prompt_manifest(script,panel,"native",0,references,policy)
        payload = prompt.model_dump(mode="json")
        payload["prompt"] += " Style: " + style["description"] + " Paper: " + style["paper_texture"] + " Palette: " + ", ".join(style["palette"]["allowed_colors"].values())
        payload["prompt"] += " Leave these speech overlay areas empty of important art: " + json.dumps(payload["bubble_safe_areas"]) + ". Raw art must contain no text, speech bubbles or card graphics."
        if script.rendering_policy == "frame_native_v1":
            width, height = prompt.size
            rectangles = [
                {"x": round(100 * area.x / width, 2),
                 "y": round(100 * area.y / height, 2),
                 "width": round(100 * area.width / width, 2),
                 "height": round(100 * area.height / height, 2)}
                for area in prompt.bubble_safe_areas
            ]
            payload["prompt"] += (
                " Speech overlay rectangles as percentages of the native frame "
                "(x/width relative to frame width; y/height relative to frame height; origin top-left): "
                + json.dumps(rectangles)
                + ". Keep important faces, hair and hands entirely outside these actual planned rectangles. "
                "Continuous scene background is allowed inside them; do not turn the whole top band into blank space."
            )
        save(episode / "prompts" / f"panel-{panel.panel}.json", payload)
    return episode / "prompts"


def record_image(episode, panel, source, started, completed):
    a = datetime.fromisoformat(started.replace("Z", "+00:00")); b = datetime.fromisoformat(completed.replace("Z", "+00:00"))
    if a.tzinfo is None or b.tzinfo is None or b < a: raise ValueError("invalid generation interval")
    manifest = episode / "prompts" / f"panel-{panel}.json"
    prompt = load(manifest)
    script = EpisodeScriptModel.model_validate(load(episode / "script.json"))
    target_size = script.panel_sizes()[panel - 1]
    if tuple(prompt["size"]) != target_size or prompt.get("rendering_policy", "legacy_contain") != script.rendering_policy:
        raise ValueError("provider manifest rendering policy/size is stale")
    path = episode / "generation-record.json"
    record = load(path) if path.exists() else {"provider":"Codex native imagegen", "image_model":"unverified", "records":[]}
    if any(x['panel']==panel and x['revision']==prompt['revision'] for x in record['records']):
        raise ValueError("panel/revision already registered; do not overwrite actual generation")
    target = episode / "raw" / f"panel-{panel}.png"; target.parent.mkdir(exist_ok=True)
    with Image.open(source) as image:
        original = image.size
        if script.rendering_policy == "frame_native_v1":
            ImageOps.fit(image.convert("RGB"), target_size, method=Image.Resampling.LANCZOS).save(target)
        else:
            image.convert("RGB").resize(target_size,Image.Resampling.LANCZOS).save(target)
    record['records'].append({"panel":panel,"revision":prompt['revision'],"provider_output":str(source),
        "provider_size":original,"raw_output":str(target),"raw_size":target_size,
        "normalization":("RGB aspect-preserving center crop to native frame before text" if script.rendering_policy == "frame_native_v1" else "RGB and delivery-size normalization only"), "prompt_manifest":str(manifest),
        "prompt_sha256":file_sha256(manifest),"reference_images":prompt['reference_images'],
        "started_at":started,"completed_at":completed,"elapsed_seconds":(b-a).total_seconds(),"token_usage":None})
    save(path, record)
    return target


def verify_visual(episode):
    report = load(episode / "visual-review.json")
    if report.get("overall", report.get("outcome")) != "pass" or not report.get("reviewer_id"):
        raise ValueError("independent visual review has not passed")
    if report.get("findings"):
        raise ValueError("visual findings remain")
    script = EpisodeScriptModel.model_validate(load(episode / "script.json"))
    expected = [f"final/page-{i:02}.png" for i in range(1,len(script.output_layout)+1)]
    if report.get("reviewed_pages") != expected:
        raise ValueError("visual review must cover every page in reading order")
    for name in expected:
        if report.get("page_sha256",{}).get(name) != file_sha256(episode / name):
            raise ValueError(f"stale visual review: {name}")
    if report.get("content_sha256") != semantic_content_sha256(episode / "brief.json",episode / "script.json"):
        raise ValueError("visual review content changed")
    if report.get("layout_sha256") != layout_sha256(episode / "script.json"):
        raise ValueError("visual review layout changed")
    return report, expected


def finalize(episode, history):
    from validate_episode import validate_episode
    from update_history import _update_history
    require_content_review(episode); require_content_lock(episode); require_layout_preflight(episode)
    visual, pages = verify_visual(episode)
    _, issues = validate_episode(episode)
    if issues: raise ValueError("; ".join(issues))
    brief = BriefModel.model_validate(load(episode / "brief.json"))
    state = {"status":"review_pending", "content_review":"PASS", "visual_qa":"PASS"}
    if brief.topic_origin == "editorial_scout":
        state["topic_research_sha256"] = file_sha256(episode / "topic-research.json")
    save(episode / "review-state.json",state)
    report = episode / "qa-report.md"
    automated = report.read_text().split("## Agent QA")[0].rstrip()
    write_text_atomic(report, automated + "\n\n## Agent QA\n\n"
        "Independent content review: content-review.json (PASS).\n\n"
        f"Independent visual review: visual-review.json; reviewer {visual['reviewer_id']} (PASS).\n\n"
        "Current content/layout/page hashes verified. Local review_pending; not published.\n")
    _update_history(episode,history,"draft")
    target = episode / f"{brief.episode_id}-PNG-{len(pages)}pages.zip"
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
        for name in pages: archive.write(episode/name,Path(name).name)
        archive.write(episode/"caption.txt","caption.txt")
    return target


def mark(episode, stage, event):
    path = episode / "timing.json"
    data = load(path) if path.exists() else {"schema_version":"1.1","token_usage":None,"events":[]}
    data.setdefault("events",[]).append({"stage":stage,"event":event,"at":datetime.now(timezone.utc).isoformat()})
    save(path,data); return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["packet","sources","prepare-prompts","record-image","finalize","mark"])
    parser.add_argument("--episode-dir",type=Path,required=True)
    parser.add_argument("--history",type=Path)
    parser.add_argument("--panel",type=int);parser.add_argument("--source",type=Path)
    parser.add_argument("--started");parser.add_argument("--completed")
    parser.add_argument("--stage");parser.add_argument("--event",choices=["start","end"])
    args=parser.parse_args();ep=args.episode_dir.resolve()
    try:
        if args.command=="packet":result=packet(ep)
        elif args.command=="sources":result=sources(ep)
        elif args.command=="prepare-prompts":result=prepare_prompts(ep)
        elif args.command=="record-image":
            if not all([args.panel,args.source,args.started,args.completed]):raise ValueError("image registration requires panel/source/started/completed")
            result=record_image(ep,args.panel,args.source,args.started,args.completed)
        elif args.command=="finalize":
            if not args.history:raise ValueError("finalize requires an explicit history path")
            result=finalize(ep,args.history)
        else:
            if not args.stage or not args.event:raise ValueError("mark requires stage/event")
            result=mark(ep,args.stage,args.event)
        print(json.dumps(result,ensure_ascii=False) if isinstance(result,dict) else result)
    except (ValueError,OSError,TypeError) as error:
        parser.exit(1,f"production failed: {error}\n")

if __name__ == "__main__":main()
