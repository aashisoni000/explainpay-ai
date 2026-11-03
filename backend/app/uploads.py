import csv
import io
import math
from pathlib import PurePosixPath
from typing import Any

from fastapi import HTTPException, UploadFile

from app.config import get_settings

REQUIRED_COLUMNS = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
MAX_COLUMNS = 64


def normalize_merchant_url(value: str | None) -> str | None:
    if not value:
        return None
    from app.ml.urls import normalize_url

    try:
        return normalize_url(value)
    except ValueError as exc:
        raise ValueError("merchant_url must be a valid public HTTP(S) URL") from exc


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in REQUIRED_COLUMNS:
        value = row.get(column)
        if isinstance(value, bool) or value is None:
            raise ValueError(f"{column} must be a finite number")
        try:
            number = float(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"{column} must be a finite number") from exc
        if not math.isfinite(number):
            raise ValueError(f"{column} must be a finite number")
        if column in {"Time", "Amount"} and number < 0:
            raise ValueError(f"{column} must not be negative")
        result[column] = number
    merchant = row.get("merchant_url")
    if merchant is not None and not isinstance(merchant, str):
        raise ValueError("merchant_url must be a string")
    if merchant:
        result["merchant_url"] = normalize_merchant_url(merchant.strip())
    return result


async def parse_upload(file: UploadFile) -> tuple[str, list[str], list[dict[str, Any]]]:
    settings = get_settings()
    filename = PurePosixPath((file.filename or "upload.csv").replace("\\", "/")).name
    filename = "".join(c for c in filename if c.isprintable())[:255]
    if not filename or not filename.lower().endswith(".csv"):
        raise HTTPException(422, "Upload must be a CSV file")
    data = bytearray()
    try:
        while chunk := await file.read(64 * 1024):
            data.extend(chunk)
            if len(data) > settings.max_upload_bytes:
                raise HTTPException(413, "CSV exceeds the configured upload size limit")
    finally:
        await file.close()
    try:
        text = bytes(data).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "CSV must use UTF-8 encoding") from exc
    if "\x00" in text:
        raise HTTPException(422, "CSV must not contain NUL characters")
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        headers = reader.fieldnames or []
        if len(headers) > MAX_COLUMNS:
            raise HTTPException(422, f"CSV cannot contain more than {MAX_COLUMNS} columns")
        if any(not name or len(name) > 128 for name in headers):
            raise HTTPException(422, "CSV column names must contain 1–128 characters")
        if len(set(headers)) != len(headers):
            raise HTTPException(422, "CSV contains duplicate column names")
        missing = [name for name in REQUIRED_COLUMNS if name not in headers]
        if missing:
            raise HTTPException(422, f"CSV is missing required columns: {', '.join(missing)}")
        rows = []
        for line, row in enumerate(reader, start=2):
            if len(rows) >= settings.max_upload_rows:
                raise HTTPException(422, f"CSV exceeds {settings.max_upload_rows} data rows")
            if None in row or any(value is None for value in row.values()):
                raise HTTPException(422, f"CSV row {line} has an inconsistent number of columns")
            try:
                rows.append(validate_row(row))
            except ValueError as exc:
                raise HTTPException(422, f"CSV row {line}: {exc}") from exc
    except csv.Error as exc:
        raise HTTPException(422, "Malformed CSV data") from exc
    if not rows:
        raise HTTPException(422, "CSV must contain at least one data row")
    columns = [name for name in headers if name in REQUIRED_COLUMNS or name == "merchant_url"]
    return filename, columns, rows
