"""
system_topology.py
------------------
Fyzická hviezdicová topológia riadiaceho systému CHRONOS.
Output: outputs/system_topology.svg
"""

import graphviz
from theme import Architecture as Arch
from render import render_diagram


def build():
    dot = graphviz.Digraph(name="system_topology")

    dot.attr("graph",
             rankdir="TB",
             splines="ortho",
             nodesep="1.2",
             ranksep="1.0",
             size="7.5,5.0",
             ratio="compress",
             pad="0.5",
             bgcolor="#F8F8FC",
             fontname="Helvetica",
             fontsize="10")

    # ── Cluster: Raspberry Pi ─────────────────────────────────────────────
    with dot.subgraph(name="cluster_rpi") as c:
        c.attr(
            label="Raspberry Pi",
            style="filled,rounded",
            fillcolor="#C8F5E8",
            color="#3AAF80",
            penwidth="2.5",
            fontname="Helvetica",
            fontsize="11",
            fontcolor="#0E3325",
            margin="20",
        )
        c.node("rpi",
               "Centrálna\nriadiaca jednotka",
               **Arch.MASTER)
        c.node("broker",
               "MQTT Broker",
               **Arch.BROKER)
        c.node("dashboard",
               "Webový dashboard",
               **Arch.DASHBOARD)

    # ── Externý klient ────────────────────────────────────────────────────
    dot.node("browser",
             "Obsluha múzea",
             **Arch.EXTERNAL)

    # ── Tri ESP32 uzly — explicitne na rovnakom ranku ─────────────────────
    with dot.subgraph() as s:
        s.attr(rank="same")
        s.node("esp_relay", "ESP32\nReléový uzol",    **Arch.DEVICE)
        s.node("esp_motor", "ESP32\nMotorický uzol",  **Arch.DEVICE)
        s.node("esp_input", "ESP32\nTlačidlový uzol", **Arch.DEVICE)

    # Obsluha múzea na rovnakom ranku ako ESP32 uzly
    with dot.subgraph() as s2:
        s2.attr(rank="same")
        s2.node("esp_relay")
        s2.node("esp_motor")
        s2.node("esp_input")
        s2.node("browser")

    # ── Hrany vnútri RPi ──────────────────────────────────────────────────
    dot.edge("rpi",       "broker",    **Arch.WIRE)
    dot.edge("rpi",       "dashboard", **Arch.WIRE)

    # Dashboard ↔ Obsluha (obojsmerné) — opravený label
    dot.edge("dashboard", "browser",
             label="  Socket.IO / HTTP",
             dir="both",
             **Arch.SOCKET_IO)

    # Broker ↔ ESP32 (Wi-Fi / MQTT, obojsmerné)
    dot.edge("broker", "esp_relay",
             label="  Wi-Fi / MQTT", dir="both", **Arch.MQTT_LABELLED)
    dot.edge("broker", "esp_motor",
             label="  Wi-Fi / MQTT", dir="both", **Arch.MQTT_LABELLED)
    dot.edge("broker", "esp_input",
             label="  Wi-Fi / MQTT", dir="both", **Arch.MQTT_LABELLED)

    render_diagram(dot)


if __name__ == "__main__":
    build()