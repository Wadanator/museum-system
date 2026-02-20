# MQTT topics – návrhy / historické poznámky

Tento súbor ostáva ako **historický záznam nápadov**. Nie je kanonický.

## Kanonický dokument
Používaj vždy:
- `docs/mqtt_topics.md`

## Prečo je tento súbor oddelený

V minulosti tu boli návrhy topicov pre:
- `system/*` globálne commandy,
- rôzne display/sensor patterns,
- širšie naming konvencie mimo aktuálneho firmvéru.

Tieto návrhy sú užitočné pri plánovaní, ale nie všetky sú implementované.
Aby nevznikol konflikt medzi „plánom“ a „realitou“, presná implementovaná verzia je len v `docs/mqtt_topics.md`.

## Ako používať tento súbor

- Môžeš sem zapisovať brainstorming nápady.
- Pred implementáciou ich vždy over vo firmware/backend kóde.
- Po implementácii presuň výsledok do kanonického dokumentu.
