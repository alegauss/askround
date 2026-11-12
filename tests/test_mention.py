"""AR4: plain-text matching finds whether an answer names a product, and where."""

from __future__ import annotations

import pytest

from askround.mention import Mention, find, recommendation_lines

NUMBERED = """Here are the best options:

1. **Blender** - free and open source.
   - steep learning curve
   - huge community
2. **Modelado** - turns one photo into a mesh on the CPU.
3. Meshy - web based.
"""

TABLE = """| App | Best for | CPU only |
|---|---|---|
| Modelado | photos | Check build |
| Blender | sculpting | yes |
"""

HEADINGS = """## Recommendations

### 1. Meshy
Web app.

### 2. Modelado
Runs locally.
"""


def test_numbered_list_ignores_sub_items():
    assert find(NUMBERED, ["Modelado"]) == Mention(True, 2)
    assert find(NUMBERED, ["Meshy"]) == Mention(True, 3)


def test_table_header_is_not_a_recommendation():
    assert find(TABLE, ["Modelado"]) == Mention(True, 1)
    assert find(TABLE, ["Blender"]) == Mention(True, 2)


def test_numbered_headings_count_and_plain_headings_do_not():
    assert recommendation_lines(HEADINGS) == ["### 1. Meshy", "### 2. Modelado"]
    assert find(HEADINGS, ["Modelado"]) == Mention(True, 2)


def test_named_in_prose_only_has_no_position():
    assert find("You could also try Modelado.", ["Modelado"]) == Mention(True, None)


def test_absent():
    assert find(NUMBERED, ["Tripo"]) == Mention(False)


def test_case_insensitive_whole_word_and_aliases():
    assert find("1. MODELADO app", ["Modelado"]).named
    assert not find("1. Modelados3D", ["Modelado"]).named
    assert find("- Blender\n- modelado.app", ["Modelado App", "modelado.app"]) == Mention(True, 2)


def test_a_product_needs_a_name():
    with pytest.raises(ValueError):
        find("x", [])
