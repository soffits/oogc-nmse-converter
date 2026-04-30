# oogc-nmse-converter

Convert OOGC / NMS Model IO style `.nmsship` ZIP exports into JSON that can be imported by [vectorcmdr/NMSE](https://github.com/vectorcmdr/NMSE), or apply raw objects JSON arrays onto an NMSE ship template.

This repository was created for converting community-downloaded No Man's Sky ship packages into NMSE's wrapper JSON format.

## What It Does

NMSE's StarshipPanel import accepts a wrapper JSON object shaped like this:

```json
{
  "Ship": {},
  "Base": { "Objects": [] },
  "CharacterCustomisationData": {}
}
```

OOGC / NMS Model IO `.nmsship` files are ZIP files. Modern NMSE versions may already import `.nmsship` files directly, but this tool is useful when you want a plain JSON wrapper or need to inspect the original members for debugging.

The converter maps ZIP members without rewriting their schemas:

- `so.json` becomes `Ship` and is required.
- `ccd.json` becomes `CharacterCustomisationData` when present.
- `objects.json` must be a JSON array and becomes `Base = {"Objects": ...}`.

NMSE requires real `Ship` data for StarshipPanel imports. Raw OOGC/NMS Model IO objects JSON files contain only placement objects, so they cannot be imported as standalone ships. To use raw objects, first export a Corvette or ship from NMSE and pass it as `--template`; the converter keeps the template `Ship`, keeps `CharacterCustomisationData` when present, keeps template `Base` properties when present, and replaces only `Base.Objects`.

## Usage

```sh
oogc-nmse-convert ship.nmsship
oogc-nmse-convert objects.json --template exported-corvette.nmscorv
```

By default this writes `ship.nmse.json` next to the input file. Refusing to overwrite existing files is intentional; use `--force` when replacing output is desired.

Use `--format nmscorv` or `--nmscorv` to write `ship.nmscorv` instead. `.nmscorv` is NMSE's Corvette export extension; the file content is the same wrapper JSON shape, not a different binary format.

```sh
oogc-nmse-convert ship.nmsship -o converted.json
oogc-nmse-convert ship.nmsship --nmscorv
oogc-nmse-convert ship.nmsship --compact --force
oogc-nmse-convert ship.nmsship --omit-default-ccd
oogc-nmse-convert ship.nmsship --extract debug-members --metadata
oogc-nmse-convert objects.json --template exported-corvette.nmscorv
oogc-nmse-convert objects.json --metadata --template exported-corvette.nmscorv
```

`--template PATH` is used for raw objects JSON input. The template may be an NMSE wrapper JSON such as `.nmscorv`, a plain ship JSON object, or a `.nmsship` ZIP export.

`--extract DIR` writes any present `so.json`, `ccd.json`, and `objects.json` ZIP members to `DIR` and still writes the NMSE wrapper JSON. Extraction is only available for `.nmsship`/ZIP input.

`--metadata` prints ZIP member sizes and top-level JSON keys, or the item count for raw objects JSON arrays, to stderr so stdout can still be used to read the output path.

## Safety

Back up your No Man's Sky save files before importing edited or converted data into any save editor. This tool only repackages JSON data from the export and does not validate whether the resulting ship data is safe for a specific save.

## Development

Runtime code uses only the Python standard library. Tests use `pytest`.

```sh
uv run pytest
```

License: AGPL-3.0-only.
