"""
_template_block.py
------------------
Template pre: HTML-label referenčné bloky
Štýl: jeden veľký annotovaný blok — vhodný ako cheat-sheet, schéma objektu,
      dokumentácia štruktúry (Scene, State, Class, Config, API response…)

POSTUP:
  1. Skopíruj, premenuj (napr. video_player_class.py)
  2. Vyber paletu — SceneAnatomy (mint) alebo StateAnatomy (sky blue)
     Pravidlo: ak ide o parent/top-level objekt → SceneAnatomy
               ak ide o child/detail objekt     → StateAnatomy
  3. Uprav title_bar(), sekcie, polia
  4. python3 nazov.py  →  outputs/nazov.svg

DOSTUPNÉ HELPERY (gv_html.py):
  title_bar(label, subtitle, bg, ...)   — farebná titulná lišta
  simple_field(name, type, note, ...)   — jeden riadok:  meno   typ   poznámka
  hint_row(text, color, ...)            — kurzívny popis / hint
  subsection(title, *rows, ...)         — farebná podsekcia s hlavičkou
  thin_rule(colspan, color)             — 1px oddeľovač
  section_column(header, *items, ...)   — stĺpec (onEnter / timeline / onExit)
  action_block(type, fields, ...)       — blok akcie (mqtt/audio/video)
  timeline_block(at, type, fields, ...) — položka timeline
  transition_card(type, fields, ...)    — karta prechodu

PALETY:
  SceneAnatomy (mint — parent):
    BG_STATE, BG_HEADER, BG_SECTION, BG_ITEM
    C_BORDER, C_DIVIDER, C_PRIMARY, C_MUTED
    SUB_GLOBAL_HDR/BG/BDR  — teal subsekcia
    SUB_STATES_HDR/BG/BDR  — sky subsekcia (naznačuje child)

  StateAnatomy (sky blue — child):
    BG_STATE, BG_HEADER, BG_ITEM
    C_BORDER, C_DIVIDER, C_PRIMARY, C_MUTED
    SEC_ONENTER / SEC_TIMELINE / SEC_ONEXIT  — tuple (hdr, bg, border, divider)
    SEC_TRANS_HDR / SEC_TRANS_BG / SEC_TRANS_BDR
    ACT_MQTT / ACT_AUDIO / ACT_VIDEO / ACT_KV
    TR_TIMEOUT / TR_MQTT / TR_VIDEO / TR_ALWAYS
"""

import graphviz
from theme import SceneAnatomy as A   # ← zmeň na StateAnatomy pre child objekt
from gv_html import (
    font, thin_rule, title_bar,
    simple_field, hint_row, subsection,
    # section_column, action_block, timeline_block, transition_card  ← odkomentuj ak treba
)
from render import render_diagram

C1, C3 = A.C_PRIMARY, A.C_MUTED
CB, CD = A.C_BORDER, A.C_DIVIDER
BG = A.BG_STATE
T, SH, BD, DT = A.FS_TITLE, A.FS_SECTION, A.FS_BODY, A.FS_DETAIL


def build_label() -> str:

    # ── Titulná lišta ─────────────────────────────────────────────────────
    # subtitle = voliteľný šedý text vedľa názvu (napr. ".json", ": class")
    row_title = title_bar(
        "NázovObjektu", subtitle=".json",        # ← uprav
        bg=A.BG_HEADER, color="#FFFFFF", color_sub="#C0F0D8",
        size=T, size_sub=BD, colspan=2, padding=10,
    ) + thin_rule(colspan=2, color=CB)

    # ── Skalárne polia ────────────────────────────────────────────────────
    # simple_field(name, type, note="")
    # note = krátka poznámka za typom, napr. "→ povinné", "default: 0"
    row_fields_inner = (
        simple_field("pole1",  "string",  color_name=C1, color_type=C3, color_note=C3)
      + simple_field("pole2",  "number",  color_name=C1, color_type=C3, color_note=C3)
      + simple_field("pole3",  "boolean", note="default: false",
                     color_name=C1, color_type=C3, color_note=C3)
    )
    row_fields = (
        f'<TR><TD COLSPAN="2" BGCOLOR="{BG}" BORDER="0" CELLPADDING="8">'
        f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0">{row_fields_inner}</TABLE>'
        f'</TD></TR>'
        + thin_rule(colspan=2, color=CD)
    )

    # ── Farebná podsekcia A ───────────────────────────────────────────────
    # Použi A.SUB_GLOBAL_HDR/BG/BDR pre teal (prvá podsekcia)
    # Použi A.SUB_STATES_HDR/BG/BDR pre sky-blue (druhá podsekcia — child hint)
    row_sekcia_a = subsection(
        "názveSekcie  [ ]",                          # ← uprav
        hint_row("Krátky popis čo táto sekcia obsahuje.", color=C3),
        simple_field("podPole1", "string",  color_name=C1, color_type=C3, color_note=C3),
        simple_field("podPole2", "string",  color_name=C1, color_type=C3, color_note=C3),
        f'<TR><TD COLSPAN="2" BORDER="0" CELLPADDING="3"></TD></TR>',
        hdr_color=A.SUB_GLOBAL_HDR, bg_color=A.SUB_GLOBAL_BG,
        bdr_color=A.SUB_GLOBAL_BDR, divider_color=A.SUB_GLOBAL_BDR,
        hdr_text="#FFFFFF", fs_header=SH, colspan=2,
    )

    # ── Farebná podsekcia B ───────────────────────────────────────────────
    row_sekcia_b = subsection(
        "ďalšiaSekcia  { }",                         # ← uprav
        hint_row("Ďalší popis.", color=C3),
        simple_field("podPole3", "array",   color_name=C1, color_type=C3, color_note=C3),
        simple_field("podPole4", "object",  color_name=C1, color_type=C3, color_note=C3),
        f'<TR><TD COLSPAN="2" BORDER="0" CELLPADDING="3"></TD></TR>',
        hdr_color=A.SUB_STATES_HDR, bg_color=A.SUB_STATES_BG,
        bdr_color=A.SUB_STATES_BDR, divider_color=A.SUB_STATES_BDR,
        hdr_text="#FFFFFF", fs_header=SH, colspan=2,
    )

    # ── Outer tabuľka ─────────────────────────────────────────────────────
    outer = (
        f'<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0" '
        f'BGCOLOR="{BG}" COLOR="{CB}" STYLE="ROUNDED">'
        f'{row_title}'
        f'{row_fields}'
        f'{row_sekcia_a}'
        f'{row_sekcia_b}'
        f'</TABLE>'
    )
    return f"<{outer}>"


def main():
    dot = graphviz.Digraph(name="_template_block")        # ← zmeň na názov súboru
    dot.attr("graph", **{k: v for k, v in A.GRAPH.items()})
    dot.node("root", label=build_label(), **A.NODE)
    render_diagram(dot)


if __name__ == "__main__":
    main()