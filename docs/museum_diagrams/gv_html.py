"""
gv_html.py
----------
Reusable HTML-label building blocks for Graphviz diagrams.
Import in any diagram script that uses HTML-like labels.

    from gv_html import font, thin_rule, spacer, action_block, ...
"""

from theme import FONT_FAMILY


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def font(text: str, size="10", color="#111111",
         bold: bool = False, italic: bool = False) -> str:
    """Wrap *text* in a Graphviz <FONT> tag."""
    inner = text
    if bold:   inner = f"<B>{inner}</B>"
    if italic: inner = f"<I>{inner}</I>"
    return f'<FONT FACE="{FONT_FAMILY}" POINT-SIZE="{size}" COLOR="{color}">{inner}</FONT>'


def thin_rule(colspan: int = 1, color: str = "#BBBBBB") -> str:
    """1-pixel horizontal divider row."""
    return (
        f'<TR><TD COLSPAN="{colspan}" BGCOLOR="{color}" '
        f'HEIGHT="1" BORDER="0"></TD></TR>'
    )


def spacer(colspan: int = 1, height: int = 4) -> str:
    return f'<TR><TD COLSPAN="{colspan}" BORDER="0" HEIGHT="{height}"></TD></TR>'


# ---------------------------------------------------------------------------
# Composite blocks
# ---------------------------------------------------------------------------

def kv_rows(fields: dict[str, str], size_key="7.5", size_val="7.5",
            color_key="#777777", color_val="#777777") -> str:
    """Render a dict as indented key: value rows."""
    rows = ""
    for key, val in fields.items():
        rows += (
            f'<TR><TD ALIGN="LEFT" BORDER="0">'
            f'{font(f"&nbsp;&nbsp;{key}:&nbsp;", size=size_key, color=color_key)}'
            f'{font(val, size=size_val, color=color_val, italic=True)}'
            f'</TD></TR>'
        )
    return rows


def action_block(action_type: str, fields: dict[str, str],
                 color_type="#444444", color_kv="#777777") -> str:
    """
    Compact inner table for one action item:
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


def timeline_block(at_seconds: str, action_type: str, fields: dict[str, str],
                   color_type="#444444", color_kv="#777777") -> str:
    """
    Render one timeline entry:
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
                   bg_header="#C4C4C4", bg_section="#F5F5F5",
                   color_border="#AAAAAA", color_divider="#BBBBBB",
                   color_header="#111111", fs_header="9") -> str:
    """
    One column cell (onEnter / timeline / onExit).
    Returns a <TD> element ready for inclusion in a <TR>.
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


def transition_card(type_str: str, fields: dict[str, str],
                    bg_item="#FFFFFF", color_border="#AAAAAA",
                    color_type="#444444", color_kv="#777777") -> str:
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