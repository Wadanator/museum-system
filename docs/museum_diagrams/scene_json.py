"""
scene_schema.py
---------------
High-level 'Scene JSON' overview — what the file looks like from the outside.
No deep detail. Output: outputs/scene_schema.svg
"""

import graphviz
from theme import StateAnatomy as A, FONT_FAMILY
from gv_html import font, thin_rule
from render import render_diagram

C1, C2, C3 = A.C_PRIMARY, A.C_SECONDARY, A.C_MUTED
CB, CD      = A.C_BORDER, A.C_DIVIDER
BG, BGH, BGS, BGI = A.BG_STATE, A.BG_HEADER, A.BG_SECTION, A.BG_ITEM
T, SH, BD, DT = A.FS_TITLE, A.FS_SECTION, A.FS_BODY, A.FS_DETAIL


def simple_field(name, type_str, note=""):
    n = f"&nbsp;&nbsp;{font(note, size=DT, color=C3, italic=True)}" if note else ""
    return (
        f'<TR>'
        f'<TD ALIGN="LEFT" BORDER="0" CELLPADDING="3" WIDTH="130">'
        f'{font(name, size=BD, color=C1, bold=True)}'
        f'</TD>'
        f'<TD ALIGN="LEFT" BORDER="0" CELLPADDING="3">'
        f'{font(type_str, size=DT, color=C3, italic=True)}{n}'
        f'</TD>'
        f'</TR>'
    )


def subsection(title, *rows):
    """A shaded inner box (for globalEvents and states)."""
    hdr = (
        f'<TR><TD COLSPAN="2" BGCOLOR="{BGH}" BORDER="0" CELLPADDING="5" ALIGN="LEFT">'
        f'{font(title, size=SH, color=C1, bold=True)}'
        f'</TD></TR>'
        + thin_rule(colspan=2, color=CD)
    )
    body = "".join(rows)
    inner = (
        f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0" BGCOLOR="{BGS}">'
        f'{hdr}{body}'
        f'</TABLE>'
    )
    return (
        f'<TR>'
        f'<TD COLSPAN="2" BORDER="1" CELLPADDING="0" BGCOLOR="{BGS}" COLOR="{CB}">'
        f'{inner}'
        f'</TD>'
        f'</TR>'
    )


def hint_row(text):
    """Italic muted hint line inside a subsection."""
    return (
        f'<TR><TD COLSPAN="2" BORDER="0" CELLPADDING="4" ALIGN="LEFT">'
        f'{font(text, size=DT, color=C3, italic=True)}'
        f'</TD></TR>'
    )


def build_label():
    # ── title ─────────────────────────────────────────────────────────────
    row_title = (
        f'<TR><TD COLSPAN="2" BGCOLOR="{BGH}" BORDER="0" CELLPADDING="9" ALIGN="LEFT">'
        f'{font("Scene", size=T, color=C1, bold=True)}'
        f'&nbsp;&nbsp;{font(".json", size=BD, color=C3, italic=True)}'
        f'</TD></TR>'
        + thin_rule(colspan=2, color=CB)
    )

    # ── top-level scalar fields ────────────────────────────────────────────
    row_fields = (
        simple_field("sceneId",      "string")
      + simple_field("version",      "string")
      + simple_field("description",  "string")
      + simple_field("initialState", "string", note="→ name of the first state")
    )
    # wrap in a plain spacer row
    row_fields_wrap = (
        f'<TR><TD COLSPAN="2" BORDER="0" CELLPADDING="6">'
        f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0">{row_fields}</TABLE>'
        f'</TD></TR>'
        + thin_rule(colspan=2, color=CD)
    )

    # ── globalEvents subsection ────────────────────────────────────────────
    row_global = subsection(
        "globalEvents  [ ]",
        hint_row("Transition[]  —  active in every state"),
        simple_field("type",  "string", note="timeout  |  mqttMessage  |  …"),
        simple_field("goto",  "string", note="state name  or  END"),
    )

    # ── states subsection ─────────────────────────────────────────────────
    row_states = subsection(
        "states  { }",
        hint_row("One entry per state, keyed by state name."),
        simple_field("description",  "string"),
        simple_field("onEnter",      "Action[]"),
        simple_field("onExit",       "Action[]"),
        simple_field("timeline",     "array"),
        simple_field("transitions",  "array"),
    )

    outer = (
        f'<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="6" CELLPADDING="0" '
        f'BGCOLOR="{BG}" COLOR="{CB}" STYLE="ROUNDED">'
        f'{row_title}'
        f'{row_fields_wrap}'
        f'{row_global}'
        f'{row_states}'
        f'</TABLE>'
    )
    return f"<{outer}>"


def main():
    dot = graphviz.Digraph(name="scene_schema")
    dot.attr("graph", **{k: v for k, v in A.GRAPH.items()})
    dot.node("scene", label=build_label(), **A.NODE)
    render_diagram(dot)


if __name__ == "__main__":
    main()