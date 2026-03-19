"""
fsm_pristup.py
--------------
Prístup FSM (Finite State Machine) k riadiacej logike expozície.
Neblokujúce prechody medzi stavmi cez udalosti.
Output: outputs/fsm_pristup.svg
"""

import graphviz
from theme import Flowchart as F
from render import render_diagram

GRAPH_OVERRIDE = {
    "rankdir": "TB",
    "size": "3.5,5.0",
    "ratio": "compress",
    "ranksep": "0.5",
    "nodesep": "0.4",
}


def build():
    dot = graphviz.Digraph(name="fsm_pristup")
    dot.attr("graph", **{k: v for k, v in F.GRAPH.items()})
    dot.attr("graph", **GRAPH_OVERRIDE)

    dot.node("start", "Štart",   **F.TERMINAL)
    dot.node("s1",    "Stav A",  **F.PROCESS)
    dot.node("s2",    "Stav B",  **F.PROCESS)
    dot.node("s3",    "Stav C",  **F.PROCESS)
    dot.node("end",   "Koniec",  **F.TERMINAL)

    dot.edge("start", "s1",  **F.FLOW)
    dot.edge("s1",    "s2",  label="  udalosť 1", **F.BRANCH)
    dot.edge("s2",    "s3",  label="  udalosť 2", **F.BRANCH)
    dot.edge("s3",    "s1",  label="  udalosť 3", **F.BRANCH)
    dot.edge("s2",    "s1",  label="  udalosť 4", **F.BRANCH)
    dot.edge("s3",    "end", label="  udalosť 5", **F.BRANCH)

    render_diagram(dot, "fsm_pristup")


if __name__ == "__main__":
    build()


if __name__ == "__main__":
    build()