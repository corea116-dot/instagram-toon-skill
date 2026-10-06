"""Speech-bubble body/tail joins stay open, including near rounded corners."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pytest
from PIL import Image, ImageDraw
from episode_models import BoxModel
from rendering import _draw_speech_bubble, TAIL_HEIGHT

@pytest.mark.parametrize('base,tip', [(150,150),(74,54),(326,346)])
def test_tail_join_has_no_internal_border(base, tip):
    image = Image.new('RGB', (400,250), '#88aa88')
    box = BoxModel(x=50,y=30,width=300,height=150)
    _draw_speech_bubble(ImageDraw.Draw(image),box,base,tip)
    bottom = box.y + box.height - TAIL_HEIGHT
    # The old independent polygon drew a dark horizontal base at bottom-2.
    assert image.getpixel((base,bottom-2)) == (255,255,255)
    assert image.getpixel((base,bottom)) == (255,255,255)
    assert image.getpixel((200,30)) == (35,38,47)
    assert image.getpixel((tip,180)) == (35,38,47)
    assert image.getpixel((200,190)) == (136,170,136)
