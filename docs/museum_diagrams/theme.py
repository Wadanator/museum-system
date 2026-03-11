"""
theme.py
--------
Centralised Graphviz style configuration for the Museum Automation System thesis.
All colours are chosen for clean black-and-white / greyscale printing.

Import from any diagram script:
    from theme import FONT_FAMILY, GRAPH_DEFAULTS, StateMachine, StateAnatomy, ...
"""

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_FAMILY       = "Helvetica"
FONT_SIZE_NORMAL  = "10"
FONT_SIZE_SMALL   = "8"
FONT_SIZE_LARGE   = "11"

# ---------------------------------------------------------------------------
# Global graph / node / edge defaults
# ---------------------------------------------------------------------------
GRAPH_DEFAULTS = {
    "dpi":       "300",
    "rankdir":   "TB",
    "splines":   "ortho",
    "nodesep":   "0.55",
    "ranksep":   "0.65",
    "pad":       "0.3",
    "fontname":  FONT_FAMILY,
    "fontsize":  FONT_SIZE_NORMAL,
    "label":     "",
    "bgcolor":   "white",
}

NODE_DEFAULTS = {
    "fontname":  FONT_FAMILY,
    "fontsize":  FONT_SIZE_NORMAL,
    "style":     "filled",
    "fillcolor": "white",
    "color":     "black",
    "penwidth":  "1.2",
}

EDGE_DEFAULTS = {
    "fontname":  FONT_FAMILY,
    "fontsize":  FONT_SIZE_SMALL,
    "color":     "black",
    "penwidth":  "1.0",
    "arrowsize": "0.7",
}


# ===========================================================================
# 1. STATE MACHINE
# ===========================================================================
class StateMachine:
    """Styles for JSON-driven state machine diagrams."""

    INITIAL = {
        **NODE_DEFAULTS,
        "shape": "circle", "label": "",
        "width": "0.25", "height": "0.25",
        "fillcolor": "black", "color": "black", "penwidth": "0",
    }
    ACTIVE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,bold",
        "fillcolor": "#E8E8E8", "color": "black", "penwidth": "2.0",
    }
    NORMAL = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "fillcolor": "white",
        "color": "black", "penwidth": "1.2",
    }
    END = {
        **NODE_DEFAULTS,
        "shape": "doublecircle", "width": "0.4", "height": "0.4",
        "fillcolor": "white", "color": "black", "penwidth": "1.5",
    }
    TRANSITION = {
        **EDGE_DEFAULTS,
        "arrowhead": "vee", "arrowsize": "0.65",
    }
    TRANSITION_TIMEOUT = {
        **EDGE_DEFAULTS,
        "arrowhead": "vee", "arrowsize": "0.65",
        "style": "dashed", "color": "#555555",
    }
    SELF_LOOP = {
        **EDGE_DEFAULTS,
        "arrowhead": "vee", "style": "dotted", "color": "#777777",
    }


# ===========================================================================
# 2. FLOWCHART
# ===========================================================================
class Flowchart:
    """Styles for algorithmic / process flowcharts."""

    PROCESS = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": "white", "color": "black", "penwidth": "1.2",
    }
    DECISION = {
        **NODE_DEFAULTS,
        "shape": "diamond", "fillcolor": "#F0F0F0",
        "color": "black", "penwidth": "1.2", "fontsize": FONT_SIZE_SMALL,
    }
    IO = {
        **NODE_DEFAULTS,
        "shape": "parallelogram", "fillcolor": "white",
        "color": "black", "penwidth": "1.2",
    }
    TERMINAL = {
        **NODE_DEFAULTS,
        "shape": "oval", "style": "filled,bold",
        "fillcolor": "#D8D8D8", "color": "black", "penwidth": "1.5",
    }
    SUBPROCESS = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled",
        "fillcolor": "white", "color": "black",
        "penwidth": "1.2", "peripheries": "2",
    }
    FLOW   = {**EDGE_DEFAULTS, "arrowhead": "normal"}
    BRANCH = {**EDGE_DEFAULTS, "arrowhead": "normal",
              "fontsize": FONT_SIZE_SMALL, "fontname": FONT_FAMILY}


