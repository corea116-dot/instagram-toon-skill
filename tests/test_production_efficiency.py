import json
import shutil
from pathlib import Path
import pytest
from PIL import Image
from test_informational_episode import informational_episode, modernize_episode, modern_review_payload, write_json, write_content_lock
from content_review import semantic_content_sha256, layout_sha256
from layout_preflight import run_layout_preflight, require_layout_preflight
from compose_episode import ComposeOptions, compose
from production_tools import packet, sources, prepare_prompts, verify_visual, review_view
from episode_models import EpisodeScriptModel
from rendering import render_carousel, find_korean_font


def modern(tmp_path):
    ep=modernize_episode(informational_episode(tmp_path))
    write_json(ep/'content-review.json',modern_review_payload(ep))
    write_content_lock(ep)
    return ep


def test_packet_keeps_every_visible_word_without_answer_leak(tmp_path):
    ep=modern(tmp_path);brief=json.loads((ep/'brief.json').read_text())
    brief['question_answer']['one_line_answer']='SECRET INTENDED ANSWER'
    write_json(ep/'brief.json',brief)
    packet(ep)
    script=EpisodeScriptModel.model_validate_json((ep/'script.json').read_text())
    visible=(ep/'review-visible.txt').read_text()
    assert 'SECRET INTENDED ANSWER' not in visible
    assert all(d.text in visible for p in script.panels for d in p.dialogue)
    assert (ep/'layout-diagnostic.json').exists()
    assert not (ep/'layout-preflight.json').exists()
    with pytest.raises((ValueError,FileNotFoundError)):sources(ep)


def test_diagnostic_never_satisfies_generation_gate(tmp_path):
    ep=modern(tmp_path);run_layout_preflight(ep,draft=True)
    with pytest.raises(ValueError):require_layout_preflight(ep)
    (ep/'content-lock.json').unlink()
    with pytest.raises(ValueError):run_layout_preflight(ep)


def test_tail_only_changes_layout_hash_and_pixels(tmp_path):
    ep=modern(tmp_path);script_path=ep/'script.json'
    old_sem=semantic_content_sha256(ep/'brief.json',script_path);old_layout=layout_sha256(script_path)
    before=EpisodeScriptModel.model_validate_json(script_path.read_text())
    data=json.loads(script_path.read_text());data['panels'][0]['dialogue'][0]['tail_anchor']={'x':950,'y':1000}
    write_json(script_path,data)
    assert semantic_content_sha256(ep/'brief.json',script_path)==old_sem
    assert layout_sha256(script_path)!=old_layout
    after=EpisodeScriptModel.model_validate(data)
    raw=ep/'test.png';Image.new('RGB',(1080,1350),'#abcdef').save(raw)
    left,_=render_carousel(raw,before.panels[0],find_korean_font())
    right,_=render_carousel(raw,after.panels[0],find_korean_font())
    assert left.tobytes()!=right.tobytes()


def test_recompose_preserves_provider_manifest_and_raw(tmp_path):
    ep=modern(tmp_path);run_layout_preflight(ep)
    compose(ComposeOptions(ep,True,None))
    prompt=ep/'prompts/panel-1.json';raw=ep/'raw/panel-1.png'
    original=(prompt.read_bytes(),raw.read_bytes())
    data=json.loads((ep/'script.json').read_text());data['panels'][0]['dialogue'][0]['tail_anchor']={'x':950,'y':1000}
    write_json(ep/'script.json',data);run_layout_preflight(ep)
    compose(ComposeOptions(ep,False,1,recompose_only=True))
    assert (prompt.read_bytes(),raw.read_bytes())==original
    with pytest.raises(ValueError):prepare_prompts(ep)


def test_visual_review_cannot_reuse_old_pages(tmp_path):
    ep=modern(tmp_path);run_layout_preflight(ep);compose(ComposeOptions(ep,True,None))
    write_json(ep/'visual-review.json',{'overall':'pass','reviewer_id':'independent','findings':[],
        'reviewed_pages':[f'final/page-{i:02}.png' for i in range(1,6)],'page_sha256':{}})
    with pytest.raises(ValueError,match='stale visual review'):verify_visual(ep)


def test_source_release_requires_current_packet(tmp_path):
    ep=modern(tmp_path);packet(ep)
    review=json.loads((ep/'content-review.json').read_text())
    write_json(ep/'blind-read.json',review['blind_read'])
    assert sources(ep)['episode_id']=='EP-999'
    data=json.loads((ep/'script.json').read_text());data['panels'][0]['dialogue'][0]['text']+=' 확인'
    write_json(ep/'script.json',data)
    with pytest.raises(ValueError,match='stale'):sources(ep)


def test_prepare_without_placeholder_art_and_preserve_on_retry(tmp_path):
    ep=modern(tmp_path);run_layout_preflight(ep);prepare_prompts(ep)
    assert not (ep/'raw').exists()
    p=ep/'prompts/panel-1.json';before=p.read_bytes()
    assert 'Palette:' in json.loads(before)['prompt']
    with pytest.raises(ValueError):prepare_prompts(ep)
    assert p.read_bytes()==before


def test_usage_deduplicates_and_excludes_outside_interval(tmp_path):
    from usage_summary import summarize
    record={'type':'token_usage_record','timestamp':'2026-10-01T00:01:00Z','payload':{'response_id':'one','usage':{'input_tokens':100,'cached_input_tokens':80,'output_tokens':10,'reasoning_output_tokens':3}}}
    log=tmp_path/'run.jsonl';log.write_text(json.dumps(record)+'\n'+json.dumps(record)+'\n')
    result=summarize([log],'2026-10-01T00:00:00Z','2026-10-01T00:02:00Z')
    assert result['responses']==1 and result['uncached_input_tokens']==20
    assert result['usage']['output_tokens']==10
    assert summarize([log],'2026-10-02','2026-10-03')['responses']==0
