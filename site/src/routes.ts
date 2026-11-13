import { BASE, repoUrl, words } from "./content";

// The one page. The table is what the design system's prerender reads.
export const SITE_ORIGIN = "https://alegauss.com";

// Absolute, because a platform fetching the social card is not on this origin.
export const OG_IMAGE = `${SITE_ORIGIN}${BASE}og.png`;

export const ROUTES = [{ path: "/", title: words.meta.title, description: words.meta.description }];

/** The canonical and og:url for a route, carrying the base. */
export function canonicalUrl(path: string): string {
  const rel = path === "/" ? "" : `${path.replace(/^\/|\/$/g, "")}/`;
  return `${SITE_ORIGIN}${BASE}${rel}`;
}

/** The page's schema.org description of the tool. The author is the Person the Alegauss hub
 *  declares, by its @id, so search engines tie the two together. */
export function jsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "askround",
    description: words.meta.description,
    url: canonicalUrl("/"),
    image: OG_IMAGE,
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Windows, macOS, Linux",
    license: "https://spdx.org/licenses/Apache-2.0.html",
    isAccessibleForFree: true,
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    sameAs: [repoUrl],
    author: { "@type": "Person", "@id": `${SITE_ORIGIN}/#person`, name: "Alexandre Oliveira", url: "https://github.com/alegauss" },
  };
}

/** The docs pages, as the docs area's sidebar lists them, for llms.txt. */
export const DOCS = [
  { path: "", title: "What askround is", about: "what it measures (the APIs, not the apps) and the laws" },
  { path: "install/", title: "Install", about: "the Claude Code plugin at project scope, pip and uvx, the API keys" },
  { path: "first-session/", title: "A first session", about: "what an agent calls when asked in plain words" },
  { path: "prompt-sets/", title: "Prompt sets", about: "product files, facts, refused questions, discover" },
  { path: "budget/", title: "Budget and consent", about: "estimate, cap, the day and month budget, personal data" },
  { path: "reports/", title: "Reports and diffs", about: "reading positions, claims, rivals, cited pages, research" },
  { path: "reference/mcp/", title: "MCP tools", about: "every tool and its arguments" },
  { path: "reference/cli/", title: "Command line", about: "every command, JSON schemas, exit codes" },
];

/** llms.txt (llmstxt.org): the product in a paragraph and where to read more, for an
 *  assistant that reads the site. Facts only: what it does and how to install it. */
export function llmsTxt(): string {
  const docs = DOCS.map((d) => `- [${d.title}](${canonicalUrl("/")}docs/${d.path}): ${d.about}`);
  return [
    "# askround",
    "",
    `> ${words.meta.description}`,
    "",
    "askround is open source (Apache-2.0), needs Python 3.11 or later and has no runtime dependencies. It asks each provider through its own API with its own web search tool, several runs per question, and reports per product how many runs named it and at which position, the rivals named beside it, the claims made about it with the passage each came from, and the pages cited. It measures the APIs, not the chat apps. In Claude Code it installs as a plugin (`/plugin marketplace add alegauss/askround`, then `/plugin install askround@askround`), which serves an MCP server so a coding agent can ask the assistants itself.",
    "",
    "## Docs",
    "",
    ...docs,
    "",
    "## Source",
    "",
    `- [Repository](${repoUrl}): the package, the README and the changelog`,
    "",
  ].join("\n");
}

/** Where a route's HTML is written, relative to dist/: "" for the root. */
export function outputDir(path: string): string {
  return path === "/" ? "" : path.replace(/^\/|\/$/g, "");
}
