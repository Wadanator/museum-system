"""
scene_json.py
-------------
High-level 'Scene JSON' overview — mint-green family (parent level).
Output: outputs/scene_json.svg
"""

import graphviz
from theme import SceneAnatomy as A
from gv_html import font, thin_rule, title_bar, simple_field, hint_row, subsection
from render import render_diagram

C1, C3 = A.C_PRIMARY, A.C_MUTED
CB, CD = A.C_BORDER, A.C_DIVIDER
BG = A.BG_STATE
T, SH, BD, DT = A.FS_TITLE, A.FS_SECTION, A.FS_BODY, A.FS_DETAIL


def build_label():
    row_title = title_bar(
        "Scene", subtitle=".json",
        bg=A.BG_HEADER, color="#FFFFFF", color_sub="#C0F0D8",
        size=T, size_sub=BD, colspan=2, padding=10,
    ) + thin_rule(colspan=2, color=CB)

    row_fields_inner = (
        simple_field("sceneId",      "string",
                     color_name=C1, color_type=C3, color_note=C3)
      + simple_field("version",      "string",
                     color_name=C1, color_type=C3, color_note=C3)
      + simple_field("description",  "string",
                     color_name=C1, color_type=C3, color_note=C3)
      + simple_field("initialState", "string",
                     note="→ name of the first state",
                     color_name=C1, color_type=C3, color_note=C3)
    )
    row_fields = (
        f'<TR><TD COLSPAN="2" BGCOLOR="{BG}" BORDER="0" CELLPADDING="8">'
        f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0">{row_fields_inner}</TABLE>'
        f'</TD></TR>'
        + thin_rule(colspan=2, color=CD)
    )

    row_global = subsection(
        "globalEvents  [ ]",
        hint_row("Transition[]  —  active in every state", color=A.C_MUTED),
        simple_field("type", "string", note="timeout  |  mqttMessage  |  …",
                     color_name=C1, color_type=C3, color_note=C3),
        simple_field("goto", "string", note="state name  or  END",
                     color_name=C1, color_type=C3, color_note=C3),
        f'<TR><TD COLSPAN="2" BORDER="0" CELLPADDING="3"></TD></TR>',
        hdr_color=A.SUB_GLOBAL_HDR, bg_color=A.SUB_GLOBAL_BG,
        bdr_color=A.SUB_GLOBAL_BDR, divider_color=A.SUB_GLOBAL_BDR,
        hdr_text="#FFFFFF", fs_header=SH, colspan=2,
    )

    row_states = subsection(
        "states  { }",
        hint_row("One entry per state, keyed by state name.", color=A.C_MUTED),
        simple_field("description",  "string",
                     color_name=C1, color_type=C3, color_note=C3),
        simple_field("onEnter",      "Action[]",
                     color_name=C1, color_type=C3, color_note=C3),
        simple_field("onExit",       "Action[]",
                     color_name=C1, color_type=C3, color_note=C3),
        simple_field("timeline",     "array",
                     color_name=C1, color_type=C3, color_note=C3),
        simple_field("transitions",  "array",
                     color_name=C1, color_type=C3, color_note=C3),
        f'<TR><TD COLSPAN="2" BORDER="0" CELLPADDING="3"></TD></TR>',
        hdr_color=A.SUB_STATES_HDR, bg_color=A.SUB_STATES_BG,
        bdr_color=A.SUB_STATES_BDR, divider_color=A.SUB_STATES_BDR,
        hdr_text="#FFFFFF", fs_header=SH, colspan=2,
    )

    outer = (
        f'<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" '
        f'BGCOLOR="{BG}" COLOR="{CB}" STYLE="ROUNDED">'
        f'{row_title}{row_fields}{row_global}{row_states}'
        f'</TABLE>'
    )
    return f"<{outer}>"


def main():
    dot = graphviz.Digraph(name="scene_json")
    dot.attr("graph", **{k: v for k, v in A.GRAPH.items()})
    dot.node("scene", label=build_label(), **A.NODE)
    render_diagram(dot)


if __name__ == "__main__":
    main()