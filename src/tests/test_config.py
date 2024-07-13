import tomllib
import pytest
from pathlib import Path


@pytest.fixture
def config_path():
    return Path(__file__).parent.parent.parent / 'config.example.toml'

@pytest.fixture
def config(config_path):
    if config_path.exists():
        with open(config_path, 'r') as f:
            return tomllib.loads(f.read())
    return {}

def test_existance(config_path):
    assert config_path.exists()
    assert config_path.is_file()

def test_defaults(config):
    for key in ['paths', 'gotify']:
        assert key in config.keys()
    
    assert config['paths'].get('db_folder') == '.'
    assert config['paths'].get('destination') == '.'
    
    assert config['gotify'].get('url') == 'https://gotify.example.com'
    assert config['gotify'].get('app_name') == ''
    assert config['gotify'].get('app_key') == ''