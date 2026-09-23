"""Zusagen zwischen Stylesheet und Komponenten, die keine Sprache prüft.

Hier steht nur, was über Dateigrenzen hinweg gilt und beim Brechen nicht
auffällt. Ein Typechecker sieht es nicht, ein Test in einer anderen Sprache
gäbe es nicht, und der Screenshot auf dem Entwicklungsrechner sah richtig aus.
"""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web" / "src"
VIEWS = ("BrainView.tsx", "FlyView.tsx")


@pytest.fixture(scope="module")
def styles() -> str:
    return (WEB / "styles.css").read_text(encoding="utf-8")


@pytest.mark.parametrize("view", VIEWS)
def test_a_canvas_gets_its_display_size_from_somewhere(view, styles):
    """`setSize(w, h, false)` heißt „fass den Style nicht an".

    three.js setzt dann nur den Backing Store auf ``w * devicePixelRatio`` und
    überlässt die Anzeigegröße dem Stylesheet. Fehlt dort die Regel, fällt das
    Canvas auf seine intrinsische Größe zurück, und die ist auf einem Gerät mit
    devicePixelRatio 2 doppelt so groß wie das Panel: es läuft über und legt
    sich über die Nachbarfelder.

    Bei devicePixelRatio 1 stimmt es zufällig. Genau deshalb steht dieser Test
    hier: der Fehler ist auf einem gewöhnlichen Schirm unsichtbar und auf einem
    Retina-Schirm zerlegt er die halbe Seite.
    """
    source = (WEB / "components" / view).read_text(encoding="utf-8")
    calls = re.findall(r"renderer\.setSize\(([^)]*)\)", source)
    assert calls, f"{view} ruft setSize nicht auf"

    host = "brain-host" if view == "BrainView.tsx" else "fly-host"
    styled = re.search(
        rf"\.{host} canvas[^{{]*{{[^}}]*width:\s*100%[^}}]*height:\s*100%",
        styles,
    ) or re.search(
        rf"\.{host} canvas,\s*\.[a-z-]+ canvas\s*{{[^}}]*width:\s*100%[^}}]*height:\s*100%",
        styles,
    ) or re.search(
        rf"\.[a-z-]+ canvas,\s*\.{host} canvas\s*{{[^}}]*width:\s*100%[^}}]*height:\s*100%",
        styles,
    )

    for call in calls:
        hands_off_the_style = call.rstrip().endswith("false")
        assert not hands_off_the_style or styled, (
            f"{view} ruft setSize(..., false) und .{host} canvas hat keine "
            "Anzeigegröße im Stylesheet. Entweder das letzte Argument weglassen, "
            "damit three.js den Style selbst setzt, oder die Regel "
            f"`.{host} canvas {{ width: 100%; height: 100% }}` wieder eintragen."
        )
