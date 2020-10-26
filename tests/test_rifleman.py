import os

import pytest

import rifleman

tests_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(tests_dir, os.path.pardir)
config_file = os.path.join(project_root, "config", "format.conf")


def test_format() -> None:
    # basic test to check if this classifies files fine
    r = rifleman.RifleMan(config_file)
    r.reload_config()
    r_dict = {r:cond for r, cond in r.rules}
    assert 'black "$@"' in r_dict
    assert 'prettier -w "$@"' in r_dict

if __name__ == "__main__":
    pytest.main()
