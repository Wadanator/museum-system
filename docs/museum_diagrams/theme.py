"""
theme.py
--------
Centralised Graphviz style configuration.
Candy / highlighter palette — soft, cheerful, prints cleanly in greyscale.

Colour hierarchy (for Museum Automation System diagrams):
  Scene (mint)
    └── State (sky blue)
          ├── onEnter    → mint
          ├── timeline   → lavender
          ├── onExit     → peach
          └── transitions→ lemon

Generic classes available for any diagram type:
  Flowchart     — process flows, algorithms
  StateMachine  — state transition diagrams
  Architecture  — hardware/network topology
  Software      — classes, interfaces, modules, services
  Pipeline      — data/media flow, queues, workers
  JSON          — nested config/data structure trees
  SceneAnatomy  — HTML-label block: Scene-level (mint)
  StateAnatomy  — HTML-label block: State-level (sky blue)
"""

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_FAMILY      = "Helvetica"
FONT_SIZE_NORMAL = "10"
FONT_SIZE_SMALL  = "8"
FONT_SIZE_LARGE  = "11"

# ---------------------------------------------------------------------------
# 🍬 Candy palette — raw tokens
# ---------------------------------------------------------------------------

# MINT — Scene-level, onEnter, "active / alive"
MINT_DEEP   = "#3AAF80"
MINT_MID    = "#7DD4B0"
MINT_LIGHT  = "#C8F5E8"
MINT_PALE   = "#EDFAF3"
MINT_RULE   = "#A8E8CC"
MINT_TEXT   = "#0E3325"

# SKY BLUE — State-level, subprocess, "logic / detail"
SKY_DEEP    = "#4A9FD4"
SKY_MID     = "#7BBCE8"
SKY_LIGHT   = "#D0EEFF"
SKY_PALE    = "#EDF5FF"
SKY_RULE    = "#B0D8F5"
SKY_TEXT    = "#0E2535"

# LAVENDER — timeline, interface, "sequence / contract"
LAV_DEEP    = "#8B6FCC"
LAV_MID     = "#B09EE0"
LAV_LIGHT   = "#EAE4FF"
LAV_PALE    = "#F5F2FF"
LAV_RULE    = "#CCC4F0"

# PEACH — onExit, I/O, data transfer, "communication"
PEACH_DEEP  = "#E07A50"
PEACH_MID   = "#F0A882"
PEACH_LIGHT = "#FFE8D8"
PEACH_PALE  = "#FFF4EE"
PEACH_RULE  = "#F5C8AA"

# LEMON — transitions, decisions, warnings, "attention"
LEM_DEEP    = "#C8A000"
LEM_MID     = "#E0C840"
LEM_LIGHT   = "#FFF8C0"
LEM_PALE    = "#FFFDE8"
LEM_RULE    = "#F0DC80"

# ROSE — events, errors, end states, "external impulse"
ROSE_DEEP   = "#D4609A"
ROSE_MID    = "#E898C0"
ROSE_LIGHT  = "#FFD6E8"
ROSE_PALE   = "#FFF0F7"

# NEUTRALS
NEUTRAL_WHITE  = "#FFFFFF"
NEUTRAL_CLOUD  = "#F8F8FC"
NEUTRAL_BORDER = "#C8C8DC"
NEUTRAL_TEXT   = "#1A1A2E"
NEUTRAL_MUTED  = "#7A7A9A"
NEUTRAL_DIV    = "#E0E0F0"
NEUTRAL_LIGHT  = "#EBEBF5"

# ---------------------------------------------------------------------------
# Global defaults
# ---------------------------------------------------------------------------
GRAPH_DEFAULTS = {
    "dpi":      "300",
    "rankdir":  "TB",
    "splines":  "ortho",
    "nodesep":  "0.55",
    "ranksep":  "0.65",
    "pad":      "0.4",
    "fontname": FONT_FAMILY,
    "fontsize": FONT_SIZE_NORMAL,
    "label":    "",
    "bgcolor":  NEUTRAL_CLOUD,
}

NODE_DEFAULTS = {
    "fontname":  FONT_FAMILY,
    "fontsize":  FONT_SIZE_NORMAL,
    "style":     "filled",
    "fillcolor": NEUTRAL_WHITE,
    "color":     NEUTRAL_BORDER,
    "penwidth":  "1.5",
}

EDGE_DEFAULTS = {
    "fontname":  FONT_FAMILY,
    "fontsize":  FONT_SIZE_SMALL,
    "color":     NEUTRAL_MUTED,
    "penwidth":  "1.2",
    "arrowsize": "0.8",
}


