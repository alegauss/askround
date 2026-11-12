# askround site

The public site, in English, at `/askround/`: a self-contained Vite + React 19 + TypeScript +
Tailwind v4 workspace, after Modelado's. The Python package and its tests neither build nor
need it.

The chrome is the family's: the nav, footer, buttons and theme toggle come from
`@viglet/viglet-design-system/site`, the colours from its default cool tone (the `--vg-*` tokens),
and the prerender and social card from its `/vite` helpers. The page between the nav and the
footer is askround's own.

## Commands

```
npm install        # once
npm run dev        # dev server at /askround/
npm run build      # tsc, client, SSR, then the prerender: the page, og.png, the touch icon
npm run preview    # serve the built dist/
```

`npm run build` is the gate. The prerender writes the page's title, description, canonical and
og:url by replace-or-throw, so a template that lost an anchor fails the build.

## Where things live

| Path | What |
|---|---|
| `src/content.ts` | **Every word**, and the base and the links, written once |
| `src/round.json` | The round the page shows: askround's reading of the answers recorded live on 2026-11-12 (`tests/fixtures/`). `tests/test_site.py` fails when it says anything else; `python tests/test_site.py` writes it again |
| `src/routes.ts` | The route and its metadata, read by the prerender |
| `src/components/Chrome.tsx` | The design system's nav and footer, with askround's brand |
| `src/components/Sections.tsx` | The page's sections |
| `public/icon.svg`, `favicon.svg` | The mark: four answers around one question |
| `scripts/prerender.mjs` | The prerender, `og.png` and `apple-touch-icon.png` |
| `docs/` | The docs area at `/askround/docs/`: its own npm project (Astro Starlight), built last by `npm run build` into `dist/docs`. The MCP and CLI reference pages are generated from the package by `docs/scripts/reference.py`; `npm ci --prefix docs` installs it |
