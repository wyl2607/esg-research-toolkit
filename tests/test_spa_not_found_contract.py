from __future__ import annotations

from pathlib import Path


def test_spa_not_found_route_sets_noindex_meta() -> None:
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")

    assert '<Route path="*" element={<NotFound />} />' in app
    assert "robots.name = 'robots'" in app
    assert "robots.content = 'noindex'" in app
