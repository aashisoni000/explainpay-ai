"""URL-only features shared by training and inference; no website requests."""

import ipaddress
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlsplit, urlunsplit

FEATURE_VERSION = "url-lexical-v1"
SUSPICIOUS_TOKENS = ("login", "verify", "secure", "account", "update", "bank", "wallet", "password")


def normalize_url(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError("URL must contain 1 to 2048 characters.")
    if re.search(r"[\s\\\x00-\x1f\x7f]", value):
        raise ValueError("URL must not contain whitespace, controls, or backslashes.")
    if "://" not in value:
        value = "https://" + value
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise ValueError("Only HTTP and HTTPS URLs with a hostname are supported.")
        if parts.username is not None or parts.password is not None:
            raise ValueError("URLs containing credentials are not allowed.")
        if parts.port not in {None, 80, 443}:
            raise ValueError("Only standard HTTP/HTTPS ports are supported.")
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            labels = host.split(".")
            if (
                len(labels) < 2
                or len(host) > 253
                or not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", labels[-1])
                or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)
                or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid", ".example", ".home", ".onion"))
                or any(re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)", label) for label in labels)
            ):
                raise ValueError("A valid public hostname is required.")
        else:
            if not address.is_global:
                raise ValueError("Private, reserved, and local IP addresses are not allowed.")
            if address.version == 6:
                host = f"[{host}]"
        netloc = host
        if parts.port is not None:
            netloc += f":{parts.port}"
        return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))
    except (UnicodeError, ValueError) as error:
        raise ValueError(f"Invalid website URL: {error}") from error


def extract_features(url: str) -> dict[str, float]:
    normalized = normalize_url(url)
    parts = urlsplit(normalized)
    host = parts.hostname or ""
    try:
        ipaddress.ip_address(host)
        is_ip = 1.0
    except ValueError:
        is_ip = 0.0
    counts = Counter(normalized)
    entropy = -sum((count / len(normalized)) * math.log2(count / len(normalized)) for count in counts.values())
    return {
        "url_length": float(len(normalized)),
        "domain_length": float(len(host)),
        "dot_count": float(normalized.count(".")),
        "subdomain_count": float(max(0, len(host.split(".")) - 2)) if not is_ip else 0.0,
        "hyphen_count": float(normalized.count("-")),
        "digit_count": float(sum(char.isdigit() for char in normalized)),
        "ip_hostname": is_ip,
        "https": float(parts.scheme == "https"),
        "suspicious_tokens": float(sum(token in normalized.lower() for token in SUSPICIOUS_TOKENS)),
        "parameter_count": float(len(parse_qsl(parts.query, keep_blank_values=True))),
        "suspicious_extension": float(parts.path.lower().endswith((".exe", ".zip", ".scr", ".apk", ".js"))),
        "url_entropy": entropy,
        "path_length": float(len(parts.path)),
        "at_count": float(normalized.count("@")),
        "encoded_count": float(normalized.count("%")),
    }
