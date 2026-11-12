// The prerender, the social card and the touch icon, after the client and SSR builds (after
// Modelado's scripts/prerender.mjs).
//
// prerenderSite writes the rendered page into dist/index.html, patching the <head> by
// replace-or-throw, and writes sitemap.xml and robots.txt from the same route table. ogCardSvg
// draws the family's social card in the cool tone with the askround mark, and renderOgCard
// rasterises it to dist/og.png at 1200 x 630. The 180 px touch icon is rasterised from
// public/icon.svg, since an Apple device will not take an SVG for it.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";
import { ogCardSvg, prerenderSite, renderOgCard } from "@viglet/viglet-design-system/vite";

import { render, ROUTES, canonicalUrl, jsonLd, llmsTxt, outputDir, OG_IMAGE } from "../dist-server/entry-server.js";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(siteDir, "dist");
const icon = readFileSync(join(siteDir, "public", "icon.svg"), "utf8");

const card = await renderOgCard({
  svg: ogCardSvg({
    eyebrow: "askround · for agents and the people who run them",
    title: ["See what assistants"],
    titleAccent: "recommend.",
    line: ["Ask ChatGPT, Gemini, Claude and Perplexity the same question", "and read whether your product is named, and where."],
    mark: icon,
    tone: "cool",
  }),
  out: join(distDir, "og.png"),
});
console.log(`og-image: dist/og.png  ${card.width}x${card.height}  (${(card.bytes / 1024).toFixed(0)} kB)`);

const touch = new Resvg(icon, { fitTo: { mode: "width", value: 180 } }).render().asPng();
writeFileSync(join(distDir, "apple-touch-icon.png"), touch);
console.log(`touch icon: dist/apple-touch-icon.png  180x180  (${(touch.length / 1024).toFixed(0)} kB)`);

const written = prerenderSite({
  distDir,
  routes: ROUTES,
  render,
  canonicalUrl,
  outputDir,
  ogImage: OG_IMAGE,
  git: { cwd: siteDir },
  log: console.log,
});

// The JSON-LD that says the page is a tool's, which the shared prerender does not write.
// Replace-or-throw, like the prerender; "<" escaped so no text in it can close the script early.
const page = join(distDir, "index.html");
const html = readFileSync(page, "utf8");
if (!html.includes("</head>")) throw new Error(`${page} lost its </head>`);
const data = jsonLd();
checkJsonLd(data);
const ld = JSON.stringify(data).replace(/</g, "\\u003c");
writeFileSync(page, html.replace("</head>", () => `<script type="application/ld+json">${ld}</script>\n  </head>`));

// AR43: llms.txt for an assistant that reads the site, checked against the format llmstxt.org
// sets before it is written: an H1 with the name, a blockquote summary, then H2 sections of
// Markdown links. A file that broke the format would fail the build, not ship.
const llms = llmsTxt();
checkLlmsTxt(llms);
writeFileSync(join(distDir, "llms.txt"), llms);
console.log(`llms.txt: dist/llms.txt  ${llms.split("\n").length} lines`);

/** The fields a SoftwareApplication needs for a rich result, and absolute URLs. */
function checkJsonLd(ld) {
  const need = ["@context", "@type", "name", "description", "url", "applicationCategory", "operatingSystem", "offers", "license", "author"];
  const missing = need.filter((key) => ld[key] === undefined || ld[key] === "");
  if (missing.length) throw new Error(`JSON-LD lacks ${missing.join(", ")}`);
  if (ld["@context"] !== "https://schema.org" || ld["@type"] !== "SoftwareApplication") {
    throw new Error("JSON-LD is not a schema.org SoftwareApplication");
  }
  if (ld.offers["@type"] !== "Offer" || ld.offers.price === undefined || !ld.offers.priceCurrency) {
    throw new Error("JSON-LD offers needs @type Offer, price and priceCurrency");
  }
  for (const url of [ld.url, ld.image, ld.license, ...(ld.sameAs ?? [])]) {
    if (url && !/^https:\/\//.test(url)) throw new Error(`JSON-LD URL is not absolute: ${url}`);
  }
}

function checkLlmsTxt(text) {
  const lines = text.split("\n");
  if (!/^# \S/.test(lines[0])) throw new Error("llms.txt must open with an H1 naming the project");
  if (!lines.some((line) => line.startsWith("> "))) throw new Error("llms.txt needs a blockquote summary");
  const links = lines.filter((line) => line.startsWith("- ["));
  if (!links.length) throw new Error("llms.txt lists no links");
  for (const line of links) {
    if (!/^- \[[^\]]+\]\(https:\/\/[^)]+\)(: .+)?$/.test(line)) throw new Error(`llms.txt link is malformed: ${line}`);
  }
}

console.log(`prerender: ${written.length} route(s), sitemap.xml and robots.txt written to dist/`);
