from __future__ import annotations

from pathlib import Path


def test_nginx_spa_contract_separates_routes_assets_and_404s() -> None:
    config = Path("nginx/esg.conf").read_text(encoding="utf-8")

    assert "charset utf-8;" in config
    assert 'location = /index.html {' in config
    assert 'add_header Cache-Control "no-cache, must-revalidate" always;' in config
    assert 'add_header Cache-Control "public, max-age=31536000, immutable" always;' in config
    assert r"location ~* \.(?:css|js|mjs|map|json|png|" in config
    assert "try_files $uri =404;" in config
    assert 'location / {\n        try_files $uri $uri/ =404;\n    }' in config

    for prefix in (
        "upload",
        "disclosures",
        "taxonomy",
        "lcoe",
        "saf",
        "companies",
        "manual",
        "compare",
        "benchmarks",
        "frameworks",
        "regional",
        "coverage",
    ):
        assert prefix in config
