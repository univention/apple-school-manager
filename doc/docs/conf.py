# SPDX-FileCopyrightText: 2026 Univention GmbH
#
# SPDX-License-Identifier: AGPL-3.0-only

"""Configuration file for the Sphinx documentation builder."""

import re
import sys
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.config import Config


def _app_version() -> str:
    """Read the app version from the topmost Debian changelog entry."""
    changelog = Path(__file__).parent.parent.parent / "apple-school-manager" / "debian" / "changelog"
    match = re.match(r"^\S+ \(([^)]+)\)", changelog.read_text(encoding="utf-8"))
    return match.group(1) if match else "0.0.0"


# -- Project information -----------------------------------------------------

project = "Apple School Manager Connector"
copyright = "2026, Univention GmbH"  # noqa: A001
author = "Univention GmbH"
version = _app_version()
release = version

doc_basename = "apple-school-manager-connector"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_last_updated_by_git",
    "sphinx_sitemap",
    "sphinxcontrib.bibtex",
    "sphinxcontrib.spelling",
    "univention_sphinx_extension",
    "sphinxext.rediraffe",
]

rediraffe_branch = "5.2"
rediraffe_redirects = "redirects.txt"

# 'sphinx_last_updated_by_git' dates each page from the git history. CI clones
# shallowly, so a page whose last change predates the clone gets no date and the
# extension warns about it.
suppress_warnings = ["git.too_shallow"]

# Section titles repeat the explicit chapter labels this documentation sets,
# for example '.. _changelog:' above a chapter called 'Changelog'. Prefixing
# the generated labels with the document name keeps the two apart.
autosectionlabel_prefix_document = True

intersphinx_mapping = {
    "uv-ucs-operation": ("https://docs.software-univention.de/ucs-operation/5.2/en/", None),
    "uv-ucsschool-manual": ("https://docs.software-univention.de/ucsschool-manual/5.2/de/", None),
    "uv-ucsschool-import": ("https://docs.software-univention.de/ucsschool-import/5.2/de/", None),
    "uv-keycloak-app": ("https://docs.software-univention.de/keycloak-app/latest/", None),
}

bibtex_bibfiles = ["bibliography.bib"]
bibtex_encoding = "utf-8"
bibtex_default_style = "unsrt"
bibtex_reference_style = "label"

templates_path = ["_templates"]
source_suffix = ".rst"
rst_epilog = """
.. include:: /substitutions.txt
"""
root_doc = "contents"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"
numfig = True

copybutton_prompt_text = r"\$ "
copybutton_prompt_is_regexp = True
copybutton_line_continuation_character = "\\"

# -- Options for HTML output -------------------------------------------------

html_theme = "univention_sphinx_book_theme"
html_show_copyright = False
html_show_sphinx = False
html_show_sourcelink = False
html_use_index = False

html_theme_options = {
    "pdf_download_filename": f"{doc_basename}.pdf",
    "show_source_license": True,
    "typesense_search": True,
    "typesense_document": doc_basename,
    "typesense_document_version": "latest",
    "univention_matomo_tracking": True,
    "univention_docs_deployment": True,
}

htmlhelp_basename = "AppleSchoolManagerConnectordoc"

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    "papersize": "a4paper",
    "babel": "\\usepackage{babel}",
}
latex_engine = "lualatex"
latex_documents = [
    (
        root_doc,
        f"{doc_basename}.tex",
        "Apple School Manager Connector Documentation",
        "Univention GmbH",
        "manual",
        False,
    ),
]

man_pages = [
    (root_doc, doc_basename, "Apple School Manager Connector Documentation", [author], 1),
]

texinfo_documents = [
    (
        root_doc,
        doc_basename,
        "Apple School Manager Connector Documentation",
        author,
        doc_basename,
        "Provision UCS@school users to Apple School Manager.",
        "Miscellaneous",
    ),
]

# -- Options for the spell checker -------------------------------------------

if "spelling" in sys.argv:
    spelling_lang = "en_US"
    spelling_show_suggestions = True
    spelling_word_list_filename = ["spelling_wordlist"]
    spelling_exclude_patterns = ["bibliography.rst"]

# -- Options for the link checker --------------------------------------------

linkcheck_allowed_redirects = {
    r"https://help\.univention\.com/t/\d+": r"https://help\.univention\.com/t/[\w-]+/\d+",
    r"https://support\.apple\.com/en-us/\w+": r"https://support\.apple\.com/\S+",
}

# Sitemap, see https://github.com/jdillard/sphinx-sitemap
univention_use_doc_base = True
univention_project_basename = doc_basename
univention_release_language_scheme = "{language}"

# See Univention Sphinx Extension for its options.
# https://git.knut.univention.de/univention/documentation/univention_sphinx_extension
univention_feedback = True
univention_pdf_show_source_license = True
univention_doc_basename = doc_basename


def adapt_settings_to_translation(_app: Sphinx, config: Config) -> None:
    """Adapt the document title and the spell check to the German build."""
    if config.language == "de":
        config.spelling_word_list_filename = [
            *config.spelling_word_list_filename,
            "spelling_wordlist_de",
        ]
        config.latex_documents = [
            (
                root_doc,
                f"{doc_basename}.tex",
                "Apple School Manager Connector Dokumentation",
                "Univention GmbH",
                "manual",
                False,
            ),
        ]
        config.bibtex_bibfiles = ["bibliography-de.bib"]
        config.intersphinx_mapping = {
            "uv-ucs-operation": ("https://docs.software-univention.de/ucs-operation/5.2/de/", None),
            "uv-ucsschool-manual": (
                "https://docs.software-univention.de/ucsschool-manual/5.2/de/",
                None,
            ),
            "uv-ucsschool-import": (
                "https://docs.software-univention.de/ucsschool-import/5.2/de/",
                None,
            ),
            "uv-keycloak-app": ("https://docs.software-univention.de/keycloak-app/latest/", None),
        }
        config.numfig_format["code-block"] = "Listing %s"
        config.numfig_format["table"] = "Tabelle %s"


def setup(app: Sphinx) -> None:
    app.connect("config-inited", adapt_settings_to_translation)
