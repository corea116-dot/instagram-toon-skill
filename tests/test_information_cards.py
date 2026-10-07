"""Synthetic character-led information cards; no real policy claims or art QA."""

import json
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from test_informational_episode import (
    informational_episode, modernize_episode, modern_review_payload, write_json,
    write_content_lock,
)
from content_review import content_review_issues, layout_sha256, semantic_content_sha256, _canonical_sha256
from episode_models import EpisodeScriptModel, CompositionModel
from information_lock import content_lock_issues
from layout_preflight import run_layout_preflight
from rendering import render_carousel, find_korean_font
from validate_episode import _check_layout
from reference_policy import CharacterReferencePolicy


def card_payload(format_name="숫자 비교표"):
    return {
        "format": format_name, "design_reason": "조건을 나란히 비교한다",
        "area": {"x": 20, "y": 350, "width": 660, "height": 950},
        "texts": [
            {"id": "title", "text": "테스트용 투자 상품", "x": 40, "y": 370, "width": 620, "height": 280},
            {"id": "value", "text": "기준 100", "x": 40, "y": 690, "width": 620, "height": 200},
        ],
        "shapes": [{"x": 25, "y": 355, "width": 650, "height": 300, "shape": "rounded_rectangle", "fill": "#eeeeff"}],
        "presenter": {"character_id": "bgoon", "pose": "카드를 가리키며 설명", "explanation_bubble": 1,
            "area": {"x": 710, "y": 350, "width": 350, "height": 950}},
    }


def card_episode(tmp_path, layout=(1, 1, 1, 1, 1)):
    episode = modernize_episode(informational_episode(tmp_path, layout))
    payload = json.loads((episode / "script.json").read_text())
    panel = payload["panels"][0]
    panel["information_card"] = card_payload()
    panel["dialogue"][0]["text"] = "기준을 확인해."
    write_json(episode / "script.json", payload)
    write_json(episode / "content-review.json", modern_review_payload(episode))
    write_content_lock(episode)
    return episode


@pytest.mark.parametrize("format_name", ["나란한 숫자 비교표", "달력 옆에 붙인 준비물 메모"])
def test_free_card_formats_and_same_panel_presenter(tmp_path, format_name):
    episode = card_episode(tmp_path)
    payload = json.loads((episode / "script.json").read_text())
    payload["panels"][0]["information_card"]["format"] = format_name
    if format_name.startswith("달력"):
        card = payload["panels"][0]["information_card"]
        card["texts"][0].update(width=300, height=500)
        card["texts"][1].update(x=360, y=370, width=300, height=500)
        card["shapes"][0].update(shape="ellipse", height=550)
    script = EpisodeScriptModel.model_validate(payload)
    assert script.panels[0].information_card.format == format_name
    raw = tmp_path / "format-raw.png"
    Image.new("RGB", (1080, 1350), "white").save(raw)
    _, entries = render_carousel(raw, script.panels[0], find_korean_font())
    assert len([entry for entry in entries if entry.kind == "card"]) == 2
    assert content_review_issues(episode) == ()  # claim is in card, not speech


@pytest.mark.parametrize("mutation", ["no_presenter", "no_dialogue", "wrong_speaker", "blank_explanation", "overlap_presenter", "overlap_dialogue", "overlap_text", "outside_card", "text_budget", "old_version"])
def test_invalid_card_contracts(tmp_path, mutation):
    episode = card_episode(tmp_path)
    payload = json.loads((episode / "script.json").read_text())
    panel = payload["panels"][0]
    card = panel["information_card"]
    if mutation == "no_presenter": del card["presenter"]
    elif mutation == "no_dialogue": panel["dialogue"] = []
    elif mutation == "wrong_speaker": panel["dialogue"][0]["speaker"] = "someone"
    elif mutation == "blank_explanation": panel["dialogue"][0]["text"] = " "
    elif mutation == "overlap_presenter": card["presenter"]["area"]["x"] = 600
    elif mutation == "overlap_dialogue": panel["dialogue"][0]["y"] = 300
    elif mutation == "overlap_text": card["texts"][1]["y"] = 500
    elif mutation == "outside_card": card["texts"][1]["x"] = 500
    elif mutation == "text_budget": panel["text_budget"] = 12
    elif mutation == "old_version": payload["schema_version"] = "1.1"
    with pytest.raises(ValidationError): EpisodeScriptModel.model_validate(payload)


def test_card_geometry_only_preserves_review_and_lock(tmp_path):
    episode = card_episode(tmp_path)
    brief, path = episode / "brief.json", episode / "script.json"
    semantic, layout = semantic_content_sha256(brief, path), layout_sha256(path)
    payload = json.loads(path.read_text())
    payload["panels"][0]["information_card"]["texts"][1]["y"] += 10
    write_json(path, payload)
    assert semantic_content_sha256(brief, path) == semantic
    assert layout_sha256(path) != layout
    assert content_review_issues(episode) == content_lock_issues(episode) == ()
    payload["panels"][0]["information_card"]["texts"][1]["text"] = "기준 200"
    write_json(path, payload)
    assert any("stale" in issue for issue in content_review_issues(episode))
    assert any("stale" in issue for issue in content_lock_issues(episode))


