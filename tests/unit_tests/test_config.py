import pytest
from _pytest.monkeypatch import MonkeyPatch

from sway.checks import CheckNotExistsError, CheckState
from sway.config import Config, get_config_file_path


@pytest.mark.original_config_file_path
def test_config_config_file_path(monkeypatch: MonkeyPatch) -> None:
    path = "/tmp/test_config.yml"

    monkeypatch.setenv("SWAY_CONFIG_FILE_PATH", path)

    assert get_config_file_path() == path


def test_config_checks_amount(config: Config) -> None:
    assert len(config.checks) == 4


def test_config_checks_server_port(config: Config) -> None:
    assert config.server_port == 60413


def test_config_checks_server_host(config: Config) -> None:
    assert config.server_host == "127.0.0.1"


def test_config_checks_server_max_connections(config: Config) -> None:
    assert config.server_max_connections == 5


def test_config_settings(config: Config) -> None:
    assert config._settings == {
        "server": {"port": 60413, "host": "127.0.0.1", "max_connections": 5},
        "checks": {
            "functional_service": {"command": "true"},
            "broken_service": {"command": "false"},
            "multiple_words_command": {"command": "echo hello"},
            "multiple_items_command": {"command": ["echo", "hello"]},
        },
    }


def test_get_check_by_name_exists(config: Config) -> None:
    assert (
        config.get_check_by_name(name="functional_service").name
        == "functional_service"
    )


def test_get_check_by_name_not_exists(config: Config) -> None:
    with pytest.raises(CheckNotExistsError):
        config.get_check_by_name(name="not_exists")
