from __future__ import annotations

import socket

import pytest

from report_parser import disclosures_api as disclosures


class _FakeResponse:
    def __init__(self, *, status_code: int, url: str, headers: dict[str, str], chunks: list[bytes]):
        self.status_code = status_code
        self.url = url
        self.headers = headers
        self._chunks = chunks

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def iter_bytes(self):
        return iter(self._chunks)


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.calls: list[tuple[str, dict[str, object]]] = []

    def stream(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        assert method == "GET"
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _public_dns(hostname: str, port: int, *_args: object, **_kwargs: object):
    assert hostname in {"public.example", "public-two.example"}
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", port),
        )
    ]


def test_ipv4_mapped_ipv6_is_private() -> None:
    assert disclosures._is_private_or_local_hostname("::ffff:127.0.0.1") is True
    assert disclosures._is_private_or_local_hostname("::ffff:169.254.169.254") is True


def test_dns_rebinding_to_mapped_private_address_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        disclosures.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::ffff:10.0.0.8", 443, 0, 0),
            )
        ],
    )

    with pytest.raises(disclosures._FetchPolicyError):
        disclosures._validate_fetch_url("https://rebound.example/report.pdf")


def test_every_redirect_hop_is_validated_before_request(monkeypatch) -> None:
    monkeypatch.setattr(disclosures.socket, "getaddrinfo", _public_dns)
    client = _FakeClient(
        [
            _FakeResponse(
                status_code=302,
                url="https://public.example/start",
                headers={"location": "https://public-two.example/next"},
                chunks=[],
            ),
            _FakeResponse(
                status_code=302,
                url="https://public-two.example/next",
                headers={"location": "https://127.0.0.1/private.pdf"},
                chunks=[],
            ),
        ]
    )

    result = disclosures._fetch_with_safe_redirects(client, "https://public.example/start")

    assert result is None
    assert [url for url, _ in client.calls] == [
        "https://public.example/start",
        "https://public-two.example/next",
    ]


def test_http_and_nonstandard_ports_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(disclosures.socket, "getaddrinfo", _public_dns)
    monkeypatch.delenv("ESG_LOCAL_FETCH_TEST_MODE", raising=False)

    with pytest.raises(disclosures._FetchPolicyError):
        disclosures._validate_fetch_url("http://public.example/report.pdf")
    with pytest.raises(disclosures._FetchPolicyError):
        disclosures._validate_fetch_url("https://public.example:8443/report.pdf")


def test_response_body_is_bounded_while_streaming(monkeypatch) -> None:
    monkeypatch.setattr(disclosures.socket, "getaddrinfo", _public_dns)
    client = _FakeClient(
        [
            _FakeResponse(
                status_code=200,
                url="https://public.example/report.pdf",
                headers={"content-type": "application/pdf"},
                chunks=[b"x" * (disclosures.MAX_RESPONSE_BYTES + 1)],
            )
        ]
    )

    result = disclosures._download_pdf_bytes(client, "https://public.example/report.pdf")

    assert result is None