def test_no_card_hashes_keep_old_contract(tmp_path):
    from episode_models import BriefModel
    episode = modernize_episode(informational_episode(tmp_path))
    script = EpisodeScriptModel.model_validate_json((episode / "script.json").read_text())
    brief = BriefModel.model_validate_json((episode / "brief.json").read_text())
    panels = script.model_dump(mode="json")["panels"]
    for panel in panels:
        panel.pop("information_card")
        panel.pop("text_budget")
        panel["dialogue"] = [{"speaker": item["speaker"], "text": item["text"]} for item in panel["dialogue"]]
    old_content = {"brief": brief.model_dump(mode="json", exclude={"output_layout", "status"}),
        "script": {"episode_id": script.episode_id, "title": script.title, "panels": panels}}
    old_layout = {"episode_id": script.episode_id, "output_layout": script.output_layout,
        "panels": [{"panel": panel.panel, "text_budget": panel.text_budget,
            "dialogue": [item.model_dump(mode="json") for item in panel.dialogue]} for panel in script.panels]}
    assert semantic_content_sha256(episode / "brief.json", episode / "script.json") == _canonical_sha256(old_content)
    assert layout_sha256(episode / "script.json") == _canonical_sha256(old_layout)


@pytest.mark.parametrize("layout", [(1, 1, 1), (2, 1), (3,), (4,)])
def test_card_render_and_actual_page_preflight(tmp_path, layout):
    episode = card_episode(tmp_path, layout)
    script = EpisodeScriptModel.model_validate_json((episode / "script.json").read_text())
    raw = tmp_path / "raw.png"
    Image.new("RGB", (1080, 1350), "pink").save(raw)
    result, layouts = render_carousel(raw, script.panels[0], find_korean_font())
    assert result.size == (1080, 1350)
    assert [entry.element_id for entry in layouts if entry.kind == "card"] == ["title", "value"]
    assert result.getpixel((21, 1000)) == (255, 255, 255)
    assert result.getpixel((900, 1000)) == (255, 192, 203)  # presenter art is not painted over
    _, preflight = run_layout_preflight(episode)
    assert any(item.kind == "card" for item in preflight.bubbles)
    assert preflight.outcome == "pass", preflight.issues
    final = episode / "final"
    final.mkdir()
    manifest = CompositionModel(schema_version="1.1", canvas=(1080, 1350), layouts=layouts, output_layout=script.output_layout)
    (final / "composition.json").write_text(manifest.model_dump_json())
    assert _check_layout(episode, (len(script.panels), script.output_layout)) == ()
    payload = manifest.model_dump(mode="json")
    payload["layouts"] = [entry for entry in payload["layouts"] if entry["kind"] != "card"]
    write_json(final / "composition.json", payload)
    assert any("missing" in issue for issue in _check_layout(episode, (len(script.panels), script.output_layout)))


def test_too_small_card_text_fails_final_page_preflight(tmp_path):
    episode = card_episode(tmp_path, (4,))
    payload = json.loads((episode / "script.json").read_text())
    payload["panels"][0]["information_card"]["texts"][1].update(text="지금 조건을 정확히 확인해야 합니다", height=140)
    write_json(episode / "script.json", payload)
    write_json(episode / "content-review.json", modern_review_payload(episode))
    write_content_lock(episode)
    _, result = run_layout_preflight(episode)
    assert result.outcome == "fail"
    assert any("card" in issue and "below 34px" in issue for issue in result.issues)


@pytest.mark.parametrize("layout", [(1, 1, 1), (2, 1), (3,), (4,)])
def test_full_composition_and_partial_refresh_keep_card_metadata(tmp_path, monkeypatch, layout):
    import compose_episode
    episode = card_episode(tmp_path, layout)
    run_layout_preflight(episode)
    policy = CharacterReferencePolicy(character_ids=("bgoon",), reference_images=("fixture.png",),
        identity_text="synthetic presenter", default_wardrobes={"bgoon": ("shirt", "shoes")})
    monkeypatch.setattr(compose_episode, "load_character_policy", lambda *args: policy)
    monkeypatch.setattr(compose_episode, "_primary_reference_images", lambda: ("fixture.png",))
    compose_episode.compose(compose_episode.ComposeOptions(episode_dir=episode, mock=True, panel=None))
    compose_episode.compose(compose_episode.ComposeOptions(episode_dir=episode, mock=True, panel=1))
    prompt = json.loads((episode / "prompts" / "panel-1.json").read_text())
    assert prompt["information_card"]["presenter"]["character_id"] == "bgoon"
    assert "Reserve completely blank card area" in prompt["prompt"]
    assert "never an information-card-only slide" in prompt["prompt"]
    manifest = json.loads((episode / "final" / "composition.json").read_text())
    assert len([entry for entry in manifest["layouts"] if entry["kind"] == "card"]) == 2
    assert _check_layout(episode, (sum(layout), layout)) == ()


