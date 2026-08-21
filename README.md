# whereismydata

Twee samenwerkende projecten die samen laten zien welke leveranciers en
landen erachter schuilgaan als je een HAR-bestand (browser-netwerkcapture)
uploadt — zonder dat het bestand zelf ooit je browser verlaat.

- **[web](web)** — de statische, client-side front-end. Sanitiseert een
  geüpload HAR-bestand volledig lokaal in de browser tot een kale lijst
  hostnamen (whitelist-extractie: alleen `request.url` en de
  `Referer`-header, nooit cookies, auth-headers, bodies of query
  strings). Gedeployed via Vercel.
- **[api](api)** — de stateless lookup-backend (FastAPI/Python). Zoekt
  per hostname de netwerkeigenaar (leverancier) en diens statutaire
  zetel op via DNS → RIPEstat → PeeringDB. Geen database, geen
  opgeslagen resultaten, rate-limited per IP-adres.

## Ontwikkelen

Beide projecten hebben hun eigen README met installatie-instructies:
[web/README.md](web/README.md) en [api/README.md](api/README.md).

Voor de end-to-end-tests van `web` moet `api` lokaal draaien (via Docker
Compose) — zie [web/README.md](web/README.md#testen).

## CI

Elk project heeft zijn eigen workflow in [.github/workflows](.github/workflows),
die alleen triggert op wijzigingen binnen de eigen submap
(`ci-web.yml` op `web/**`, `ci-api.yml` op `api/**`).

## Geschiedenis

`web` en `api` waren oorspronkelijk twee losse repositories; deze repo
voegt ze samen met behoud van hun volledige commit-geschiedenis (via
`git subtree`). De ontwerp- en implementatiedocumenten uit die periode
staan nog in `web/docs/superpowers/` en `api/docs/superpowers/`.

## License

EUPL-1.2 — zie [LICENSE](LICENSE).
