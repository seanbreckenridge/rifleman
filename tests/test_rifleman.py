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
    # should ignore tests_dir
    actions = r.collect_actions([__file__, tests_dir, os.path.join(project_root, "README.md")])
    assert 'black "$@"' in actions.keys()
    assert 'prettier -w "$@"' in actions.keys()
    assert len(actions.keys()) == 2


if __name__ == "__main__":
    pytest.main()