# ===========================================================================
# 1. FLOWCHART
#    Use for: algorithms, process flows, decision trees, "what happens when X"
#
#    Shape guide:
#      TERMINAL   — start / end                       (lavender, oval)
#      PROCESS    — action / step                     (mint, rounded rect)
#      DECISION   — yes/no branch                     (lemon, diamond)
#      IO         — input / output / data transfer    (peach, parallelogram)
#      SUBPROCESS — call to another process/function  (sky, double-border rect)
#      EVENT      — external trigger / interrupt      (rose, rounded rect)
#      NOTE       — annotation / comment              (lemon, note shape)
# ===========================================================================
class Flowchart:
    TERMINAL = {
        **NODE_DEFAULTS,
        "shape": "oval", "style": "filled,bold",
        "fillcolor": LAV_LIGHT, "color": LAV_DEEP, "penwidth": "2.2",
    }
    PROCESS = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": MINT_LIGHT, "color": MINT_DEEP, "penwidth": "1.8",
    }
    DECISION = {
        **NODE_DEFAULTS,
        "shape": "diamond",
        "fillcolor": LEM_LIGHT, "color": LEM_DEEP, "penwidth": "1.8",
        "fontsize": FONT_SIZE_SMALL,
    }
    IO = {
        **NODE_DEFAULTS,
        "shape": "parallelogram",
        "fillcolor": PEACH_LIGHT, "color": PEACH_DEEP, "penwidth": "1.8",
    }
    SUBPROCESS = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled",
        "fillcolor": SKY_LIGHT, "color": SKY_DEEP,
        "penwidth": "1.8", "peripheries": "2",
    }
    EVENT = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": ROSE_LIGHT, "color": ROSE_DEEP, "penwidth": "1.8",
    }
    NOTE = {
        **NODE_DEFAULTS,
        "shape": "note",
        "fillcolor": LEM_PALE, "color": LEM_MID, "penwidth": "1.2",
        "fontsize": FONT_SIZE_SMALL,
    }

    FLOW   = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": SKY_DEEP}
    BRANCH = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": PEACH_DEEP,
              "fontsize": FONT_SIZE_SMALL}
    DASHED = {**EDGE_DEFAULTS, "arrowhead": "vee", "style": "dashed",
              "color": NEUTRAL_MUTED}

    # LR = left→right, stays wide and low — fits under text on A4
    # size = max bounding box in inches (A4 usable width ~7.5in, low height)
    GRAPH = {
        **GRAPH_DEFAULTS,
        "rankdir":  "LR",
        "splines":  "ortho",
        "nodesep":  "0.4",
        "ranksep":  "0.6",
        "pad":      "0.3",
        "size":     "7.5,2.8",   # max width x height in inches — tweak per diagram
        "ratio":    "compress",   # compress into size box without distorting nodes
    }


# ===========================================================================
# 2. STATE MACHINE
#    Use for: JSON state machines, UI state, connection lifecycle
#
#    Shape guide:
#      INITIAL  — filled dot, entry point
#      NORMAL   — regular state
#      ACTIVE   — highlighted / current state
#      END      — double circle, terminal state
# ===========================================================================
class StateMachine:
    INITIAL = {
        **NODE_DEFAULTS,
        "shape": "circle",
        "width": "0.25", "height": "0.25",
        "fillcolor": LAV_DEEP, "color": LAV_DEEP, "penwidth": "0",
    }
    NORMAL = {
        **NODE_DEFAULTS,
        "shape": "rectangle",
        "fillcolor": SKY_LIGHT, "color": SKY_MID, "penwidth": "1.5",
    }
    ACTIVE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,bold",
        "fillcolor": SKY_LIGHT, "color": SKY_DEEP, "penwidth": "2.4",
    }
    END = {
        **NODE_DEFAULTS,
        "shape": "doublecircle", "width": "0.4", "height": "0.4",
        "fillcolor": ROSE_LIGHT, "color": ROSE_DEEP, "penwidth": "2.0",
    }

    TRANSITION         = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": SKY_DEEP}
    TRANSITION_TIMEOUT = {**EDGE_DEFAULTS, "arrowhead": "vee",
                          "style": "dashed", "color": LAV_DEEP}
    SELF_LOOP          = {**EDGE_DEFAULTS, "arrowhead": "vee",
                          "style": "dotted", "color": NEUTRAL_MUTED}

    GRAPH = {**GRAPH_DEFAULTS,
             "rankdir":  "LR",
             "splines":  "ortho",
             "nodesep":  "0.5",
             "ranksep":  "0.8",
             "pad":      "0.4",
             "size":     "7.5,3.0",
             "ratio":    "compress"}


