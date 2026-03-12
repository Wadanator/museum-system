"""
gv_html.py
----------
Reusable HTML-label building blocks for Graphviz diagrams.
All defaults draw from theme.py candy tokens — no hardcoded greys.

    from gv_html import font, thin_rule, spacer, simple_field, hint_row,
                        subsection, action_block, timeline_block,
                        section_column, transition_card
"""

from theme import (
    FONT_FAMILY,
    NEUTRAL_TEXT, NEUTRAL_MUTED, NEUTRAL_DIV, NEUTRAL_BORDER, NEUTRAL_WHITE,
    MINT_DEEP, MINT_LIGHT, MINT_MID, MINT_RULE,
    SKY_DEEP, SKY_LIGHT, SKY_MID, SKY_RULE,
    LAV_DEEP, LAV_LIGHT, LAV_MID, LAV_RULE,
    PEACH_DEEP, PEACH_LIGHT, PEACH_MID, PEACH_RULE,
    LEM_DEEP, LEM_LIGHT, LEM_MID, LEM_RULE,
)


# ===========================================================================
# Primitives
# ===========================================================================

def font(text: str, size="10", color=NEUTRAL_TEXT,
         bold: bool = False, italic: bool = False) -> str:
    """Wrap *text* in a Graphviz <FONT> tag."""
    inner = text
    if bold:   inner = f"<B>{inner}</B>"
    if italic: inner = f"<I>{inner}</I>"
    return f'<FONT FACE="{FONT_FAMILY}" POINT-SIZE="{size}" COLOR="{color}">{inner}</FONT>'


def thin_rule(colspan: int = 1, color: str = NEUTRAL_DIV) -> str:
    """1-pixel horizontal divider row."""
    return (
        f'<TR><TD COLSPAN="{colspan}" BGCOLOR="{color}" '
        f'HEIGHT="1" BORDER="0"></TD></TR>'
    )


def spacer(colspan: int = 1, height: int = 4) -> str:
    return f'<TR><TD COLSPAN="{colspan}" BORDER="0" HEIGHT="{height}"></TD></TR>'


def padding_row(colspan: int = 1, height: int = 3) -> str:
    """Invisible bottom-padding row inside a subsection."""
    return f'<TR><TD COLSPAN="{colspan}" BORDER="0" CELLPADDING="{height}"></TD></TR>'


# ===========================================================================
# Generic field / label helpers
# (usable in any HTML-label block — scene, state, class diagram, pipeline…)
# ===========================================================================

def simple_field(name: str, type_str: str, note: str = "",
                 color_name=NEUTRAL_TEXT, color_type=NEUTRAL_MUTED,
                 color_note=NEUTRAL_MUTED,
                 size_name="8", size_type="7.5", size_note="7.5",
                 width: int = 130) -> str:
    """
    One key: type  [optional note] row.
    Used in scene_json, state_anatomy, and any reference block.

        sceneId    string    → name of the first state
    """
    n = (
        f"&nbsp;&nbsp;{font(note, size=size_note, color=color_note, italic=True)}"
        if note else ""
    )
    return (
        f'<TR>'
        f'<TD ALIGN="LEFT" BORDER="0" CELLPADDING="3" WIDTH="{width}">'
        f'{font(name, size=size_name, color=color_name, bold=True)}'
        f'</TD>'
        f'<TD ALIGN="LEFT" BORDER="0" CELLPADDING="3">'
        f'{font(type_str, size=size_type, color=color_type, italic=True)}{n}'
        f'</TD>'
        f'</TR>'
    )


def hint_row(text: str, color=NEUTRAL_MUTED,
             size="7.5", colspan: int = 2) -> str:
    """Italic muted hint / description line inside a block."""
    return (
        f'<TR><TD COLSPAN="{colspan}" BORDER="0" CELLPADDING="4" ALIGN="LEFT">'
        f'{font(text, size=size, color=color, italic=True)}'
        f'</TD></TR>'
    )


def title_bar(label: str, subtitle: str = "",
              bg=MINT_DEEP, color="#FFFFFF", color_sub="#DDFFF0",
              size="13", size_sub="8", colspan: int = 2,
              padding: int = 10) -> str:
    """
    Full-width coloured title bar for any HTML-label block.

        Scene   .json
    """
    sub = (
        f'&nbsp;&nbsp;{font(subtitle, size=size_sub, color=color_sub, italic=True)}'
        if subtitle else ""
    )
    return (
        f'<TR><TD COLSPAN="{colspan}" BGCOLOR="{bg}" BORDER="0" '
        f'CELLPADDING="{padding}" ALIGN="LEFT">'
        f'{font(label, size=size, color=color, bold=True)}{sub}'
        f'</TD></TR>'
    )


