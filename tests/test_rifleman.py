import os

import pytest

import rifleman

tests_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(tests_dir, os.path.pardir)


def test_format() -> None:
    assert True


if __name__ == "__main__":
    pytest.main()