# ===========================================================================
# 3. ARCHITECTURE — hardware / network topology
#    Use for: RPI ↔ ESP32 ↔ MQTT broker, physical deployment, device map
#
#    Shape guide:
#      MASTER    — main controller (RPI, server)       (mint, bold)
#      DEVICE    — embedded / peripheral (ESP32, cam)  (sky)
#      BROKER    — message broker / hub                (peach, oval)
#      DASHBOARD — UI / monitoring surface             (lavender, rounded)
#      SERVICE   — OS service / daemon                 (lemon, rounded)
#      EXTERNAL  — outside system boundary             (neutral, dashed)
#      MODULE    — generic unlabelled component        (white)
# ===========================================================================
class Architecture:
    MASTER = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,bold",
        "fillcolor": MINT_LIGHT, "color": MINT_DEEP,
        "penwidth": "2.5", "fontsize": FONT_SIZE_LARGE,
    }
    DEVICE = {
        **NODE_DEFAULTS,
        "shape": "rectangle",
        "fillcolor": SKY_LIGHT, "color": SKY_MID, "penwidth": "1.8",
    }
    BROKER = {
        **NODE_DEFAULTS,
        "shape": "oval",
        "fillcolor": PEACH_LIGHT, "color": PEACH_DEEP, "penwidth": "2.0",
    }
    DASHBOARD = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": LAV_LIGHT, "color": LAV_MID, "penwidth": "1.8",
    }
    SERVICE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": LEM_LIGHT, "color": LEM_DEEP, "penwidth": "1.8",
    }
    EXTERNAL = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,dashed",
        "fillcolor": NEUTRAL_CLOUD, "color": NEUTRAL_BORDER,
        "penwidth": "1.2", "fontsize": FONT_SIZE_SMALL,
    }
    MODULE = {
        **NODE_DEFAULTS,
        "shape": "rectangle",
        "fillcolor": NEUTRAL_WHITE, "color": NEUTRAL_BORDER,
    }

    MQTT          = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": SKY_DEEP}
    MQTT_LABELLED = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": SKY_DEEP,
                     "fontsize": FONT_SIZE_SMALL}
    SOCKET_IO     = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": LAV_DEEP,
                     "style": "dashed"}
    HTTP          = {**EDGE_DEFAULTS, "arrowhead": "normal", "color": PEACH_DEEP}
    LINK          = {**EDGE_DEFAULTS, "arrowhead": "normal", "arrowtail": "normal",
                     "dir": "both", "style": "dashed", "color": NEUTRAL_MUTED}
    WIRE          = {**EDGE_DEFAULTS, "arrowhead": "none",
                     "color": NEUTRAL_TEXT, "penwidth": "2.0"}

    GRAPH = {**GRAPH_DEFAULTS,
             "rankdir":  "LR",
             "splines":  "ortho",
             "nodesep":  "0.5",
             "ranksep":  "0.8",
             "pad":      "0.4",
             "size":     "7.5,3.5",
             "ratio":    "compress"}


# ===========================================================================
# 4. SOFTWARE — code structure
#    Use for: class diagrams, module dependency, internal architecture of a
#             service, function call graphs
#
#    Shape guide:
#      CLASS      — concrete class                     (sky, rect)
#      ABSTRACT   — abstract class                     (sky, dashed border)
#      INTERFACE  — interface / protocol               (lavender)
#      MODULE     — file / package / namespace         (mint, bold)
#      FUNCTION   — standalone function                (mint, rounded)
#      DATABASE   — persistent store / file            (peach, cylinder)
#      CONSTANT   — config / env value                 (lemon, note)
#      EXTERNAL   — third-party lib / OS call          (neutral, dashed)
# ===========================================================================
class Software:
    CLASS = {
        **NODE_DEFAULTS,
        "shape": "rectangle",
        "fillcolor": SKY_LIGHT, "color": SKY_DEEP, "penwidth": "1.8",
    }
    ABSTRACT = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,dashed",
        "fillcolor": SKY_PALE, "color": SKY_MID, "penwidth": "1.8",
    }
    INTERFACE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": LAV_LIGHT, "color": LAV_DEEP, "penwidth": "1.8",
    }
    MODULE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,bold",
        "fillcolor": MINT_LIGHT, "color": MINT_DEEP, "penwidth": "2.2",
    }
    FUNCTION = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": MINT_PALE, "color": MINT_MID, "penwidth": "1.5",
    }
    DATABASE = {
        **NODE_DEFAULTS,
        "shape": "cylinder",
        "fillcolor": PEACH_LIGHT, "color": PEACH_DEEP, "penwidth": "1.8",
    }
    CONSTANT = {
        **NODE_DEFAULTS,
        "shape": "note",
        "fillcolor": LEM_PALE, "color": LEM_MID, "penwidth": "1.2",
        "fontsize": FONT_SIZE_SMALL,
    }
    EXTERNAL = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,dashed",
        "fillcolor": NEUTRAL_CLOUD, "color": NEUTRAL_BORDER,
        "penwidth": "1.2", "fontsize": FONT_SIZE_SMALL,
    }

    INHERITS   = {**EDGE_DEFAULTS, "arrowhead": "empty",
                  "color": SKY_DEEP, "penwidth": "1.5"}
    IMPLEMENTS = {**EDGE_DEFAULTS, "arrowhead": "empty",
                  "style": "dashed", "color": LAV_DEEP, "penwidth": "1.5"}
    USES       = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": NEUTRAL_MUTED}
    CALLS      = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": MINT_DEEP}
    OWNS       = {**EDGE_DEFAULTS, "arrowhead": "diamond",
                  "color": SKY_DEEP, "penwidth": "1.6"}

    GRAPH = {
        **GRAPH_DEFAULTS,
        "rankdir":  "LR",
        "splines":  "ortho",
        "nodesep":  "0.5",
        "ranksep":  "0.7",
        "pad":      "0.4",
        "size":     "7.5,3.5",
        "ratio":    "compress",
    }


