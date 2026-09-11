#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
Render the changelog of the manual into the fragment the App Center shows.

``doc/docs/changelog.rst`` is the only place the changelog is written. The App
Center wants HTML, so ``appcenter/README_UPDATE_EN.jinja`` extends the
``changelog.html`` this script produces, and the two can never drift apart.

Sphinx rather than plain docutils, so the roles used in the changelog render
exactly as they do in the published manual.
"""

import subprocess
import tempfile
from pathlib import Path

from lxml import html

REPO_ROOT = Path(__file__).resolve().parent
CHANGELOG_RST = REPO_ROOT / "doc" / "docs" / "changelog.rst"
CHANGELOG_HTML = REPO_ROOT / "changelog.html"

# A throwaway Sphinx project with none of the manual's theme, intersphinx or
# bibtex configuration. It is fast, needs no network, and therefore runs
# unchanged in CI. The changelog carries no cross-reference into the rest of
# the manual, so it builds on its own.
CONF_PY = """\
project = "Apple School Manager Connector"
extensions = []
html_theme = "basic"
exclude_patterns = ["_build"]
"""

INDEX_RST = """\
:orphan:

.. toctree::

   changelog
"""


def _build_sphinx(srcdir: Path, outdir: Path) -> None:
    (srcdir / "conf.py").write_text(CONF_PY)
    (srcdir / "index.rst").write_text(INDEX_RST)
    (srcdir / "changelog.rst").write_text(CHANGELOG_RST.read_text())
    subprocess.run(
        ["sphinx-build", "--builder", "html", str(srcdir), str(outdir)],
        check=True,
    )


def _extract(page: Path, xpath: str) -> str:
    """
    Return the HTML of the element that ``xpath`` matches in a built page.

    Raise if docutils rendered an error node. An unknown role or malformed
    markup surfaces as a ``system-message`` or ``problematic`` node, so this
    fails the build loudly instead of shipping a broken fragment.
    """
    tree = html.fromstring(page.read_text())
    broken = tree.xpath(
        "//*[contains(@class, 'system-message')] | //*[contains(@class, 'problematic')]",
    )
    if broken:
        msg = f"{page.name} contains {len(broken)} docutils error node(s)"
        raise ValueError(msg)
    matches = tree.xpath(xpath)
    if not matches:
        msg = f"no element matched {xpath!r} in {page.name}"
        raise ValueError(msg)
    fragment: str = html.tostring(matches[0], encoding="unicode", pretty_print=True)
    return fragment


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        srcdir = Path(tmp) / "src"
        outdir = Path(tmp) / "out"
        srcdir.mkdir()
        _build_sphinx(srcdir, outdir)
        changelog = _extract(outdir / "changelog.html", "//*[@id='changelog']")
    CHANGELOG_HTML.write_text(f"<div>\n{changelog}\n</div>")


if __name__ == "__main__":
    main()
