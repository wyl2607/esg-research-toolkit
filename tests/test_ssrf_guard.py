from __future__ import annotations

import pytest

from report_parser.disclosures_api import _is_private_or_local_hostname


@pytest.mark.parametrize(
    "hostname",
    [
        None,
        "",
        "localhost",
        "127.0.0.1",
        "::1",
        "10.0.0.5",
        "192.168.1.10",
        "172.16.0.1",
        "169.254.169.254",  # cloud metadata endpoint
        "foo.local",
        "bar.internal",
    ],
)
def test_internal_hosts_are_blocked(hostname) -> None:
    assert _is_private_or_local_hostname(hostname) is True


def test_unresolvable_host_fails_closed() -> None:
    # A name that cannot resolve must be treated as unsafe.
    assert _is_private_or_local_hostname("definitely-not-a-real-host.invalid") is True
