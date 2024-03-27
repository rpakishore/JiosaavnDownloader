import pytest
import requests

import json

from jiosaavn.API import SaavnMe

@pytest.fixture
def saavn():
    return SaavnMe()

def test_saavn_address(saavn):
    assert requests.get(saavn.BASEURL), 'Cannot Access BASEURL'
    
    #Check Playlist
    _res = requests.get(f"{saavn.url('playlist')}?id=109815423")
    assert json.loads(_res.content.decode()).get('success') is True, 'Cannot Access Playlist URL'

def test_song_retrieval(saavn):
    song = saavn.song(url='https://www.jiosaavn.com/song/houdini/OgwhbhtDRwM')
    assert song.id == 'JdJ_osp0'
    assert song.image_url != ''
    assert song.media_url != ''

def test_playlist_retrieval(saavn):
    pl = saavn.playlist('109815423')
    assert len(pl) > 10
    assert pl[0].id != pl[1].id