# ===========================================================================
# 5. PIPELINE — data / media / message flow
#    Use for: video playback pipeline, MQTT message routing, event processing,
#             worker queues, IPC between processes
#
#    Shape guide:
#      SOURCE    — origin of data / trigger            (mint, bold)
#      PROCESS   — transformation / worker step        (sky, rounded)
#      QUEUE     — buffer / message queue / topic      (lemon, rect)
#      SINK      — final consumer / output             (peach)
#      SERVICE   — OS-level service / daemon           (lavender, rounded)
#      STORE     — file / DB / persistent output       (peach, cylinder)
#      ERROR     — error handler / dead-letter         (rose)
# ===========================================================================
class Pipeline:
    SOURCE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,bold",
        "fillcolor": MINT_LIGHT, "color": MINT_DEEP, "penwidth": "2.2",
    }
    PROCESS = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": SKY_LIGHT, "color": SKY_DEEP, "penwidth": "1.8",
    }
    QUEUE = {
        **NODE_DEFAULTS,
        "shape": "rectangle",
        "fillcolor": LEM_LIGHT, "color": LEM_DEEP, "penwidth": "1.8",
    }
    SINK = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": PEACH_LIGHT, "color": PEACH_DEEP, "penwidth": "1.8",
    }
    SERVICE = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": LAV_LIGHT, "color": LAV_DEEP, "penwidth": "1.8",
    }
    STORE = {
        **NODE_DEFAULTS,
        "shape": "cylinder",
        "fillcolor": PEACH_PALE, "color": PEACH_MID, "penwidth": "1.8",
    }
    ERROR = {
        **NODE_DEFAULTS,
        "shape": "rectangle", "style": "filled,rounded",
        "fillcolor": ROSE_LIGHT, "color": ROSE_DEEP, "penwidth": "1.8",
    }

    FLOW      = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": SKY_DEEP}
    ASYNC     = {**EDGE_DEFAULTS, "arrowhead": "vee",
                 "style": "dashed", "color": LAV_DEEP}
    PUBLISH   = {**EDGE_DEFAULTS, "arrowhead": "vee", "color": MINT_DEEP}
    SUBSCRIBE = {**EDGE_DEFAULTS, "arrowhead": "vee",
                 "style": "dashed", "color": MINT_MID}
    ERROR_EDGE= {**EDGE_DEFAULTS, "arrowhead": "vee",
                 "color": ROSE_DEEP, "style": "dashed"}

    # LR = wide and low, fits as inline figure in A4 document
    GRAPH = {
        **GRAPH_DEFAULTS,
        "rankdir":  "LR",
        "splines":  "ortho",
        "nodesep":  "0.4",
        "ranksep":  "0.6",
        "pad":      "0.3",
        "size":     "7.5,2.8",
        "ratio":    "compress",
    }


