import asyncio
import csv
import io

import pytest
from app.config import get_settings
from app.uploads import REQUIRED_COLUMNS, parse_upload, validate_row
from fastapi import HTTPException, UploadFile


def csv_data(rows=None, headers=None):
    headers = headers or REQUIRED_COLUMNS
    rows = rows if rows is not None else [[0] * len(headers)]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode()


def parse(data, name="transactions.csv"):
    return asyncio.run(parse_upload(UploadFile(filename=name, file=io.BytesIO(data))))


def test_upload_keeps_only_required_fields_and_safe_filename():
    headers = [*REQUIRED_COLUMNS, "Class", "customer_email", "merchant_url"]
    row = [*([0] * 30), 1, "private@example.com", "https://example.com"]
    filename, columns, rows = parse(csv_data([row], headers), "../../data.csv")
    assert filename == "data.csv"
    assert "customer_email" not in columns
    assert "customer_email" not in rows[0]
    assert "Class" not in rows[0]
    assert rows[0]["merchant_url"] == "https://example.com/"
    assert len(rows[0]) == 31


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"Amount\n1\n",
        b"\xff",
        b"\x00",
        csv_data([], REQUIRED_COLUMNS),
        csv_data([[0] * 29]),
        csv_data([[0] * 31]),
        csv_data([[0] * 31], [*REQUIRED_COLUMNS, "Amount"]),
        csv_data([[0] * 65], [*REQUIRED_COLUMNS, *[f"extra{i}" for i in range(35)]]),
        csv_data([["NaN", *([0] * 29)]]),
        csv_data([["inf", *([0] * 29)]]),
        csv_data([[-1, *([0] * 29)]]),
        csv_data([[*([0] * 29), -1]]),
        csv_data([[*([0] * 30), "http://127.0.0.1"]], [*REQUIRED_COLUMNS, "merchant_url"]),
        b"Time,V1\n\"unterminated",
    ],
)
def test_invalid_csv(data):
    with pytest.raises(HTTPException) as error:
        parse(data)
    assert error.value.status_code == 422


def test_upload_limits(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_bytes", 16)
    with pytest.raises(HTTPException) as error:
        parse(csv_data())
    assert error.value.status_code == 413
    monkeypatch.setattr(settings, "max_upload_bytes", 10 * 1024 * 1024)
    monkeypatch.setattr(settings, "max_upload_rows", 1)
    with pytest.raises(HTTPException) as error:
        parse(csv_data([[0] * 30, [0] * 30]))
    assert error.value.status_code == 422


def test_numeric_and_bool_validation():
    row = {name: 0 for name in REQUIRED_COLUMNS}
    row["V2"] = True
    with pytest.raises(ValueError, match="finite number"):
        validate_row(row)


def test_filename_and_csv_encoding():
    with pytest.raises(HTTPException):
        parse(csv_data(), "data.exe")
    assert len(parse(b"\xef\xbb\xbf" + csv_data())[2]) == 1