# ===========================================================================
# 3. JSON STRUCTURE
# ===========================================================================
class JSON:
    """Styles for visualising nested JSON / config structures."""

    ROOT = {
        **NODE_DEFAULTS,
        "shape": "record", "style": "filled,bold",
        "fillcolor": "#E0E0E0", "color": "black", "penwidth": "1.8",
    }
    OBJECT = {
        **NODE_DEFAULTS,
        "shape": "record", "fillcolor": "#F5F5F5",
        "color": "black", "penwidth": "1.0", "fontsize": FONT_SIZE_SMALL,
    }
    VALUE = {
        **NODE_DEFAULTS,
        "shape": "plaintext", "fillcolor": "white", "fontsize": FONT_SIZE_SMALL,
    }
    ARRAY = {
        **NODE_DEFAULTS,
        "shape": "record", "style": "filled,dashed",
        "fillcolor": "white", "color": "#555555",
        "penwidth": "1.0", "fontsize": FONT_SIZE_SMALL,
    }
    CONTAINS  = {**EDGE_DEFAULTS, "arrowhead": "odot", "arrowsize": "0.5",
                 "style": "solid", "color": "#444444"}
    REFERENCE = {**EDGE_DEFAULTS, "arrowhead": "open",
                 "style": "dashed", "color": "#777777"}


# ===========================================================================
# 4. ARCHITECTURE / NETWORK
# ===========================================================================
class Architecture:
    """Styles for hardware-level / protocol-level architecture diagrams."""

    MASTER    = {**NODE_DEFAULTS, "shape": "rectangle", "style": "filled,bold",
                 "fillcolor": "#D8D8D8", "color": "black", "penwidth": "2.2",
                 "fontsize": FONT_SIZE_LARGE}
    ESP32     = {**NODE_DEFAULTS, "shape": "rectangle", "style": "filled",
                 "fillcolor": "#F0F0F0", "color": "black", "penwidth": "1.4"}
    DASHBOARD = {**NODE_DEFAULTS, "shape": "rectangle", "style": "filled,rounded",
                 "fillcolor": "#E8E8E8", "color": "black", "penwidth": "1.4"}
    BROKER    = {**NODE_DEFAULTS, "shape": "oval", "fillcolor": "white",
                 "color": "black", "penwidth": "1.6"}
    EXTERNAL  = {**NODE_DEFAULTS, "shape": "rectangle", "style": "filled,dashed",
                 "fillcolor": "white", "color": "#888888", "penwidth": "1.0",
                 "fontsize": FONT_SIZE_SMALL}
    MODULE    = {**NODE_DEFAULTS, "shape": "rectangle", "fillcolor": "white",
                 "color": "black", "penwidth": "1.0"}
    MQTT         = {**EDGE_DEFAULTS, "arrowhead": "vee", "arrowsize": "0.7"}
    MQTT_LABELLED= {**EDGE_DEFAULTS, "arrowhead": "vee", "arrowsize": "0.7",
                    "fontsize": FONT_SIZE_SMALL}
    LINK  = {**EDGE_DEFAULTS, "arrowhead": "normal", "arrowtail": "normal",
             "dir": "both", "style": "dashed", "color": "#555555"}
    WIRE  = {**EDGE_DEFAULTS, "arrowhead": "none", "style": "solid",
             "color": "black", "penwidth": "1.6"}


# ===========================================================================
# 5. STATE ANATOMY  (single-state structure diagram)
# ===========================================================================
class StateAnatomy:
    """
    Colour tokens and node/graph settings for the 'State Anatomy' diagram —
    a single-node HTML-table layout documenting every field of one state.
    """

    # muted blue-slate palette  (readable on screen, prints cleanly)
    BG_STATE    = "#E8EEF4"   # overall background — pale steel blue
    BG_HEADER   = "#6B8FA8"   # section headers — muted teal-blue
    BG_SECTION  = "#F2F6FA"   # column / section background
    BG_ITEM     = "#FFFFFF"   # individual card background
    C_BORDER    = "#7A9BB5"   # inner cell borders
    C_DIVIDER   = "#B0C8DA"   # thin horizontal rules
    C_PRIMARY   = "#1A2E3D"   # main labels — dark navy
    C_SECONDARY = "#2E6188"   # key names / type labels — medium blue
    C_MUTED     = "#6B8BA4"   # value strings — muted blue-grey

    # font sizes (pt)
    FS_TITLE   = "13"
    FS_SECTION = "9"
    FS_BODY    = "8"
    FS_DETAIL  = "7.5"

    NODE = {
        "shape":    "none",
        "margin":   "0",
        "fontname": FONT_FAMILY,
    }
    GRAPH = {
        **GRAPH_DEFAULTS,
        "rankdir":  "TB",
        "splines":  "line",
        "pad":      "0.5",
        "nodesep":  "0",
        "ranksep":  "0",
    }