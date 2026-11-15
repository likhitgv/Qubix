"""Load and validate KAIRO crop-reference records.

The CSV is deliberately initialized with a schema only.  Crop records must be
added from traceable sources before this module is used for recommendations.
All public return values are plain Python dictionaries/lists so they can be
passed to a Streamlit dashboard or combined later with Member 2's analysis
object without a pandas dependency.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "1.0"

REQUIRED_COLUMNS = (
    "crop_id",
    "crop_name",
    "crop_family",
    "suitable_seasons",
    "soil_types",
    "min_temperature_c",
    "max_temperature_c",
    "min_rainfall_mm",
    "max_rainfall_mm",
    "water_requirement",
    "legume",
    "rotation_notes",
    "source_name",
    "source_urls",
    "source_accessed_date",
    "source_notes",
)

LIST_FIELDS = ("suitable_seasons", "soil_types")
NUMERIC_FIELDS = (
    "min_temperature_c",
    "max_temperature_c",
    "min_rainfall_mm",
    "max_rainfall_mm",
)


class CropDatabaseValidationError(ValueError):
    """Raised when the crop-reference CSV does not meet the data contract."""


def default_database_path() -> Path:
    """Return the repository-local crop database path without using a CWD."""

    return Path(__file__).resolve().parents[1] / "data" / "crop_database.csv"


def validate_crop_database(csv_path: str | Path | None = None) -> dict[str, Any]:
    """Validate a crop database and return a compact, dashboard-safe report.

    A header-only CSV is valid during setup.  Once a crop record is added, all
    required fields, units, and provenance fields are required.
    """

    path, fieldnames, rows = _read_rows(csv_path)
    _validate_columns(fieldnames, path)

    _validate_records(rows)

    return {
        "valid": True,
        "schema_version": SCHEMA_VERSION,
        "path": str(path),
        "record_count": len(rows),
        "columns": list(REQUIRED_COLUMNS),
    }


def load_crop_database(csv_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load validated crop records as JSON-friendly dictionaries.

    ``suitable_seasons`` and ``soil_types`` use pipe-separated values in the
    CSV and are returned as lists. Temperatures are in degrees Celsius and
    rainfall values are in millimetres, as named by their columns.
    """

    path, fieldnames, rows = _read_rows(csv_path)
    _validate_columns(fieldnames, path)

    _validate_records(rows)
    records: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        record = dict(row)
        for field in LIST_FIELDS:
            record[field] = [item.strip() for item in row[field].split("|") if item.strip()]
        for field in NUMERIC_FIELDS:
            record[field] = float(row[field])
        record["legume"] = row["legume"].strip().lower() == "true"
        records.append(record)

    return records


def crop_database_handoff(csv_path: str | Path | None = None) -> dict[str, Any]:
    """Return the Member 3 data handoff shape for Member 4's dashboard.

    Member 2 climate-analysis fields are intentionally not required here:
    Member 3's later suitability module will combine those environmental summaries
    with these source-backed reference records later.
    """

    report = validate_crop_database(csv_path)
    records = load_crop_database(csv_path)
    return {
        "records": records,
        "metadata": {
            **report,
            "units": {"temperature": "celsius", "rainfall": "mm"},
            "limitations": [
                "This module validates reference-data structure; it does not validate agronomic suitability.",
                "The starter database contains no crop records until traceable sources are entered.",
            ],
        },
    }


def _read_rows(
    csv_path: str | Path | None,
) -> tuple[Path, list[str] | None, list[dict[str, str]]]:
    path = Path(csv_path) if csv_path is not None else default_database_path()
    if not path.is_file():
        raise CropDatabaseValidationError(f"Crop database not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return path, reader.fieldnames, list(reader)


def _validate_columns(fieldnames: list[str] | None, path: Path) -> None:
    columns = tuple(fieldnames or ())
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    unexpected = [column for column in columns if column not in REQUIRED_COLUMNS]
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected columns: {', '.join(unexpected)}")
        raise CropDatabaseValidationError(f"Invalid crop database schema in {path}: {'; '.join(details)}")


def _validate_record(row: dict[str, str], row_number: int) -> None:
    empty_fields = [field for field in REQUIRED_COLUMNS if not (row.get(field) or "").strip()]
    if empty_fields:
        raise CropDatabaseValidationError(
            f"Row {row_number} has empty required fields: {', '.join(empty_fields)}"
        )

    for field in LIST_FIELDS:
        if not [value for value in row[field].split("|") if value.strip()]:
            raise CropDatabaseValidationError(f"Row {row_number} has no values in {field}")

    values = _numeric_values(row, row_number)
    if values["min_temperature_c"] > values["max_temperature_c"]:
        raise CropDatabaseValidationError(f"Row {row_number} has min_temperature_c above max_temperature_c")
    if values["min_rainfall_mm"] > values["max_rainfall_mm"]:
        raise CropDatabaseValidationError(f"Row {row_number} has min_rainfall_mm above max_rainfall_mm")
    if values["min_rainfall_mm"] < 0 or values["max_rainfall_mm"] < 0:
        raise CropDatabaseValidationError(f"Row {row_number} has negative rainfall")

    if row["legume"].strip().lower() not in {"true", "false"}:
        raise CropDatabaseValidationError(f"Row {row_number} legume must be true or false")

    source_urls = [url.strip() for url in row["source_urls"].split("|") if url.strip()]
    if not source_urls:
        raise CropDatabaseValidationError(f"Row {row_number} requires at least one source URL")
    for source_url in source_urls:
        parsed_source = urlparse(source_url)
        if parsed_source.scheme not in {"http", "https"} or not parsed_source.netloc:
            raise CropDatabaseValidationError(
                f"Row {row_number} source_urls must contain only http(s) URLs"
            )

    try:
        date.fromisoformat(row["source_accessed_date"].strip())
    except ValueError as error:
        raise CropDatabaseValidationError(
            f"Row {row_number} source_accessed_date must use YYYY-MM-DD"
        ) from error


def _validate_records(rows: list[dict[str, str]]) -> None:
    crop_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        _validate_record(row, row_number)
        crop_id = row["crop_id"].strip()
        if crop_id in crop_ids:
            raise CropDatabaseValidationError(f"Row {row_number} repeats crop_id: {crop_id}")
        crop_ids.add(crop_id)


def _numeric_values(row: dict[str, str], row_number: int) -> dict[str, float]:
    values: dict[str, float] = {}
    for field in NUMERIC_FIELDS:
        try:
            values[field] = float(row[field])
        except ValueError as error:
            raise CropDatabaseValidationError(
                f"Row {row_number} {field} must be numeric"
            ) from error
    return values
