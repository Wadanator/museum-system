# Museum Automation System — Diagram Generation Guide

## Základný princíp: Lievik

Každý nový obrázok má **jednu zodpovednosť**. Nejdeme do hĺbky, kým to nie je potrebné.

```
Celý JSON súbor
    └── Ako vyzerá jeden stav
            └── Čo sú akcie
                    └── Čo sú prechody
```

Každý diagram = jeden pohľad. Nie encyklopédia, nie celý systém naraz.

---

## Súborová štruktúra

```
museum_diagrams/
├── theme.py          ← farby, fonty, štýly  (NEMENIŤ bez dôvodu)
├── gv_html.py        ← znovupoužiteľné HTML-label helpery
├── render.py         ← export do SVG, auto-názov podľa skriptu
├── scene_schema.py   ← diagram: ako vyzerá celý JSON súbor
├── state_anatomy.py  ← diagram: ako vyzerá jeden stav
└── outputs/          ← všetky vygenerované SVG
```

Každý nový diagram = nový `.py` súbor. Názov súboru = názov výstupu.

---

## Ako vygenerovať nový diagram

### 1. Načítaj kontext
Vždy nahraj:
- `theme.py` — paleta a štýly
- `gv_html.py` — dostupné helpery

### 2. Povedz čo chceš zobraziť
Formuluj požiadavku jednou vetou. Príklady:

> *"Chcem diagram ktorý ukazuje ako vyzerá jeden prechod (Transition)."*

> *"Chcem diagram celého systému — Raspberry Pi, MQTT broker, ESP32 zariadenia."*

> *"Chcem diagram flow — čo sa deje keď príde MQTT správa."*

### 3. Urči úroveň detailu
Defaultne platí: **čo najmenej detailov, ktoré stále dávajú zmysel.**

| Situácia | Prístup |
|---|---|
| Prvý pohľad na tému | Iba názvy polí, žiadne hodnoty |
| Vysvetlenie štruktúry | Polia + typy + krátka poznámka |
| Referencia / cheat-sheet | Polia + typy + príklady hodnôt |

---

## Čo AI dostane a čo spraví

**Dostane:**
- `theme.py` + `gv_html.py` (kontext)
- Popis čo má zobraziť
- Prípadne JSON / schéma ako vstupné dáta

**Spraví:**
- Nový `.py` súbor ktorý importuje `theme`, `gv_html`, `render`
- Jeden blok / jeden pohľad
- Žiadne PDF, žiadne duplikáty kódu

---

## Pravidlá pre AI

```
- Jeden súbor = jeden diagram = jedna myšlienka
- Importuj z theme.py, gv_html.py, render.py — nepíš znova to čo už existuje
- Nepoužívaj farby natvrdo v skripte, len tokeny z theme.py (C1, C2, BGH, ...)
- Nechodíš do hĺbky pokiaľ to nie je explicitne požadované
- render_diagram(dot) na konci — bez argumentov, názov = názov súboru
```

---

## Dostupné helpery (gv_html.py)

| Funkcia | Použitie |
|---|---|
| `font(text, size, color, bold, italic)` | obalí text do `<FONT>` tagu |
| `thin_rule(colspan, color)` | 1px horizontálny oddeľovač |
| `spacer(colspan, height)` | prázdny riadok |
| `action_block(type, fields)` | blok jednej akcie (mqtt / audio / video) |
| `timeline_block(at, type, fields)` | blok jednej timeline položky |
| `section_column(header, *items)` | stĺpec so záhlavím (onEnter / timeline / onExit) |
| `transition_card(type, fields)` | karta jedného prechodu |

---

## Paleta (theme.py → StateAnatomy)

| Token | Použitie |
|---|---|
| `BGH` | záhlavie sekcie |
| `BGS` | pozadie sekcie |
| `BGI` | pozadie karty / položky |
| `BG` | celkové pozadie bloku |
| `C1` | hlavný text |
| `C2` | kľúče, typy |
| `C3` | hodnoty, poznámky (muted) |
| `CB` | border |
| `CD` | divider (tenká čiara) |
