"""
state_anatomy.py
----------------
'State Anatomy' reference diagram — a single annotated block showing every
possible field that one state in the Museum Automation System JSON State
Machine may contain.

Output: outputs/state_anatomy.svg
"""

import graphviz
from theme import StateAnatomy as A
from gv_html import (
    font, thin_rule,
    action_block, timeline_block,
    section_column, transition_card,
)
from render import render_diagram


# ── shorthand colour / size aliases ──────────────────────────────────────
T   = A.FS_TITLE
SH  = A.FS_SECTION
BD  = A.FS_BODY
DT  = A.FS_DETAIL
C1, C2, C3 = A.C_PRIMARY, A.C_SECONDARY, A.C_MUTED
CB, CD      = A.C_BORDER, A.C_DIVIDER
BG, BGH, BGS, BGI = A.BG_STATE, A.BG_HEADER, A.BG_SECTION, A.BG_ITEM


# ═══════════════════════════════════════════════════════════════════════════
# Label assembly
# ═══════════════════════════════════════════════════════════════════════════

def build_label() -> str:

    # Row 1 — state name header bar
    row_name = (
        f'<TR>'
        f'<TD COLSPAN="3" BGCOLOR="{BGH}" BORDER="0" CELLPADDING="9" ALIGN="LEFT">'
        f'{font("STATE_EXAMPLE", size=T, color=C1, bold=True)}'
        f'</TD></TR>'
    )

    # Row 2 — description field
    row_desc = (
        f'<TR>'
        f'<TD COLSPAN="3" BORDER="0" CELLPADDING="7" ALIGN="LEFT">'
        f'{font("description:", size=DT, color=C3)}&nbsp;'
        f'{font("&quot;Example state showcasing all available properties&quot;", size=DT, color=C3, italic=True)}'
        f'</TD></TR>'
    )

    # Row 3 — full-width rule
    row_divider = (
        f'<TR><TD COLSPAN="3" BGCOLOR="{CB}" HEIGHT="1" BORDER="0"></TD></TR>'
    )

    # Row 4 — three section columns
    col_onenter = section_column(
        "onEnter",
        action_block("mqtt",  {"topic": '"room1/light/fire"', "message": '"ON"'},
                     color_type=C2, color_kv=C3),
        action_block("audio", {"message": '"PLAY:intro.wav:1"'},
                     color_type=C2, color_kv=C3),
        action_block("video", {"message": '"PLAY_VIDEO:clip.mp4"'},
                     color_type=C2, color_kv=C3),
        bg_header=BGH, bg_section=BGS, color_border=CB,
        color_divider=CD, color_header=C1, fs_header=SH,
    )

    col_timeline = section_column(
        "timeline",
        timeline_block("1.4 s", "mqtt",    {"topic": '"room1/light/2"', "message": '"ON"'},
                       color_type=C2, color_kv=C3),
        timeline_block("5 s",   "audio",   {"message": '"PLAY:sfx.wav:0.8"'},
                       color_type=C2, color_kv=C3),
        timeline_block("10 s",  "actions", {"[0]": "mqtt", "[1]": "mqtt"},
                       color_type=C2, color_kv=C3),
        bg_header=BGH, bg_section=BGS, color_border=CB,
        color_divider=CD, color_header=C1, fs_header=SH,
    )

    col_onexit = section_column(
        "onExit",
        action_block("audio", {"message": '"STOP"'},
                     color_type=C2, color_kv=C3),
        action_block("mqtt",  {"topic": '"room1/motor1"', "message": '"STOP"'},
                     color_type=C2, color_kv=C3),
        action_block("video", {"message": '"STOP_VIDEO"'},
                     color_type=C2, color_kv=C3),
        bg_header=BGH, bg_section=BGS, color_border=CB,
        color_divider=CD, color_header=C1, fs_header=SH,
    )

    row_sections = f'<TR>{col_onenter}{col_timeline}{col_onexit}</TR>'

    # Row 5 — transitions header
    row_trans_header = (
        f'<TR>'
        f'<TD COLSPAN="3" BGCOLOR="{BGH}" BORDER="0" CELLPADDING="5" ALIGN="CENTER">'
        f'{font("transitions", size=SH, color=C1, bold=True)}'
        f'</TD></TR>'
    )
    row_trans_rule = (
        f'<TR><TD COLSPAN="3" BGCOLOR="{CD}" HEIGHT="1" BORDER="0"></TD></TR>'
    )

    # Row 6 — transition cards
    cards = "".join([
        transition_card("timeout",     {"delay": "30",   "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=CB, color_type=C2, color_kv=C3),
        transition_card("mqttMessage", {"topic": '"room1/button1"', "message": '"PRESS"', "goto": '"END"'},
                        bg_item=BGI, color_border=CB, color_type=C2, color_kv=C3),
        transition_card("videoEnd",    {"target": '"clip.mp4"', "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=CB, color_type=C2, color_kv=C3),
        transition_card("always",      {"delay": "0",    "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=CB, color_type=C2, color_kv=C3),
    ])

    cards_table = (
        f'<TABLE BORDER="0" CELLSPACING="4" CELLPADDING="0">'
        f'<TR>{cards}</TR>'
        f'</TABLE>'
    )

    row_transitions = (
        f'<TR>'
        f'<TD COLSPAN="3" BORDER="0" CELLPADDING="8" BGCOLOR="{BGS}" ALIGN="CENTER">'
        f'{cards_table}'
        f'</TD></TR>'
    )

    # Outer table
    outer = (
        f'<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" '
        f'BGCOLOR="{BG}" COLOR="{CB}" STYLE="ROUNDED">'
        f'{row_name}{row_desc}{row_divider}'
        f'{row_sections}'
        f'{row_trans_header}{row_trans_rule}{row_transitions}'
        f'</TABLE>'
    )
    return f"<{outer}>"


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    dot = graphviz.Digraph(name="state_anatomy")
    dot.attr("graph", **{k: v for k, v in A.GRAPH.items()})
    dot.node("state", label=build_label(), **A.NODE)
    render_diagram(dot)


if __name__ == "__main__":
    main()