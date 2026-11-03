import uuid
from datetime import UTC, datetime

import httpx

from app import schemas
from app.config import get_settings
from app.providers import check_providers, provider_status
from app.reports import generate_pdf


def test_no_provider_network_without_configuration(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "virustotal_api_key", "")
    monkeypatch.setattr(settings, "google_webrisk_api_key", "")
    monkeypatch.setattr(settings, "rdap_enabled", False)

    def unexpected(*args, **kwargs):
        raise AssertionError("Unconfigured providers must not access the network")

    monkeypatch.setattr(httpx, "Client", unexpected)
    statuses, findings = check_providers("https://example.com/", "example.com")
    assert findings == []
    assert [status["status"] for status in statuses] == [
        "not_configured", "not_configured", "disabled",
    ]
    assert provider_status()["rdap"] == "disabled"


def test_fixed_hosts_timeout_failures_and_no_secret_leak(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "virustotal_api_key", "very-secret-vt-key")
    monkeypatch.setattr(settings, "google_webrisk_api_key", "very-secret-google-key")
    monkeypatch.setattr(settings, "rdap_enabled", True)
    original_client = httpx.Client
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        if request.url.host in {"rdap.org", "rdap.verisign.com"}:
            return httpx.Response(302, headers={"location": "https://attacker.example/private"})
        return httpx.Response(429)

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["trust_env"] is False
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "Client", client)
    statuses, findings = check_providers("https://untrusted.example/path", "untrusted.example")
    assert set(hosts) == {"www.virustotal.com", "webrisk.googleapis.com", "rdap.org"}
    assert all(status["status"] == "unavailable" for status in statuses)
    assert "very-secret" not in str(statuses)
    assert findings == []


def test_provider_evidence_is_allowlisted(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "virustotal_api_key", "test")
    monkeypatch.setattr(settings, "google_webrisk_api_key", "test")
    monkeypatch.setattr(settings, "rdap_enabled", True)
    original_client = httpx.Client

    def handler(request):
        if request.url.host == "www.virustotal.com":
            return httpx.Response(200, json={
                "data": {"attributes": {
                    "last_analysis_stats": {"malicious": 2, "suspicious": 1, "secret": "drop"},
                    "private": "do not persist",
                }},
            })
        if request.url.host == "webrisk.googleapis.com":
            return httpx.Response(200, json={
                "threat": {"threatTypes": ["MALWARE", "PRIVATE_DATA"]},
            })
        return httpx.Response(200, json={
            "events": [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}],
            "entities": [{"email": "sensitive@example.com"}],
        })

    monkeypatch.setattr(
        httpx, "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    statuses, findings = check_providers("https://example.com/", "example.com")
    assert all(status["status"] == "available" for status in statuses)
    assert len(findings) == 2
    assert statuses[0]["details"]["malicious"] == 2
    assert "PRIVATE_DATA" not in str(statuses)
    assert "sensitive" not in str(statuses)


def test_report_escapes_text_and_does_not_invent_predictions():
    now = datetime.now(UTC)
    investigation = schemas.InvestigationDetail(
        id=uuid.uuid4(), created_at=now, updated_at=now, investigation_type="upload",
        title='<a href="file:///private">Injected & malformed <b>',
        status="pending", risk_level=None, resource_id=None,
    )
    content = generate_pdf(investigation)
    assert content.startswith(b"%PDF-")
    assert len(content) > 1000
