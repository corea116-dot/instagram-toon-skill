"""Frame geometry, crop-before-text and pixel-exact delivery regression tests."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pytest
from PIL import Image, ImageDraw, ImageChops, ImageOps
from pydantic import ValidationError
from test_output_layout import _make_episode
from episode_models import EpisodeScriptModel
from frame_geometry import panel_sizes, grid_geometry
from content_review import layout_sha256
from delivery import render_delivery, delivery_paths
from rendering import render_carousel, find_korean_font, RenderError
from production_tools import record_image
from validate_episode import _check_images


def native_episode(tmp_path, layout=(1, 2, 3, 4)):
    ep = _make_episode(tmp_path, layout)
    data = json.loads((ep / 'script.json').read_text())
    data['rendering_policy'] = 'frame_native_v1'
    for panel, (width, height) in zip(data['panels'], panel_sizes(layout)):
        panel['dialogue'][0].update(x=30, y=30, width=width-60, height=150)
    (ep / 'script.json').write_text(json.dumps(data))
    return ep, data


def test_all_slots():
    assert panel_sizes((1,2,3,4)) == ((1080,1350),(1008,630),(1008,630),(1008,594),(492,660),(492,660),*((492,621),)*4)


@pytest.mark.parametrize('part', ['bubble', 'tail', 'card', 'presenter', 'cardtext'])
def test_native_bounds(tmp_path, part):
    from test_information_cards import card_payload
    ep, data = native_episode(tmp_path)
    panel = data['panels'][1]
    if part == 'bubble': panel['dialogue'][0]['y'] = 600
    elif part == 'tail': panel['dialogue'][0]['tail_anchor'] = {'x':20,'y':631}
    else:
        # Existing card geometry is legal on the legacy canvas but outside this short slot.
        data['schema_version']='1.2'
        for p in data['panels']:
            p.update(panel_job=str(p['panel']),new_information='test',reader_takeaway='test',scope='test',text_budget=180)
        card=card_payload()
        panel['information_card']=card
    with pytest.raises(ValidationError): EpisodeScriptModel.model_validate(data)


def test_layout_hash_policy_and_legacy(tmp_path):
    ep, data = native_episode(tmp_path)
    native = layout_sha256(ep/'script.json')
    del data['rendering_policy']
    (ep/'script.json').write_text(json.dumps(data))
    legacy = layout_sha256(ep/'script.json')
    data['rendering_policy']='legacy_contain'
    (ep/'script.json').write_text(json.dumps(data))
    assert legacy == layout_sha256(ep/'script.json') != native
    assert EpisodeScriptModel.model_validate(data).panel_sizes() == ((1080,1350),)*10


def test_native_delivery_keeps_every_lettered_pixel(tmp_path):
    ep, data = native_episode(tmp_path)
    script = EpisodeScriptModel.model_validate(data)
    paths = delivery_paths(ep,10,script.output_layout)
    originals=[]
    for index,(path,size) in enumerate(zip(paths.rendered_panels,script.panel_sizes())):
        path.parent.mkdir(exist_ok=True)
        art=Image.new('RGB',size,(100+index,40,80))
        draw=ImageDraw.Draw(art)
        draw.rectangle((0,0,size[0]-1,size[1]-1),outline='black',width=3)
        draw.text((1,size[1]-12),'TEXT EDGE',fill='white')
        art.save(path); originals.append(art)
    render_delivery(ep,10,script.output_layout,None,'frame_native_v1')
    for page in paths.pages:
        with Image.open(page.output_path) as image:
            sizes,positions=(((1080,1350),),((0,0),)) if len(page.panel_numbers)==1 else grid_geometry(len(page.panel_numbers))
            for n,size,pos in zip(page.panel_numbers,sizes,positions):
                crop=image.crop((*pos,pos[0]+size[0],pos[1]+size[1]))
                assert ImageChops.difference(crop, originals[n-1]).getbbox() is None
    Image.new('RGB',(1080,1350)).save(paths.rendered_panels[1])
    with pytest.raises(RenderError):render_delivery(ep,10,script.output_layout,2,'frame_native_v1')


def test_record_aspect_crop_then_text_and_sizes(tmp_path):
    ep,data=native_episode(tmp_path)
    script=EpisodeScriptModel.model_validate(data)
    (ep/'prompts').mkdir()
    (ep/'prompts/panel-2.json').write_text(json.dumps({'revision':0,'size':[1008,630],'rendering_policy':'frame_native_v1','reference_images':[]}))
    original=Image.new('RGB',(1200,900),'#884422')
    ImageDraw.Draw(original).ellipse((400,250,800,650),fill='white')
    source=tmp_path/'source.png';original.save(source)
    raw=record_image(ep,2,source,'2026-10-02T00:00:00Z','2026-10-02T00:00:01Z')
    expected=ImageOps.fit(original,(1008,630),method=Image.Resampling.LANCZOS)
    with Image.open(raw) as actual: assert ImageChops.difference(actual,expected).getbbox() is None
    rendered, entries=render_carousel(raw,script.panels[1],find_korean_font(),(1008,630))
    assert rendered.size==(1008,630)
    assert entries and all(e.box.x+e.box.width<=1008 and e.box.y+e.box.height<=630 for e in entries)
    assert _check_images(ep,(10,script.output_layout))==()
    Image.new('RGB',(1080,1350)).save(raw)
    assert 'expected 1008x630' in _check_images(ep,(10,script.output_layout))[0]


def test_record_rejects_stale_provider_size(tmp_path):
    ep,_=native_episode(tmp_path)
    (ep/'prompts').mkdir()
    (ep/'prompts/panel-2.json').write_text(json.dumps({'revision':0,'size':[1080,1350]}))
    with pytest.raises(ValueError,match='stale'):
        record_image(ep,2,tmp_path/'not-read.png','2026-10-02T00:00:00Z','2026-10-02T00:00:01Z')


def test_native_preflight_semantic_lock_and_stale_policy(tmp_path):
    from test_informational_episode import informational_episode, modernize_episode, write_json, modern_review_payload, write_content_lock
    from content_review import semantic_content_sha256
    from layout_preflight import run_layout_preflight, layout_preflight_issues
    episode=modernize_episode(informational_episode(tmp_path,(1,1,1,1,1)))
    data=json.loads((episode/'script.json').read_text())
    before=semantic_content_sha256(episode/'brief.json',episode/'script.json')
    data['rendering_policy']='frame_native_v1'
    write_json(episode/'script.json',data)
    assert semantic_content_sha256(episode/'brief.json',episode/'script.json')==before
    write_json(episode/'content-review.json',modern_review_payload(episode))
    write_content_lock(episode)
    _, record=run_layout_preflight(episode)
    assert record.outcome=='pass'
    assert all(b.font_size==b.effective_font_size for b in record.bubbles)
    data.pop('rendering_policy')
    write_json(episode/'script.json',data)
    assert any('stale' in issue for issue in layout_preflight_issues(episode))


def test_native_mock_compose_validate_and_manifest(tmp_path):
    from compose_episode import compose, ComposeOptions
    from validate_episode import validate_episode
    ep,data=native_episode(tmp_path)
    compose(ComposeOptions(ep,True,None))
    _, issues=validate_episode(ep)
    assert not issues
    prompt=json.loads((ep/'prompts/panel-2.json').read_text())
    assert prompt['size']==[1008,630] and prompt['rendering_policy']=='frame_native_v1'
    assert 'no letterboxing' in prompt['prompt']
    manifest=json.loads((ep/'final/composition.json').read_text())
    assert manifest['panel_sizes']==[list(s) for s in panel_sizes((1,2,3,4))]
    prompt['rendering_policy']='legacy_contain'
    (ep/'prompts/panel-2.json').write_text(json.dumps(prompt))
    with pytest.raises(RenderError,match='stale'):
        compose(ComposeOptions(ep,False,None,True))


def test_prepare_native_prompt_percent_rectangles_and_preserves_manifest(tmp_path):
    from production_tools import prepare_prompts
    ep,data=native_episode(tmp_path)
    prepare_prompts(ep)
    marker='origin top-left): '
    for number, (width,height) in enumerate(panel_sizes((1,2,3,4)),start=1):
        payload=json.loads((ep/f'prompts/panel-{number}.json').read_text())
        rectangles=json.loads(payload['prompt'].split(marker,1)[1].split('. Keep important',1)[0])
        assert rectangles==[{'x':round(3000/width,2),'y':round(3000/height,2),
                            'width':round(100*(width-60)/width,2),'height':round(15000/height,2)}]
        assert payload['size']==[width,height]
        assert 'faces, hair and hands entirely outside these actual planned rectangles' in payload['prompt']
        assert 'Continuous scene background is allowed inside them' in payload['prompt']
    manifest=ep/'prompts/panel-2.json'
    original=manifest.read_bytes()
    with pytest.raises(ValueError,match='preserve it'):
        prepare_prompts(ep)
    assert manifest.read_bytes()==original


def test_prepare_legacy_prompt_has_no_native_percentage_directive(tmp_path):
    from production_tools import prepare_prompts
    ep=_make_episode(tmp_path,(1,1,1))
    prepare_prompts(ep)
    payload=json.loads((ep/'prompts/panel-1.json').read_text())
    assert 'Speech overlay rectangles as percentages' not in payload['prompt']
