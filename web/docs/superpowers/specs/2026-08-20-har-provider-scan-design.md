# HAR Provider Scan — Design

**Datum**: 2026-08-20
**Status**: Goedgekeurd, klaar voor implementatieplan

## Doel

Mensen moeten een HAR-bestand (geëxporteerd uit hun browser devtools) kunnen
uploaden en per aangeroepen hostname te zien krijgen welke leverancier
(organisatie) daarachter zit en waar die statutair gevestigd is — als
platte, feitelijke data, niet als samengestelde soevereiniteitsscore
(zie "Niet-doelen").

Aanleiding: `soevereinscan` (C:\dev\soevereinscan) doet dit al tijdens een
live scan van een URL, maar heeft geen manier om een reeds bestaand
HAR-bestand te analyseren. Een los, publiek beschikbaar tooltje voor dat
specifieke gebruiksdoel ontbreekt.

HAR-bestanden kunnen vertrouwelijke data bevatten (cookies, auth-headers,
tokens, POST-bodies, query strings met sessie-informatie). Sanitizen vóór
verwerking is daarom een hard vereiste, niet een nice-to-have.

## Niet-doelen

- Geen samengestelde jurisdictie-/soevereiniteitsscore (0-4, zoals
  `soevereinscan`'s `classify_jurisdiction`). De interpretatie van
  SEAL-niveaus is omstreden (bijv. is een geval niveau 2 of 3) — dit tool
  toont alleen de onderliggende feiten, geen oordeel.
- Geen fysiek serverland (GeoIP/MaxMind). Alleen de statutaire zetel van
  de netwerkeigenaar zoals geregistreerd in PeeringDB.
- Geen opslag van scanresultaten of geüploade HAR's. Volledig ephemeral.
- Geen hergebruik van de `soevereinscan`-database, -deployment of
  -codebase. Twee nieuwe, losstaande repositories.

## Architectuur — twee ontkoppelde componenten

```
Browser                          har-provider-lookup (serverless)
┌─────────────────────┐          ┌──────────────────────────────┐
│ har-scan-web         │  fetch   │ POST /lookup                 │
│ (GitHub Pages,       │ ───────► │  hostname → DNS → IP          │
│  statisch)            │          │  IP → RIPEstat network-info   │
│                       │ ◄─────── │       → ASN                  │
│ 1. HAR parsen         │  JSON    │  ASN → PeeringDB /net + /org  │
│ 2. Whitelist-extractie│          │       → leverancier + land   │
│ 3. Tabel renderen     │          │  (7-dagen cache, geen opslag) │
└─────────────────────┘          └──────────────────────────────┘
```

### 1. `har-scan-web` — statische front-end (GitHub Pages)

- TypeScript (`strict: true`), ESM, Vite-build (geen `any`, conform
  organisatiebrede coderichtlijnen). Output is statische HTML/CSS/JS,
  gepubliceerd via een GitHub Actions-workflow naar GitHub Pages.
- Gebruiker sleept een `.har`-bestand in de pagina (drag&drop of
  file-picker). Alles gebeurt client-side:
  1. Bestand lezen als tekst, `JSON.parse`.
  2. Itereren over `log.entries`. Voor elke entry: `new URL(entry.request.url).hostname`
     extraheren en tellen. Voor de graafstructuur: `Referer`-header
     opzoeken, ook daarvan alleen het hostname-deel via `new URL(...)`.
  3. Alle overige velden (headers, cookies, query strings, request/response
     bodies, timings, `postData`, screenshots) worden nergens in een
     variabele buiten de parse-loop opgeslagen — ze worden simpelweg nooit
     gelezen buiten de velden genoemd in stap 2.
  4. Resultaat: `{ hostnames: [{ host: string, count: number }], edges: [{ parent: string, child: string }] }`.
- Bestandsgroottelimiet client-side: 50 MB (HAR's kunnen tientallen MB's
  zijn, zoals het voorbeeldbestand van 22 MB dat tot deze feature leidde).
  Boven de limiet: duidelijke Nederlandse foutmelding, niets verwerkt.
- Na parsen: `fetch()` naar de `har-provider-lookup`-microservice met de
  sanitized payload. Resultaat wordt gerenderd als platte tabel:

  | Hostname | Leverancier | Statutaire zetel | Aantal requests | EU? |
  |---|---|---|---|---|
  | cdn.bluedolphin.app | Microsoft Azure Front Door | IE / NL / ... | 8 | ✓ |

  De EU-badge is een simpele lookup tegen dezelfde `EU_COUNTRIES`-lijst
  als `soevereinscan`'s `classifier.py` — puur visuele hint, geen score.
- Foutafhandeling per hostname: als de microservice voor een hostname
  geen resultaat kan geven (DNS-fail, RIPEstat/PeeringDB down of
  rate-limited, of organisatie onbekend in PeeringDB), toont de rij
  "onbekend" in plaats van de hele tabel te laten falen.

### 2. `har-provider-lookup` — stateless microservice

- Python 3.12+, FastAPI, geen database, geen Redis-hard-dependency (een
  optionele in-memory of Redis-cache mag, zelfde 7-dagen-cache-patroon
  als `soevereinscan/app/services/peeringdb.py` en `ripestat.py`, puur
  om PeeringDB/RIPEstat niet te overvragen — dit is een harde eis uit
  de CFT-werkwijze ["Geen API-misbruik"]).
- Eén endpoint: `POST /lookup` — body: `{"hostnames": ["a.example.com", ...]}`
  (max 200 hostnames per request, afgedwongen met een Pydantic/Zod-achtige
  validatie — voorkomt misbruik als DNS/RIPEstat/PeeringDB-proxy).
- Per hostname, sequentieel per stap maar hostnames parallel (asyncio):
  1. DNS-resolve → IP('s). Faalt de resolve, dan hostname → `null`-resultaat.
  2. RIPEstat `https://stat.ripe.net/data/network-info/data.json?resource={ip}`
     → ASN. (Vervangt de lokale MaxMind-ASN-database die `soevereinscan`
     gebruikt — geen licentiegebonden binair bestand nodig in deze
     microservice.)
  3. PeeringDB `/api/net?asn={asn}` → org_id, org_name (leverancier).
  4. PeeringDB `/api/org/{org_id}` → country (statutaire zetel).
- Response: `{"results": [{"hostname": ..., "org_name": ..., "org_country": ..., "asn": ...}]}`.
- CORS: alleen de `har-scan-web`-Pages-origin toegestaan (geen wildcard).
- Config volledig via env vars (12-factor): `ALLOWED_ORIGIN`,
  `PEERINGDB_API_KEY` (optioneel), `REDIS_URL` (optioneel), `PORT`.
- `GET /healthz` (liveness) en `GET /readyz` (readiness — check of
  RIPEstat/PeeringDB bereikbaar zijn) conform de portability-regels.
- Dockerfile: multi-stage, non-root (`USER 1001`), `HEALTHCHECK`,
  gepind base-image-digest, `.dockerignore`. Gehost op een serverless
  platform (Fly.io of Render — definitieve keuze bij implementatie,
  beide draaien een Dockerfile).

## Data flow (samengevat)

1. Gebruiker opent `har-scan-web` in browser.
2. Sleept `.har`-bestand in de pagina. Bestand verlaat nooit de browser
   in ruwe vorm.
3. Client parseert + sanitiseert → klein JSON-object met alleen
   hostnamen, tellingen en referer-graaf.
4. `fetch POST` naar `har-provider-lookup` met dat JSON-object.
5. Microservice doet DNS → RIPEstat → PeeringDB per hostname, retourneert
   platte resultaten. Niets wordt server-side opgeslagen.
6. Front-end rendert tabel + eenvoudige boomweergave (optioneel, o.b.v.
   `edges`) client-side. Geen PDF, geen e-mail, geen deelbare link
   (ephemeral, zoals afgesproken).

## Sanitisatie — expliciete whitelist

**Wel gebruikt / verzonden**:
- Hostname uit `request.url`.
- Hostname uit `Referer`-responseheader (voor de graafstructuur).
- Aantal requests per hostname.

**Nooit gebruikt / verzonden** (expliciete denylist als extra
verificatielaag bovenop de whitelist-aanpak):
- Query strings, paden, fragment-identifiers.
- Alle request- en response-headers behalve `Referer` (dus geen
  `Authorization`, `Cookie`, `Set-Cookie`, custom API-keys, etc.) — en
  van `Referer` wordt alleen `hostname` overgenomen, nooit de volledige
  waarde.
- `postData` / request-bodies, response-bodies.
- Timings, `serverIPAddress`, `connection`, cache-informatie.
- Eventuele ingesloten screenshots/base64-content (sommige HAR-varianten
  bevatten die niet standaard, maar voor de zekerheid genegeerd).

## Error handling

- Ongeldig/corrupt JSON in het HAR-bestand: front-end toont
  "Kon HAR-bestand niet lezen — is dit een geldig HAR-exportbestand?",
  niets wordt verzonden.
- HAR zonder `log.entries`: zelfde foutmelding, specifieker
  ("Geen requests gevonden in dit bestand").
- Microservice onbereikbaar: front-end toont een retry-melding, geen
  halve resultaten.
- Individuele hostname-lookup faalt (DNS/RIPEstat/PeeringDB): die rij
  toont "onbekend", de rest van de tabel blijft gewoon zichtbaar
  (graceful degradation per hostname, zelfde patroon als bestaande
  `soevereinscan`-services die `None` retourneren bij API-falen).

## Testing

- **Front-end (`har-scan-web`)**: Vitest-unit tests voor de
  parser/sanitizer met een bewust "vervuild" test-HAR-fixture (bevat
  cookies, `Authorization`-headers, query strings met een nep-token) —
  assert dat de payload naar de microservice nooit iets anders bevat dan
  hostnamen/tellingen/edges. Dit is de belangrijkste test in de hele
  spec, gezien het vertrouwelijkheidsvereiste.
- **Microservice (`har-provider-lookup`)**: pytest, HTTP-calls naar
  DNS/RIPEstat/PeeringDB gemockt (`respx` of vergelijkbaar). Testen voor:
  happy path, ASN niet gevonden, org niet gevonden, rate-limit/5xx van
  PeeringDB, meer dan 200 hostnames in één request (moet 400 geven).
- **E2E**: Playwright-test in `har-scan-web` die een voorbeeld-HAR
  uploadt tegen een lokaal draaiende `har-provider-lookup`-instantie
  (docker compose voor lokale ontwikkeling) en controleert dat de tabel
  correct rendert. Conform de E2E-regel uit CLAUDE.md wordt deze
  infrastructuur bij implementatie ook echt opgestart en de test
  daadwerkelijk groen gedraaid, niet alleen beweerd.

## Licenties & compliance (verplicht per repo)

- Beide repo's: EUPL-1.2 `LICENSE`-bestand.
- Beide repo's: README met dependency-licentietabel, bijgewerkt zodra
  dependencies wijzigen.
- Geen `Co-Authored-By`-regels voor AI-modellen in commits.
- `har-provider-lookup`: Haven-compliant Helm-chart is hier niet van
  toepassing (serverless hosting buiten Kubernetes) — expliciet
  uitgezonderd van de Haven-eis, wél 12-factor/Dockerfile-eisen.

## Open punten voor implementatiefase

- Definitieve keuze Fly.io vs. Render voor de microservice-hosting.
- Domeinnaam voor `har-scan-web` (custom domain op GitHub Pages of
  `<org>.github.io/har-scan-web`).
- PeeringDB API-key: wel/niet gebruiken (verhoogt rate-limits, vereist
  account/secret-beheer).
