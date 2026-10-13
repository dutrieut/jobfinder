from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from jobfinder.config import Config, load_config

# ---------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------


def test_load_config_returns_config_instance(config_file):
    config = load_config(config_file)

    assert isinstance(config, Config)


def test_load_config_reads_all_sections(config_file):
    config = load_config(config_file)

    assert len(config.ats) == 1
    assert config.ats[0].name == "greenhouse"
    assert config.ats[0].companies[0].name == "A-TEK"

    assert config.http.timeout_s == 20
    assert config.http.delay_s == 0.5
    assert config.http.retry.number == 5
    assert config.http.retry.backoff_factor == 1.0
    assert config.http.retry.respect_retry_after_header is True
    assert config.http.retry.status_forcelist == [429, 500, 502, 503, 504]

    assert config.search.locations == ["Paris", "London"]

    assert config.storage.storage_type == "json"
    assert config.storage.data_dir == Path("data")


def test_load_config_accepts_empty_ats(valid_config_data):
    valid_config_data["ats"] = []

    config = Config.model_validate(valid_config_data)

    assert config.ats == []


def test_load_config_accepts_empty_companies(valid_config_data):
    valid_config_data["ats"][0]["companies"] = []

    config = Config.model_validate(valid_config_data)

    assert config.ats[0].companies == []


def test_load_config_rejects_missing_locations(valid_config_data):
    valid_config_data["search"]["locations"] = []

    with pytest.raises(ValidationError) as exc_info:
        Config.model_validate(valid_config_data)

    assert exc_info.value.errors()[0]["type"] == "too_short"


def test_load_config_missing_file_raises_error(tmp_path):
    path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_config(path)


# ---------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------


def test_invalid_yaml_raises_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("ats: [invalid\nhttp: {", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_config(path)


def test_empty_yaml_raises_validation_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


# ---------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["ats", "http", "search", "storage"],
)
def test_missing_top_level_field_raises_validation_error(
    valid_config_data,
    missing_field,
):
    del valid_config_data[missing_field]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("http", "timeout_s"),
        ("http", "delay_s"),
        ("http", "retry"),
        ("search", "locations"),
        ("storage", "type"),
        ("storage", "data_dir"),
    ],
)
def test_missing_required_field_raises_validation_error(
    valid_config_data,
    section,
    field,
):
    del valid_config_data[section][field]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_missing_ats_name_raises_validation_error(valid_config_data):
    del valid_config_data["ats"][0]["name"]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_missing_ats_endpoint_raises_validation_error(valid_config_data):
    del valid_config_data["ats"][0]["endpoint"]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_missing_ats_companies_raises_validation_error(valid_config_data):
    del valid_config_data["ats"][0]["companies"]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_missing_company_name_raises_validation_error(valid_config_data):
    del valid_config_data["ats"][0]["companies"][0]["name"]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_missing_company_token_raises_validation_error(valid_config_data):
    del valid_config_data["ats"][0]["companies"][0]["token"]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


# ---------------------------------------------------------------------
# Unknown fields
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("section", "unknown_field"),
    [
        ("http", "unknown_option"),
        ("search", "unknown_option"),
        ("storage", "unknown_option"),
    ],
)
def test_unknown_field_raises_validation_error(
    valid_config_data,
    section,
    unknown_field,
):
    valid_config_data[section][unknown_field] = True

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_unknown_ats_field_raises_validation_error(valid_config_data):
    valid_config_data["ats"][0]["unknown_option"] = True

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_unknown_company_field_raises_validation_error(valid_config_data):
    valid_config_data["ats"][0]["companies"][0]["unknown_option"] = True

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


# ---------------------------------------------------------------------
# HTTP validation
# ---------------------------------------------------------------------


@pytest.mark.parametrize("timeout_s", [0, -1, -0.5])
def test_non_positive_timeout_is_rejected(valid_config_data, timeout_s):
    valid_config_data["http"]["timeout_s"] = timeout_s

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


@pytest.mark.parametrize("delay_s", [-1, -0.1])
def test_negative_delay_is_rejected(valid_config_data, delay_s):
    valid_config_data["http"]["delay_s"] = delay_s

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


@pytest.mark.parametrize("retries", [-1, -5])
def test_negative_retries_are_rejected(valid_config_data, retries):
    valid_config_data["http"]["retry"]["number"] = retries

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_zero_delay_is_allowed(valid_config_data):
    valid_config_data["http"]["delay_s"] = 0

    config = Config.model_validate(valid_config_data)

    assert config.http.delay_s == 0


def test_zero_retries_is_allowed(valid_config_data):
    valid_config_data["http"]["retry"]["number"] = 0

    config = Config.model_validate(valid_config_data)

    assert config.http.retry.number == 0


def test_fractional_retries_are_rejected(valid_config_data):
    valid_config_data["http"]["retries"] = 1.5

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


# ---------------------------------------------------------------------
# Storage validation
# ---------------------------------------------------------------------


@pytest.mark.parametrize("storage_type", ["sqlite", "postgresql", "unknown"])
def test_unsupported_storage_type_is_rejected(
    valid_config_data,
    storage_type,
):
    valid_config_data["storage"]["type"] = storage_type

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_storage_type_alias_is_available_as_storage_type(valid_config_data):
    config = Config.model_validate(valid_config_data)

    assert config.storage.storage_type == "json"


def test_storage_data_dir_is_converted_to_path(valid_config_data):
    config = Config.model_validate(valid_config_data)

    assert isinstance(config.storage.data_dir, Path)


# ---------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("search", "locations", "Paris"),
        ("http", "timeout_s", "invalid"),
        ("http", "delay_s", "invalid"),
        ("http", "retries", "invalid"),
    ],
)
def test_invalid_field_type_is_rejected(
    valid_config_data,
    section,
    field,
    value,
):
    valid_config_data[section][field] = value

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_invalid_ats_list_type_is_rejected(valid_config_data):
    valid_config_data["ats"] = "greenhouse"

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_invalid_company_list_item_is_rejected(valid_config_data):
    valid_config_data["ats"][0]["companies"] = ["A-TEK"]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)


def test_invalid_location_item_type_is_rejected(valid_config_data):
    valid_config_data["search"]["locations"] = ["Paris", 123]

    with pytest.raises(ValidationError):
        Config.model_validate(valid_config_data)
