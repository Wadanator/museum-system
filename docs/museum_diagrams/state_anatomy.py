"""
state_anatomy.py
----------------
State Anatomy reference diagram — sky-blue family (child of Scene/mint).
Each section has its own accent colour:
  onEnter     → mint green
  timeline    → lavender
  onExit      → peach
  transitions → lemon yellow

Output: outputs/state_anatomy.svg
"""

import graphviz
from theme import StateAnatomy as A
from gv_html import (
    font, thin_rule, title_bar,
    action_block, timeline_block,
    section_column, transition_card,
)
from render import render_diagram

T   = A.FS_TITLE
SH  = A.FS_SECTION
BD  = A.FS_BODY
DT  = A.FS_DETAIL
C1, C3 = A.C_PRIMARY, A.C_MUTED
CB, CD = A.C_BORDER, A.C_DIVIDER
BG, BGH, BGI = A.BG_STATE, A.BG_HEADER, A.BG_ITEM


def build_label() -> str:

    # ── Row 1: state name bar ─────────────────────────────────────────────
    row_name = title_bar(
        "STATE_EXAMPLE", bg=BGH, color="#FFFFFF",
        size=T, colspan=3, padding=10,
    )

    # ── Row 2: description ────────────────────────────────────────────────
    row_desc = (
        f'<TR>'
        f'<TD COLSPAN="3" BGCOLOR="{BG}" BORDER="0" CELLPADDING="7" ALIGN="LEFT">'
        f'{font("description:", size=DT, color=C3)}&nbsp;'
        f'{font("&quot;Example state showcasing all available properties&quot;", size=DT, color=C3, italic=True)}'
        f'</TD></TR>'
    )

    row_divider = f'<TR><TD COLSPAN="3" BGCOLOR="{CB}" HEIGHT="1" BORDER="0"></TD></TR>'

    # ── Row 3: three section columns, each with its own accent colour ─────
    mh, ms, mb, md = A.SEC_ONENTER
    col_onenter = section_column(
        "onEnter",
        action_block("mqtt",  {"topic": '"room1/light/fire"', "message": '"ON"'},
                     color_type=A.ACT_MQTT, color_kv=A.ACT_KV),
        action_block("audio", {"message": '"PLAY:intro.wav:1"'},
                     color_type=A.ACT_AUDIO, color_kv=A.ACT_KV),
        action_block("video", {"message": '"PLAY_VIDEO:clip.mp4"'},
                     color_type=A.ACT_VIDEO, color_kv=A.ACT_KV),
        bg_header=mh, bg_section=ms, color_border=mb,
        color_divider=md, color_header="#FFFFFF", fs_header=SH,
    )

    lh, ls, lb, ld = A.SEC_TIMELINE
    col_timeline = section_column(
        "timeline",
        timeline_block("1.4 s", "mqtt",    {"topic": '"room1/light/2"', "message": '"ON"'},
                       color_type=A.ACT_MQTT, color_kv=A.ACT_KV),
        timeline_block("5 s",   "audio",   {"message": '"PLAY:sfx.wav:0.8"'},
                       color_type=A.ACT_AUDIO, color_kv=A.ACT_KV),
        timeline_block("10 s",  "actions", {"[0]": "mqtt", "[1]": "mqtt"},
                       color_type=A.ACT_MQTT, color_kv=A.ACT_KV),
        bg_header=lh, bg_section=ls, color_border=lb,
        color_divider=ld, color_header="#FFFFFF", fs_header=SH,
    )

    ph, ps, pb, pd = A.SEC_ONEXIT
    col_onexit = section_column(
        "onExit",
        action_block("audio", {"message": '"STOP"'},
                     color_type=A.ACT_AUDIO, color_kv=A.ACT_KV),
        action_block("mqtt",  {"topic": '"room1/motor1"', "message": '"STOP"'},
                     color_type=A.ACT_MQTT, color_kv=A.ACT_KV),
        action_block("video", {"message": '"STOP_VIDEO"'},
                     color_type=A.ACT_VIDEO, color_kv=A.ACT_KV),
        bg_header=ph, bg_section=ps, color_border=pb,
        color_divider=pd, color_header="#FFFFFF", fs_header=SH,
    )

    row_sections = f'<TR>{col_onenter}{col_timeline}{col_onexit}</TR>'

    # ── Row 4: transitions header — LEMON ────────────────────────────────
    row_trans_header = (
        f'<TR>'
        f'<TD COLSPAN="3" BGCOLOR="{A.SEC_TRANS_HDR}" BORDER="0" '
        f'CELLPADDING="6" ALIGN="CENTER">'
        f'{font("transitions", size=SH, color="#FFFFFF", bold=True)}'
        f'</TD></TR>'
        f'<TR><TD COLSPAN="3" BGCOLOR="{A.SEC_TRANS_BDR}" HEIGHT="1" BORDER="0"></TD></TR>'
    )

    # ── Row 5: transition cards — each type has its own colour ───────────
    cards = "".join([
        transition_card("timeout",
                        {"delay": "30", "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=mb,
                        color_type=A.TR_TIMEOUT, color_kv=A.ACT_KV),
        transition_card("mqttMessage",
                        {"topic": '"room1/button1"', "message": '"PRESS"', "goto": '"END"'},
                        bg_item=BGI, color_border=mb,
                        color_type=A.TR_MQTT, color_kv=A.ACT_KV),
        transition_card("videoEnd",
                        {"target": '"clip.mp4"', "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=pb,
                        color_type=A.TR_VIDEO, color_kv=A.ACT_KV),
        transition_card("audioEnd",
                        {"target": '"intro.wav"', "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=lb,
                        color_type=A.ACT_AUDIO, color_kv=A.ACT_KV),
        transition_card("always",
                        {"delay": "0", "goto": '"STATE_NEXT"'},
                        bg_item=BGI, color_border=lb,
                        color_type=A.TR_ALWAYS, color_kv=A.ACT_KV),
    ])

    row_transitions = (
        f'<TR>'
        f'<TD COLSPAN="3" BORDER="0" CELLPADDING="8" '
        f'BGCOLOR="{A.SEC_TRANS_BG}" ALIGN="CENTER">'
        f'<TABLE BORDER="0" CELLSPACING="4" CELLPADDING="0">'
        f'<TR>{cards}</TR>'
        f'</TABLE>'
        f'</TD></TR>'
    )

    outer = (
        f'<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" '
        f'BGCOLOR="{BG}" COLOR="{CB}" STYLE="ROUNDED">'
        f'{row_name}{row_desc}{row_divider}'
        f'{row_sections}'
        f'{row_trans_header}{row_transitions}'
        f'</TABLE>'
    )
    return f"<{outer}>"


def main() -> None:
    dot = graphviz.Digraph(name="state_anatomy")
    dot.attr("graph", **{k: v for k, v in A.GRAPH.items()})
    dot.node("state", label=build_label(), **A.NODE)
    render_diagram(dot)


if __name__ == "__main__":
    main()