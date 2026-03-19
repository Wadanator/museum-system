"""
linearny_pristup.py
-------------------
Lineárny (sekvenčný) prístup k riadiacej logike expozície.
Pevná séria akcií — vlákno blokované počas každého čakania.
Output: outputs/linearny_pristup.svg
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
    dot = graphviz.Digraph(name="linearny_pristup")
    dot.attr("graph", **{k: v for k, v in F.GRAPH.items()})
    dot.attr("graph", **GRAPH_OVERRIDE)

    dot.node("start", "Štart",   **F.TERMINAL)
    dot.node("a1",    "Akcia",   **F.PROCESS)
    dot.node("w1",    "Čakaj",   **F.SUBPROCESS)
    dot.node("a2",    "Akcia",   **F.PROCESS)
    dot.node("w2",    "Čakaj",   **F.SUBPROCESS)
    dot.node("a3",    "Akcia",   **F.PROCESS)
    dot.node("end",   "Koniec",  **F.TERMINAL)

    dot.node("note", "blokované", **F.NOTE)

    dot.edge("start", "a1",  **F.FLOW)
    dot.edge("a1",    "w1",  **F.FLOW)
    dot.edge("w1",    "a2",  **F.FLOW)
    dot.edge("a2",    "w2",  **F.FLOW)
    dot.edge("w2",    "a3",  **F.FLOW)
    dot.edge("a3",    "end", **F.FLOW)

    dot.edge("w1", "note", **F.DASHED)
    dot.edge("w2", "note", **F.DASHED)

    render_diagram(dot, "linearny_pristup")


if __name__ == "__main__":
    build()