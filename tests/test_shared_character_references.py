from pathlib import Path

import pytest

from test_six_panel_workflow import _make_episode, SKILL_ROOT
from episode_models import BriefModel
from reference_policy import CharacterBibleModel, load_character_policy


@pytest.mark.parametrize("shared_folder", [False, True])
def test_shared_references_are_attached_once(
    tmp_path: Path, shared_folder: bool,
) -> None:
    # Given: two registered identities sharing a validated reference source.
    episode = _make_episode(tmp_path)
    brief_path = episode / "brief.json"
    brief = BriefModel.model_validate_json(brief_path.read_text(encoding="utf-8"))
    brief_path.write_text(
        brief.model_copy(update={"characters": ("bgoon", "friend")}).model_dump_json(),
        encoding="utf-8",
    )
    root = tmp_path / "skill"
    styles = root / "assets" / "references" / "styles"
    styles.mkdir(parents=True)
    (styles / "sample.png").write_bytes(b"path-validation-fixture")
    source = "assets/references/styles" if shared_folder else "assets/references/styles/sample.png"
    bible = CharacterBibleModel.model_validate_json(
        (SKILL_ROOT / "memory" / "character-bible.json").read_text(encoding="utf-8")
    )
    protagonist = bible.characters[0].model_copy(update={"reference_images": (source,)})
    friend = protagonist.model_copy(update={"id": "friend", "display_name": "friend"})
    path = root / "characters.json"
    path.write_text(
        bible.model_copy(update={"characters": (protagonist, friend)}).model_dump_json(by_alias=True),
        encoding="utf-8",
    )

    # When: the real character-policy loader aggregates both characters.
    policy = load_character_policy(episode, path, root)

    # Then: both identities remain, with only one shared attachment.
    assert policy.character_ids == ("bgoon", "friend")
    assert policy.reference_images == ("assets/references/styles/sample.png",)
