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
| `src/components/Chrome.tsx` | The design system's nav (with the alegauss parent link) and footer (with the Viglet sponsor and the house ad), after FreeHarbor's |
| `src/components/Sections.tsx` | The page's sections, on the design system's `SiteHero` and `SiteSectionHead`; `.reveal` elements rise in as they scroll into view (`App.tsx`) |
| `src/components/HeroSession.tsx` | The hero's agent session, prerendered whole and played one step at a time after load |
| `src/components/Ripples.tsx` | The hero's and footer's motion: rings out from the mark, four assistants in orbit. Still under reduced motion |
| `src/components/Ad.tsx`, `ads.ts` | The japode-ads house slot above the footer: one script, a shadow root, no memory, redrawn when the theme flips |
| `src/components/Consent.tsx` | Google Analytics only after the visitor allows it, sharing the hub's choice |
| `public/icon.svg`, `favicon.svg` | The mark: four answers around one question |
| `scripts/prerender.mjs` | The prerender, `og.png` and `apple-touch-icon.png` |
| `docs/` | The docs area at `/askround/docs/`: its own npm project (Astro Starlight), built last by `npm run build` into `dist/docs`. The MCP and CLI reference pages are generated from the package by `docs/scripts/reference.py`; `npm ci --prefix docs` installs it |
