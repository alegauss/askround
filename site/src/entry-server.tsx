import { renderToString } from "react-dom/server";
import { App } from "./App";

// The build-side render: scripts/prerender.mjs calls it for the route and writes the result into
// its index.html, with the head patched from the route table.
export { ROUTES, canonicalUrl, jsonLd, outputDir, OG_IMAGE } from "./routes";

export function render(): string {
  return renderToString(<App />);
}
