# har-scan-web

Statische, client-side webpagina waar je een HAR-bestand kunt uploaden om
te zien welke leveranciers en landen erachter schuilgaan — zonder dat het
bestand ooit in ruwe vorm je browser verlaat.

Sanitizing gebeurt volledig lokaal: alleen hostnamen (en hoe vaak ze
worden aangeroepen) worden naar de lookup-backend
([har-provider-lookup](../har-provider-lookup)) gestuurd. Cookies,
auth-headers, request/response-bodies en query strings worden nooit
gelezen buiten het moment van hostname-extractie.

## Ontwikkelen

```bash
npm install
cp .env.example .env
npm run dev
```

Vereist een lokaal draaiende `har-provider-lookup` op de URL uit
`VITE_LOOKUP_API_URL` (standaard `http://localhost:8080`) — zie de
README van die repo.

## Testen

```bash
npm test              # unit tests (Vitest)
npm run check          # lint + format (Biome)
npm run e2e             # end-to-end (Playwright, start har-provider-lookup via Docker eerst — zie playwright.config.ts)
```

## Bouwen

```bash
npm run build
```

Output in `dist/`, gepubliceerd naar GitHub Pages via
`.github/workflows/deploy-pages.yml` bij elke push naar `main`.

Afhankelijk van de hostingkeuze moet `VITE_BASE` in die workflow worden gezet:
laat hem ongezet bij een custom domain (base blijft `/`), en zet hem op
`/<repo-naam>/` bij een GitHub Pages project-site (`<org>.github.io/<repo>`).

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
