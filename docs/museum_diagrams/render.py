"""
render.py
---------
Central render helper used by every diagram script.

Usage (at the bottom of any diagram script):
    from render import render_diagram
    render_diagram(dot)          # output name = calling script's filename
    render_diagram(dot, "name")  # explicit override
"""

import os
import sys
import graphviz

# All SVG outputs land in this folder (relative to the diagram scripts).
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def render_diagram(dot: graphviz.Digraph | graphviz.Graph,
                   name: str | None = None) -> str:
    """
    Render *dot* to SVG inside the outputs/ folder.

    Parameters
    ----------
    dot  : Graphviz source object
    name : Base filename without extension.
           If None (default), the caller's script filename is used.
           e.g.  state_anatomy.py  →  outputs/state_anatomy.svg

    Returns the full output path.
    """
    if name is None:
        # Walk up the call stack to find the first __main__ script.
        caller = sys.argv[0]
        name = os.path.splitext(os.path.basename(caller))[0]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, name)

    dot.render(filename=out_path, format="svg", cleanup=True, quiet=True)
    full = f"{out_path}.svg"
    print(f"[✓] SVG → {full}")
    return full