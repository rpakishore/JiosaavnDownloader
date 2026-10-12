import logging
from unittest.mock import patch

import requests

from jiosaavn.notify import gotify


def test_noop_without_url_or_token():
    with patch('jiosaavn.notify.requests.post') as post:
        gotify('', 'tok', 't', 'm')
        gotify('https://g.example', '', 't', 'm')
    post.assert_not_called()


def test_posts_message_with_key_in_header():
    with patch('jiosaavn.notify.requests.post') as post:
        gotify('https://g.example/', 'secret', 'Title', 'Body', priority=5)
    args, kwargs = post.call_args
    assert args == ('https://g.example/message',)
    assert 'secret' not in args[0]
    assert kwargs['headers'] == {'X-Gotify-Key': 'secret'}
    assert kwargs['timeout'] == 10
    assert kwargs['json']['title'] == 'Title'
    assert kwargs['json']['message'] == 'Body'
    assert kwargs['json']['priority'] == 5
    assert kwargs['json']['extras']['client::display']['contentType'] == 'text/markdown'


def test_network_error_is_logged_not_raised(caplog):
    with patch('jiosaavn.notify.requests.post', side_effect=requests.ConnectionError('boom')):
        with caplog.at_level(logging.WARNING):
            gotify('https://g.example', 'secret', 't', 'm')
    assert 'boom' in caplog.text
    assert 'secret' not in caplog.text


def test_http_error_is_logged_not_raised(caplog):
    response = requests.Response()
    response.status_code = 401
    with patch('jiosaavn.notify.requests.post', return_value=response):
        with caplog.at_level(logging.WARNING):
            gotify('https://g.example', 'secret', 't', 'm')
    assert '401' in caplog.text
    assert 'secret' not in caplog.text
