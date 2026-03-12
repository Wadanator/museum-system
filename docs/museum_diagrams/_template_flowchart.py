"""
_template_flowchart.py
----------------------
Template pre: Flowchart, Pipeline, Architecture, StateMachine, Software
Štýl:  ľavá → pravá, nízky diagram, vhodný pod text na A4.

POSTUP:
  1. Skopíruj tento súbor, premenuj (napr. video_pipeline.py)
  2. Vyber jednu triedu z theme.py (sekcia "Ktorú triedu použiť?" v DIAGRAM_GUIDE.md)
  3. Nahraď uzly a hrany — NIKDY nemeň **F.XXX štýly, len labely
  4. Ak je diagram príliš plochý / vysoký, uprav size= nižšie
  5. python3 nazov.py  →  outputs/nazov.svg

DOSTUPNÉ TRIEDY A ICH UZLY / HRANY:
─────────────────────────────────────────────────────────────────────────────
  Flowchart   F.TERMINAL, F.PROCESS, F.DECISION, F.IO, F.SUBPROCESS, F.EVENT
              F.FLOW, F.BRANCH, F.DASHED

  Pipeline    PL.SOURCE, PL.PROCESS, PL.QUEUE, PL.SINK, PL.SERVICE,
              PL.STORE, PL.ERROR
              PL.FLOW, PL.ASYNC, PL.PUBLISH, PL.SUBSCRIBE, PL.ERROR_EDGE

  Architecture
              Arch.MASTER, Arch.DEVICE, Arch.BROKER, Arch.DASHBOARD,
              Arch.SERVICE, Arch.EXTERNAL, Arch.MODULE
              Arch.MQTT, Arch.MQTT_LABELLED, Arch.SOCKET_IO, Arch.HTTP,
              Arch.LINK, Arch.WIRE

  StateMachine
              SM.INITIAL, SM.NORMAL, SM.ACTIVE, SM.END
              SM.TRANSITION, SM.TRANSITION_TIMEOUT, SM.SELF_LOOP

  Software    SW.MODULE, SW.CLASS, SW.ABSTRACT, SW.INTERFACE, SW.FUNCTION,
              SW.DATABASE, SW.CONSTANT, SW.EXTERNAL
              SW.INHERITS, SW.IMPLEMENTS, SW.USES, SW.CALLS, SW.OWNS
─────────────────────────────────────────────────────────────────────────────

FAREBNÚ LOGIKA (platí naprieč všetkými triedami):
  🟢 MINT      — zdroj, štart, aktívny vstup
  🔵 SKY       — logika, subprocess, detail
  🟣 LAVENDER  — sekvencia, interface, async
  🍑 PEACH     — I/O, výstup, komunikácia
  🟡 LEMON     — rozhodnutie, fronta, pozornosť
  🌸 ROSE      — error, externý impulz, koniec
  ⬜ NEUTRAL   — vonkajší systém

NASTAVENIE VEĽKOSTI:
  size="7.5,2.8"  →  vhodné pod odsek textu na A4 (štandardný flowchart)
  size="7.5,3.5"  →  pre širší diagram so viac vetvami
  size="7.5,4.5"  →  pre komplexnú architektúru / software diagram
  ratio="compress" necháme vždy — nepresahuje size box, nedeformuje uzly
"""

import graphviz
from theme import Flowchart as F   # ← zmeň na Pipeline, Architecture, SM, SW...
from render import render_diagram

# Ak potrebuješ iný size ako default z F.GRAPH, pridaj ho sem:
SIZE_OVERRIDE = {}          # napr. {"size": "7.5,3.5"} — inak nechaj prázdne


def build():
    dot = graphviz.Digraph(name="_template_flowchart")   # ← zmeň na názov súboru
    dot.attr("graph", **{k: v for k, v in F.GRAPH.items()})
    if SIZE_OVERRIDE:
        dot.attr("graph", **SIZE_OVERRIDE)

    # ── UZLY ─────────────────────────────────────────────────────────────
    # Pravidlo: jeden uzol = jedna zodpovednosť, label max 2 riadky
    # "\n" = nový riadok v labeli

    dot.node("start", "Štart",          **F.TERMINAL)    # 🟣 lavender oval
    dot.node("step1", "Krok 1",         **F.PROCESS)     # 🟢 mint rect
    dot.node("check", "Podmienka?",     **F.DECISION)    # 🟡 lemon diamond
    dot.node("sub",   "Subprocess",     **F.SUBPROCESS)  # 🔵 sky double-rect
    dot.node("io",    "Vstup / výstup", **F.IO)          # 🍑 peach parallelogram
    dot.node("event", "Externá\nudalosť", **F.EVENT)     # 🌸 rose rect
    dot.node("end",   "Koniec",         **F.TERMINAL)    # 🟣 lavender oval

    # ── HRANY ────────────────────────────────────────────────────────────
    # F.FLOW   = plná čiara, hlavný tok
    # F.BRANCH = plná čiara + label (áno/nie, match/no match...)
    # F.DASHED = prerušovaná (voliteľný tok, späť-loop, poznámka)

    dot.edge("start", "step1",  **F.FLOW)
    dot.edge("step1", "check",  **F.FLOW)
    dot.edge("check", "sub",    label="  áno",  **F.BRANCH)
    dot.edge("check", "io",     label="  nie",  **F.BRANCH)
    dot.edge("sub",   "end",    **F.FLOW)
    dot.edge("io",    "end",    **F.FLOW)
    # dot.edge("end", "start",  **F.DASHED)   # ← príklad spätnej slučky

    render_diagram(dot)


if __name__ == "__main__":
    build()