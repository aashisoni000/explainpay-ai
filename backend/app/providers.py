import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings


def provider_status() -> dict[str, str]:
    settings = get_settings()
    return {
        "virustotal": "configured" if settings.virustotal_api_key else "not_configured",
        "google_webrisk": "configured" if settings.google_webrisk_api_key else "not_configured",
        "rdap": "configured" if settings.rdap_enabled else "disabled",
    }


def _result(name: str, status: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": status, "details": details}


def _finding(
    source: str, finding_type: str, severity: str, description: str, evidence: dict[str, Any]
) -> dict[str, Any]:
    return {
        "source": source,
        "finding_type": finding_type,
        "severity": severity,
        "description": description,
        "evidence": evidence,
    }


def _check(name: str, url: str, domain: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    settings = get_settings()
    status = provider_status()[name]
    if status != "configured":
        return _result(name, status), []
    try:
        # All network destinations are constants; redirects and environment proxies are disabled.
        with httpx.Client(
            timeout=httpx.Timeout(settings.provider_timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            if name == "virustotal":
                url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
                response = client.get(
                    f"https://www.virustotal.com/api/v3/urls/{url_id}",
                    headers={"x-apikey": settings.virustotal_api_key},
                )
                if response.status_code == 404:
                    return _result(name, "no_data", message="URL is not present in the provider"), []
                response.raise_for_status()
                stats = response.json().get("data", {}).get("attributes", {}).get(
                    "last_analysis_stats", {}
                )
                counts = {
                    key: max(0, int(stats.get(key, 0)))
                    for key in ("malicious", "suspicious", "harmless", "undetected")
                }
                findings = []
                if counts["malicious"] or counts["suspicious"]:
                    findings.append(
                        _finding(
                            name,
                            "reputation",
                            "high" if counts["malicious"] else "medium",
                            "VirusTotal engines reported malicious or suspicious reputation.",
                            counts,
                        )
                    )
                return _result(name, "available", **counts), findings
            if name == "google_webrisk":
                response = client.get(
                    "https://webrisk.googleapis.com/v1/uris:search",
                    params={
                        "key": settings.google_webrisk_api_key,
                        "uri": url,
                        "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                    },
                )
                response.raise_for_status()
                allowed = {"MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"}
                threats = [
                    item
                    for item in response.json().get("threat", {}).get("threatTypes", [])
                    if item in allowed
                ]
                findings = []
                if threats:
                    findings.append(
                        _finding(
                            name, "threat_list", "high",
                            "Google Web Risk matched a known threat list.", {"threat_types": threats},
                        )
                    )
                return _result(name, "available", threat_types=threats), findings
            suffix = domain.rsplit(".", 1)[-1].lower()
            # Common registry endpoints are fixed, not learned from DNS or RDAP referrals.
            if suffix in {"com", "net"}:
                endpoint = f"https://rdap.verisign.com/{suffix}/v1/domain/"
            else:
                endpoint = "https://rdap.org/domain/"
            response = client.get(endpoint + quote(domain, safe=""))
            if response.status_code == 404:
                return _result(name, "no_data", message="No registration data returned"), []
            if response.is_redirect:
                return _result(
                    name, "unavailable", message="Registry referral not followed by trusted-host policy"
                ), []
            response.raise_for_status()
            payload = response.json()
            # Registration contacts and arbitrary provider text are deliberately not persisted.
            events = [
                {"action": e["eventAction"], "date": e["eventDate"][:64]}
                for e in payload.get("events", [])[:20]
                if isinstance(e, dict)
                and e.get("eventAction") in {"registration", "expiration", "last changed"}
                and isinstance(e.get("eventDate"), str)
            ]
            return _result(name, "available", events=events), []
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        # Do not expose HTTP exception strings: they may contain API keys or submitted URLs.
        return _result(name, "unavailable", message="Provider request failed or returned invalid data"), []


def check_providers(url: str, domain: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    names = ("virustotal", "google_webrisk", "rdap")
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda name: _check(name, url, domain), names))
    return [result[0] for result in results], [
        finding for _, findings in results for finding in findings
    ]