def subsection(title: str, *rows: str,
               hdr_color=SKY_DEEP, bg_color=SKY_LIGHT,
               bdr_color=SKY_MID, divider_color=SKY_RULE,
               hdr_text="#FFFFFF", fs_header="9",
               colspan: int = 2) -> str:
    """
    Coloured inner subsection box with header + body rows.
    Works for any number of colspan columns.

        ┌─ globalEvents [ ] ────────────────┐
        │ Transition[] — active in…         │
        │ type    string   timeout | mqtt…  │
        └───────────────────────────────────┘
    """
    inner_hdr = (
        f'<TR><TD COLSPAN="{colspan}" BGCOLOR="{hdr_color}" BORDER="0" '
        f'CELLPADDING="6" ALIGN="LEFT">'
        f'{font(title, size=fs_header, color=hdr_text, bold=True)}'
        f'</TD></TR>'
        + thin_rule(colspan=colspan, color=divider_color)
    )
    body = "".join(rows)
    inner = (
        f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0" BGCOLOR="{bg_color}">'
        f'{inner_hdr}{body}'
        f'</TABLE>'
    )
    return (
        f'<TR>'
        f'<TD COLSPAN="{colspan}" BORDER="1" CELLPADDING="0" '
        f'BGCOLOR="{bg_color}" COLOR="{bdr_color}">'
        f'{inner}'
        f'</TD>'
        f'</TR>'
    )


# ===========================================================================
# Action / timeline blocks  (State-level content)
# ===========================================================================

def kv_rows(fields: dict, size_key="7.5", size_val="7.5",
            color_key=NEUTRAL_MUTED, color_val=NEUTRAL_MUTED) -> str:
    """Render a dict as indented  key: value  rows."""
    rows = ""
    for key, val in fields.items():
        rows += (
            f'<TR><TD ALIGN="LEFT" BORDER="0">'
            f'{font(f"&nbsp;&nbsp;{key}:&nbsp;", size=size_key, color=color_key)}'
            f'{font(val, size=size_val, color=color_val, italic=True)}'
            f'</TD></TR>'
        )
    return rows


def action_block(action_type: str, fields: dict,
                 color_type=MINT_DEEP, color_kv=NEUTRAL_MUTED) -> str:
    """
    Compact block for one action:
        mqtt
          topic:   "room/device"
          message: "ON"
    """
    rows = (
        f'<TR><TD ALIGN="LEFT" BORDER="0">'
        f'{font(action_type, size="8", color=color_type, bold=True)}'
        f'</TD></TR>'
        + kv_rows(fields, color_key=color_kv, color_val=color_kv)
    )
    return f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1">{rows}</TABLE>'


def timeline_block(at_seconds: str, action_type: str, fields: dict,
                   color_type=MINT_DEEP, color_kv=NEUTRAL_MUTED) -> str:
    """
    One timeline entry:
        @ 5s
          action:  audio
          message: "PLAY:sfx.wav:1"
    """
    rows = (
        f'<TR><TD ALIGN="LEFT" BORDER="0">'
        f'{font(f"@ {at_seconds}", size="8", color=color_type, bold=True)}'
        f'</TD></TR>'
        f'<TR><TD ALIGN="LEFT" BORDER="0">'
        f'{font("&nbsp;&nbsp;action:&nbsp;", size="7.5", color=color_kv)}'
        f'{font(action_type, size="7.5", color=color_kv, italic=True)}'
        f'</TD></TR>'
        + kv_rows(fields, color_key=color_kv, color_val=color_kv)
    )
    return f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1">{rows}</TABLE>'


def section_column(header: str, *item_htmls: str,
                   bg_header=SKY_DEEP, bg_section=SKY_LIGHT,
                   color_border=SKY_MID, color_divider=SKY_RULE,
                   color_header="#FFFFFF", fs_header="9") -> str:
    """
    One column cell (onEnter / timeline / onExit).
    Returns a <TD> ready for inclusion in a <TR>.
    Pass per-section accent colours from StateAnatomy.SEC_* tuples.
    """
    hdr = (
        f'<TR><TD ALIGN="CENTER" BORDER="0" CELLPADDING="5" BGCOLOR="{bg_header}">'
        f'{font(header, size=fs_header, color=color_header, bold=True)}'
        f'</TD></TR>'
    )
    body = hdr + thin_rule(color=color_divider)
    for i, item in enumerate(item_htmls):
        body += (
            f'<TR><TD BORDER="0" CELLPADDING="6" ALIGN="LEFT" VALIGN="TOP">'
            f'{item}'
            f'</TD></TR>'
        )
        if i < len(item_htmls) - 1:
            body += thin_rule(color=color_divider)

    inner = (
        f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0" BGCOLOR="{bg_section}">'
        f'{body}'
        f'</TABLE>'
    )
    return (
        f'<TD VALIGN="TOP" BORDER="1" CELLPADDING="0" '
        f'BGCOLOR="{bg_section}" COLOR="{color_border}">'
        f'{inner}'
        f'</TD>'
    )


def transition_card(type_str: str, fields: dict,
                    bg_item=NEUTRAL_WHITE, color_border=SKY_MID,
                    color_type=SKY_DEEP, color_kv=NEUTRAL_MUTED) -> str:
    """One transition card as a bordered <TD>."""
    rows = (
        f'<TR><TD ALIGN="LEFT" BORDER="0">'
        f'{font(type_str, size="8", color=color_type, bold=True)}'
        f'</TD></TR>'
        + kv_rows(fields, color_key=color_kv, color_val=color_kv)
    )
    inner = f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="1">{rows}</TABLE>'
    return (
        f'<TD VALIGN="TOP" BORDER="1" CELLPADDING="7" '
        f'BGCOLOR="{bg_item}" COLOR="{color_border}">'
        f'{inner}'
        f'</TD>'
    )