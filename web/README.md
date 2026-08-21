# har-scan-web

Statische, client-side webpagina waar je een HAR-bestand kunt uploaden om
te zien welke leveranciers en landen erachter schuilgaan — zonder dat het
bestand ooit in ruwe vorm je browser verlaat.

Sanitizing gebeurt volledig lokaal: alleen hostnamen (en hoe vaak ze
worden aangeroepen) worden naar de lookup-backend ([api](../api))
gestuurd. Cookies, auth-headers, request/response-bodies en query
strings worden nooit gelezen buiten het moment van hostname-extractie —
met twee gerichte uitzonderingen, beide puur lokaal, nooit verstuurd:

- **Aantal Set-Cookie-headers per hostname** (alleen de headernaam wordt
  gecontroleerd, nooit de cookiewaarde zelf).
- **Browserextensie-ID's** (`chrome-extension://`/`moz-extension://`)
  worden apart getoond, nooit naar de lookup-backend gestuurd — een
  extensie-ID heeft toch geen zinnige PeeringDB/RIPEstat-match.

Daarnaast toont de pagina de referer-gebaseerde aanroepvolgorde (bijv. om
te zien dat een authenticatie-redirect vóór de doel-webapp kwam) en
markeert hostnamen die overeenkomen met bekende tracking-domeinpatronen
(puur op basis van de al-geëxtraheerde hostname, geen extra HAR-velden).

## Ontwikkelen

```bash
npm install
cp .env.example .env
npm run dev
```

Vereist een lokaal draaiende [api](../api) op de URL uit
`VITE_LOOKUP_API_URL` (standaard `http://localhost:8080`) — zie de
README daarvan.

## Testen

```bash
npm test              # unit tests (Vitest)
npm run check          # lint + format (Biome)
npm run e2e             # end-to-end (Playwright, start ../api automatisch via Docker Compose)
```

## Bouwen

```bash
npm run build
```

Output in `dist/`. Deployment loopt via Vercel (auto-deploy bij elke push
naar `main`, config in `vercel.json`). Zet `VITE_LOOKUP_API_URL` als
environment variable in het Vercel-project-dashboard (Settings →
Environment Variables) — niet in code, want de uiteindelijke URL van
`har-provider-lookup` staat pas vast na de hostingkeuze daarvoor.

## License

EUPL-1.2 — zie [LICENSE](LICENSE).

## Dependencies

| Package | License |
|---|---|
| @biomejs/biome (dev) | MIT |
| @playwright/test (dev) | Apache-2.0 |
| @types/node (dev) | MIT |
| cross-env (dev) | MIT |
| jsdom (dev) | MIT |
| typescript (dev) | Apache-2.0 |
| vite (dev) | MIT |
| vitest (dev) | MIT |
