# museum-dashboard

Samostatný React/Vite dashboard frontend pre museum-system.

> Poznámka: Raspberry Pi backend aktuálne servuje produkčný dashboard z `raspberry_pi/Web/`.
> Tento projekt je vhodný na vývoj alebo refaktor UI mimo embedded backend runtime.

---

## 1) Spustenie

```bash
cd museum-dashboard
npm install
npm run dev
```

Build:
```bash
npm run build
```

---

## 2) Architektúra frontendu (stručne)

- `src/services/api.js` – REST volania
- `src/services/socket.js` – socket komunikácia
- `src/context/*` – Auth/Socket/Confirm kontexty
- `src/hooks/*` – hooks pre scenes, logs, devices, media, system actions
- `src/styles/*` – modulárne CSS vrstvy

---

## 3) Integrácia s backendom

Tento frontend očakáva API/socket endpointy kompatibilné s routes v `raspberry_pi/Web/routes/*`.
Pri zmene backend endpointov aktualizuj aj:
- `src/services/api.js`
- príslušné hooks

---

## 4) Typické použitie v tíme

- návrh a iterácia UI komponentov,
- oddelené testovanie dashboard správania,
- príprava zmien pred portovaním do `raspberry_pi/Web/` produkčnej verzie.
