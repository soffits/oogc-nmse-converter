"""Convert OOGC / NMS Model IO exports to NMSE wrapper JSON."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


class ConversionError(ValueError):
    """Raised when an input file cannot be converted."""


@dataclass(frozen=True)
class ConversionResult:
    """Information about a completed conversion."""

    input_path: Path
    output_path: Path
    wrapper: dict[str, Any]


ZIP_MAGIC_PREFIXES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
KNOWN_MEMBERS = ("so.json", "ccd.json", "objects.json")
OutputFormat = Literal["json", "nmscorv"]


def default_output_path(input_path: Path, output_format: OutputFormat = "json") -> Path:
    """Return the default NMSE wrapper output path for an input file."""

    suffix = ".nmscorv" if output_format == "nmscorv" else ".nmse.json"
    return input_path.with_suffix(suffix)


def read_nmsship(path: Path, *, include_default_ccd: bool = True) -> dict[str, Any]:
    """Read a .nmsship/ZIP file and return an NMSE import wrapper object."""

    path = Path(path)
    _validate_zip_magic(path)

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "so.json" not in names:
                raise ConversionError(f"{path} is missing required member so.json")

            ship = _read_json_member(archive, "so.json")
            wrapper: dict[str, Any] = {"Ship": ship}

            if "ccd.json" in names:
                ccd = _read_json_member(archive, "ccd.json")
                if include_default_ccd or not is_default_ccd(ccd):
                    wrapper["CharacterCustomisationData"] = ccd

            if "objects.json" in names:
                objects = _read_json_member(archive, "objects.json")
                if not isinstance(objects, list):
                    raise ConversionError("objects.json must contain a JSON array")
                wrapper["Base"] = {"Objects": objects}

            return wrapper
    except zipfile.BadZipFile as exc:
        raise ConversionError(f"{path} is not a valid ZIP file") from exc


def read_raw_objects(path: Path) -> dict[str, Any]:
    """Read a raw objects JSON array and return an NMSE import wrapper object."""

    objects = _read_json_file(Path(path))
    if not isinstance(objects, list):
        raise ConversionError(f"{path} must contain a top-level JSON array")
    return {"Base": {"Objects": objects}}


def read_wrapper(path: Path, *, include_default_ccd: bool = True) -> dict[str, Any]:
    """Read supported input data and return an NMSE import wrapper object."""

    path = Path(path)
    if _has_zip_magic(path):
        return read_nmsship(path, include_default_ccd=include_default_ccd)
    return read_raw_objects(path)


def convert_file(
    input_path: Path,
    output_path: Path | None = None,
    *,
    output_format: OutputFormat = "json",
    pretty: bool = True,
    include_default_ccd: bool = True,
) -> Path:
    """Convert a supported input file to an NMSE wrapper JSON file."""

    input_path = Path(input_path)
    output_path = (
        Path(output_path) if output_path is not None else default_output_path(input_path, output_format)
    )
    wrapper = read_wrapper(input_path, include_default_ccd=include_default_ccd)

    with output_path.open("w", encoding="utf-8") as handle:
        if pretty:
            json.dump(wrapper, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        else:
            json.dump(wrapper, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")

    return output_path


def extract_members(input_path: Path, output_dir: Path, *, force: bool = False) -> list[Path]:
    """Extract known NMSSHIP JSON members for debugging."""

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    if not _has_zip_magic(input_path):
        raise ConversionError("extract only supports ZIP/.nmsship input files")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(input_path) as archive:
            extracted: list[Path] = []
            names = set(archive.namelist())
            for member in KNOWN_MEMBERS:
                if member not in names:
                    continue
                destination = output_dir / member
                if destination.exists() and not force:
                    raise ConversionError(f"refusing to overwrite existing file: {destination}")
                destination.write_bytes(archive.read(member))
                extracted.append(destination)
            return extracted
    except zipfile.BadZipFile as exc:
        raise ConversionError(f"{input_path} is not a valid ZIP file") from exc


def member_metadata(input_path: Path) -> list[dict[str, Any]]:
    """Return basic member metadata and top-level JSON key information."""

    input_path = Path(input_path)
    if not _has_zip_magic(input_path):
        objects = _read_json_file(input_path)
        if not isinstance(objects, list):
            raise ConversionError(f"{input_path} must contain a top-level JSON array")
        return [{"name": input_path.name, "size": input_path.stat().st_size, "items": len(objects)}]

    try:
        with zipfile.ZipFile(input_path) as archive:
            rows: list[dict[str, Any]] = []
            for info in archive.infolist():
                row: dict[str, Any] = {"name": info.filename, "size": info.file_size}
                if info.filename in KNOWN_MEMBERS:
                    data = _read_json_member(archive, info.filename)
                    if isinstance(data, dict):
                        row["keys"] = sorted(str(key) for key in data.keys())
                    elif isinstance(data, list):
                        row["items"] = len(data)
                rows.append(row)
            return rows
    except zipfile.BadZipFile as exc:
        raise ConversionError(f"{input_path} is not a valid ZIP file") from exc


def is_default_ccd(ccd: Any) -> bool:
    """Return True if CharacterCustomisationData appears blank/default."""

    if not isinstance(ccd, dict):
        return False

    selected_preset = ccd.get("SelectedPreset", "")
    if selected_preset not in ("", "^"):
        return False

    custom_data = ccd.get("CustomData", {})
    if custom_data in (None, ""):
        custom_data = {}
    if not isinstance(custom_data, dict):
        return False

    if custom_data.get("PaletteID", "") not in ("", "^"):
        return False

    for key in ("DescriptorGroups", "Colours", "TextureOptions", "BoneScales"):
        if custom_data.get(key) not in (None, [], {}, ""):
            return False

    allowed_top_level = {"SelectedPreset", "CustomData"}
    if any(_has_value(value) for key, value in ccd.items() if key not in allowed_top_level):
        return False

    allowed_custom_data = {
        "PaletteID",
        "DescriptorGroups",
        "Colours",
        "TextureOptions",
        "BoneScales",
    }
    return not any(
        _has_value(value) for key, value in custom_data.items() if key not in allowed_custom_data
    )


def _read_json_member(archive: zipfile.ZipFile, member: str) -> Any:
    try:
        with archive.open(member) as handle:
            return json.load(handle)
    except KeyError as exc:
        raise ConversionError(f"missing ZIP member: {member}") from exc
    except json.JSONDecodeError as exc:
        raise ConversionError(f"{member} is not valid JSON: {exc.msg}") from exc


def _read_json_file(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise ConversionError(f"cannot read input file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConversionError(f"{path} is not valid JSON: {exc.msg}") from exc


def _has_zip_magic(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            magic = handle.read(4)
    except OSError as exc:
        raise ConversionError(f"cannot read input file {path}: {exc}") from exc

    return magic in ZIP_MAGIC_PREFIXES


def _validate_zip_magic(path: Path) -> None:
    if not _has_zip_magic(path):
        raise ConversionError(f"{path} does not look like a ZIP/.nmsship file")


def _has_value(value: Any) -> bool:
    return value not in (None, "", [], {})
