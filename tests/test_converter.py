import json
import zipfile
from pathlib import Path

import pytest

from oogc_nmse_converter.cli import main
from oogc_nmse_converter.converter import (
    ConversionError,
    convert_file,
    extract_members,
    member_metadata,
    read_nmsship,
)


def write_zip(path: Path, members: dict[str, object]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, json.dumps(data))
    return path


def test_conversion_with_all_three_members(tmp_path: Path):
    input_path = write_zip(
        tmp_path / "ship.nmsship",
        {
            "so.json": {"Name": "Test Ship", "Stats": {"Damage": 1}},
            "ccd.json": {"SelectedPreset": "PilotPreset", "CustomData": {"PaletteID": "Blue"}},
            "objects.json": [{"ObjectID": "Decoration"}],
        },
    )

    wrapper = read_nmsship(input_path)

    assert wrapper == {
        "Ship": {"Name": "Test Ship", "Stats": {"Damage": 1}},
        "CharacterCustomisationData": {
            "SelectedPreset": "PilotPreset",
            "CustomData": {"PaletteID": "Blue"},
        },
        "Base": {"Objects": [{"ObjectID": "Decoration"}]},
    }


def test_missing_so_json_error(tmp_path: Path):
    input_path = write_zip(tmp_path / "ship.nmsship", {"ccd.json": {}})

    with pytest.raises(ConversionError, match="missing required member so.json"):
        read_nmsship(input_path)


def test_default_json_output_name(tmp_path: Path):
    input_path = write_zip(tmp_path / "ship.nmsship", {"so.json": {"Name": "Test Ship"}})

    output_path = convert_file(input_path, output_format="json")

    assert output_path == tmp_path / "ship.nmse.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"Ship": {"Name": "Test Ship"}}


def test_default_nmscorv_output_name(tmp_path: Path):
    input_path = write_zip(tmp_path / "ship.nmsship", {"so.json": {"Name": "Test Ship"}})

    output_path = convert_file(input_path, output_format="nmscorv")

    assert output_path == tmp_path / "ship.nmscorv"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"Ship": {"Name": "Test Ship"}}


def test_cli_nmscorv_shortcut_writes_nmscorv(tmp_path: Path):
    input_path = write_zip(tmp_path / "ship.nmsship", {"so.json": {"Name": "Test Ship"}})

    exit_code = main([str(input_path), "--nmscorv"])

    output_path = tmp_path / "ship.nmscorv"
    assert exit_code == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"Ship": {"Name": "Test Ship"}}


def test_cli_output_override_ignores_format_suffix(tmp_path: Path):
    input_path = write_zip(tmp_path / "ship.nmsship", {"so.json": {"Name": "Test Ship"}})
    output_path = tmp_path / "custom.output"

    exit_code = main([str(input_path), "--format", "nmscorv", "-o", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    assert not (tmp_path / "ship.nmscorv").exists()


def test_omit_default_ccd(tmp_path: Path):
    input_path = write_zip(
        tmp_path / "ship.nmsship",
        {
            "so.json": {"Name": "Test Ship"},
            "ccd.json": {
                "SelectedPreset": "^",
                "CustomData": {
                    "PaletteID": "^",
                    "DescriptorGroups": [],
                    "Colours": [],
                    "TextureOptions": [],
                    "BoneScales": [],
                },
            },
        },
    )

    wrapper = read_nmsship(input_path, include_default_ccd=False)

    assert wrapper == {"Ship": {"Name": "Test Ship"}}


def test_cli_refuses_overwrite_without_force(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    input_path = write_zip(tmp_path / "ship.nmsship", {"so.json": {"Name": "Test Ship"}})
    output_path = tmp_path / "ship.nmse.json"
    output_path.write_text("existing", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([str(input_path)])

    assert exc_info.value.code == 2
    assert "refusing to overwrite existing file" in capsys.readouterr().err
    assert output_path.read_text(encoding="utf-8") == "existing"


def test_convert_raw_objects_json_array(tmp_path: Path):
    input_path = tmp_path / "objects.json"
    objects = [
        {
            "Timestamp": 123,
            "ObjectID": "Decoration",
            "UserData": 0,
            "Position": [1, 2, 3],
            "Up": [0, 1, 0],
            "At": [0, 0, 1],
        }
    ]
    input_path.write_text(json.dumps(objects), encoding="utf-8")

    output_path = convert_file(input_path)

    assert output_path == tmp_path / "objects.nmse.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"Base": {"Objects": objects}}


def test_raw_objects_json_must_be_array(tmp_path: Path):
    input_path = tmp_path / "objects.json"
    input_path.write_text(json.dumps({"Objects": []}), encoding="utf-8")

    with pytest.raises(ConversionError, match="top-level JSON array"):
        convert_file(input_path)


def test_metadata_reports_raw_objects_count(tmp_path: Path):
    input_path = tmp_path / "objects.json"
    input_path.write_text(json.dumps([{"ObjectID": "One"}, {"ObjectID": "Two"}]), encoding="utf-8")

    assert member_metadata(input_path) == [
        {"name": "objects.json", "size": input_path.stat().st_size, "items": 2}
    ]


def test_extract_is_zip_only_for_raw_objects_json(tmp_path: Path):
    input_path = tmp_path / "objects.json"
    output_dir = tmp_path / "extract"
    input_path.write_text(json.dumps([{"ObjectID": "Decoration"}]), encoding="utf-8")

    with pytest.raises(ConversionError, match="extract only supports ZIP/.nmsship"):
        extract_members(input_path, output_dir)

    assert not output_dir.exists()
