
import csv
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data/nasa_power")

FILES = [
    "ballari_2025-01.csv",
    "shivamogga_2025-01.csv",
    "vijayapura_2025-01.csv",
    "belagavi_2025-01.csv",
    "dharwad_2025-01.csv",
]

REQUIRED_COLUMNS = [
    "location",
    "latitude",
    "longitude",
    "date",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
]

NUMERIC_COLUMNS = REQUIRED_COLUMNS[1:3] + REQUIRED_COLUMNS[4:]

def validate_file(filename):
    path = DATA_DIR / filename
    errors = []

    if not path.exists():
        return [f"File not found: {path}"]

    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not set(REQUIRED_COLUMNS).issubset(reader.fieldnames or []):
            return ["Required columns are missing."]

        rows = list(reader)

    if len(rows) != 31:
        errors.append(f"Expected 31 records, found {len(rows)}.")

    dates = []

    for row_number, row in enumerate(rows, start=2):
        try:
            dates.append(
                datetime.strptime(row["date"], "%Y%m%d").date()
            )
        except ValueError:
            errors.append(f"Invalid date at CSV row {row_number}.")

        for column in NUMERIC_COLUMNS:
            try:
                value = float(row[column])
                if value == -999:
                    errors.append(
                        f"Missing-data marker in {column}, row {row_number}."
                    )
            except (ValueError, TypeError):
                errors.append(
                    f"Invalid or missing {column}, row {row_number}."
                )

        try:
            if float(row["RH2M"]) < 0 or float(row["RH2M"]) > 100:
                errors.append(f"RH2M outside 0-100 at row {row_number}.")
        except (ValueError, TypeError):
            pass

    expected_dates = {
        datetime.strptime(f"2025-01-{day:02d}", "%Y-%m-%d").date()
        for day in range(1, 32)
    }

    if set(dates) != expected_dates:
        errors.append("Dates do not exactly cover January 1-31, 2025.")

    return errors


if __name__ == "__main__":
    total_errors = 0

    for filename in FILES:
        errors = validate_file(filename)

        print(f"\n{filename}")

        if errors:
            print("FAILED")
            for error in errors:
                print(" -", error)
            total_errors += len(errors)
        else:
            print("PASSED - 31 records validated.")

    print("\nTotal validation errors:", total_errors)