@pytest.mark.parametrize("mutation", ["text", "small_font", "overlap"])
def test_final_validation_detects_bad_card_composition(tmp_path, mutation):
    episode = card_episode(tmp_path)
    script = EpisodeScriptModel.model_validate_json((episode / "script.json").read_text())
    raw = tmp_path / "raw.png"
    Image.new("RGB", (1080, 1350), "white").save(raw)
    _, entries = render_carousel(raw, script.panels[0], find_korean_font())
    manifest = CompositionModel(schema_version="1.1", canvas=(1080, 1350), layouts=entries, output_layout=script.output_layout).model_dump(mode="json")
    entry = manifest["layouts"][0]
    if mutation == "text": entry["lines"] = ["wrong text"]
    elif mutation == "small_font": entry["font_size"] = 26
    else: entry["box"].update(x=710, width=200)
    (episode / "final").mkdir()
    write_json(episode / "final" / "composition.json", manifest)
    issues = _check_layout(episode, (len(script.panels), script.output_layout))
    assert issues
    assert any({"text": "differs", "small_font": "34px", "overlap": "overlap"}[mutation] in issue for issue in issues)


def test_taped_memo_is_deterministic_and_stays_inside_card(tmp_path):
    episode = card_episode(tmp_path)
    payload = json.loads((episode / "script.json").read_text())
    card = payload["panels"][0]["information_card"]
    card["style"] = "taped_memo_v1"
    card["shapes"] = []
    card["texts"][0].update(x=50, y=470, width=600, height=180, role="label", accent="yellow")
    card["texts"][1].update(x=50, y=790, width=600, height=200, role="emphasis", accent="mint")
    panel = EpisodeScriptModel.model_validate(payload).panels[0]
    raw = tmp_path / "plain.png"
    Image.new("RGB", (1080, 1350), "pink").save(raw)
    first, layouts = render_carousel(raw, panel, find_korean_font())
    second, _ = render_carousel(raw, panel, find_korean_font())
    assert first.tobytes() == second.tobytes()
    colors = set(first.get_flattened_data())
    assert (255, 253, 247) in colors  # cream paper
    assert (223, 212, 183) in colors  # two tape strips
    assert (240, 217, 157) in colors  # yellow label
    assert (208, 225, 209) in colors  # mint emphasis marker
    assert first.getpixel((19, 1000)) == (255, 192, 203)
    assert first.getpixel((681, 1000)) == (255, 192, 203)
    assert first.getpixel((900, 1000)) == (255, 192, 203)
    assert [item.element_id for item in layouts if item.kind == "card"] == ["title", "value"]


def test_card_style_change_preserves_fact_lock_but_invalidates_layout(tmp_path):
    episode = card_episode(tmp_path)
    brief, path = episode / "brief.json", episode / "script.json"
    old_content, old_layout = semantic_content_sha256(brief, path), layout_sha256(path)
    payload = json.loads(path.read_text())
    card = payload["panels"][0]["information_card"]
    card.update(style="taped_memo_v1")
    card["texts"][1].update(role="emphasis", accent="yellow")
    write_json(path, payload)
    assert semantic_content_sha256(brief, path) == old_content
    assert layout_sha256(path) != old_layout
    assert content_review_issues(episode) == content_lock_issues(episode) == ()


@pytest.mark.parametrize("mutation", ["no_style", "body_accent", "unknown_style"])
def test_invalid_memo_style_contracts(tmp_path, mutation):
    episode = card_episode(tmp_path)
    payload = json.loads((episode / "script.json").read_text())
    card = payload["panels"][0]["information_card"]
    card["style"] = "taped_memo_v1"
    if mutation == "no_style":
        del card["style"]
        card["texts"][0]["role"] = "label"
    elif mutation == "body_accent":
        card["texts"][0]["accent"] = "yellow"
    else:
        card["style"] = "unregistered"
    with pytest.raises(ValidationError):
        EpisodeScriptModel.model_validate(payload)


def test_legacy_card_serialization_omits_new_style_defaults(tmp_path):
    episode = card_episode(tmp_path)
    script = EpisodeScriptModel.model_validate_json((episode / "script.json").read_text())
    card = script.panels[0].information_card.model_dump(mode="json")
    assert "style" not in card
    assert all("role" not in text and "accent" not in text for text in card["texts"])