# ===========================================================================
# 6. JSON STRUCTURE — nested config / data trees
#    Use for: visualising JSON schema, config file structure
# ===========================================================================
class JSON:
    ROOT = {
        **NODE_DEFAULTS,
        "shape": "record", "style": "filled,bold",
        "fillcolor": MINT_LIGHT, "color": MINT_DEEP, "penwidth": "2.2",
    }
    OBJECT = {
        **NODE_DEFAULTS,
        "shape": "record",
        "fillcolor": SKY_LIGHT, "color": SKY_MID,
        "penwidth": "1.5", "fontsize": FONT_SIZE_SMALL,
    }
    ARRAY = {
        **NODE_DEFAULTS,
        "shape": "record", "style": "filled,dashed",
        "fillcolor": MINT_LIGHT, "color": MINT_MID,
        "penwidth": "1.5", "fontsize": FONT_SIZE_SMALL,
    }
    VALUE = {
        **NODE_DEFAULTS,
        "shape": "plaintext", "fillcolor": NEUTRAL_WHITE,
        "fontsize": FONT_SIZE_SMALL,
    }
    CONTAINS  = {**EDGE_DEFAULTS, "arrowhead": "odot", "color": LAV_DEEP}
    REFERENCE = {**EDGE_DEFAULTS, "arrowhead": "open",
                 "style": "dashed", "color": NEUTRAL_MUTED}


# ===========================================================================
# 7. STATE ANATOMY — HTML-label block, sky-blue family (child of Scene)
#    Use for: reference diagram of a single State object
# ===========================================================================
class StateAnatomy:
    BG_STATE   = SKY_PALE
    BG_HEADER  = SKY_DEEP
    BG_SECTION = SKY_LIGHT
    BG_ITEM    = NEUTRAL_WHITE
    C_BORDER   = SKY_MID
    C_DIVIDER  = SKY_RULE
    C_PRIMARY  = NEUTRAL_TEXT
    C_SECONDARY= SKY_DEEP
    C_MUTED    = "#5A88AA"

    # Per-section accent colours (header, bg, border, divider)
    SEC_ONENTER  = (MINT_DEEP,  MINT_LIGHT,  MINT_MID,  MINT_RULE)
    SEC_TIMELINE = (LAV_DEEP,   LAV_LIGHT,   LAV_MID,   LAV_RULE)
    SEC_ONEXIT   = (PEACH_DEEP, PEACH_LIGHT, PEACH_MID, PEACH_RULE)
    SEC_TRANS_HDR= LEM_DEEP
    SEC_TRANS_BG = LEM_LIGHT
    SEC_TRANS_BDR= LEM_MID

    ACT_MQTT  = "#2E7A40"
    ACT_AUDIO = "#6040B0"
    ACT_VIDEO = "#B05020"
    ACT_KV    = "#7A7A9A"

    TR_TIMEOUT = "#2060A0"
    TR_MQTT    = "#2E7A40"
    TR_VIDEO   = "#B05020"
    TR_ALWAYS  = "#8B6FCC"

    FS_TITLE   = "13"
    FS_SECTION = "9"
    FS_BODY    = "8"
    FS_DETAIL  = "7.5"

    NODE  = {"shape": "none", "margin": "0", "fontname": FONT_FAMILY}
    GRAPH = {**GRAPH_DEFAULTS, "rankdir": "TB", "splines": "line",
             "pad": "0.5", "nodesep": "0", "ranksep": "0"}


# ===========================================================================
# 8. SCENE ANATOMY — HTML-label block, mint-green family (parent of State)
#    Use for: reference diagram of the top-level Scene JSON object
# ===========================================================================
class SceneAnatomy:
    BG_STATE   = MINT_PALE
    BG_HEADER  = MINT_DEEP
    BG_SECTION = MINT_LIGHT
    BG_ITEM    = NEUTRAL_WHITE
    C_BORDER   = MINT_MID
    C_DIVIDER  = MINT_RULE
    C_PRIMARY  = NEUTRAL_TEXT
    C_SECONDARY= MINT_DEEP
    C_MUTED    = "#4A8A6A"

    SUB_GLOBAL_HDR = "#2E9A78"
    SUB_GLOBAL_BG  = "#D8F5EC"
    SUB_GLOBAL_BDR = MINT_MID

    SUB_STATES_HDR = SKY_DEEP
    SUB_STATES_BG  = "#E0F2FF"
    SUB_STATES_BDR = SKY_MID

    FS_TITLE   = "13"
    FS_SECTION = "9"
    FS_BODY    = "8"
    FS_DETAIL  = "7.5"

    NODE  = {"shape": "none", "margin": "0", "fontname": FONT_FAMILY}
    GRAPH = {**GRAPH_DEFAULTS, "rankdir": "TB", "splines": "line",
             "pad": "0.5", "nodesep": "0", "ranksep": "0"}