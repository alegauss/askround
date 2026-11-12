import { BASE, repoUrl, words } from "./content";

// The one page. The table is what the design system's prerender reads.
export const SITE_ORIGIN = "https://alegauss.github.io";

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

/** Where a route's HTML is written, relative to dist/: "" for the root. */
export function outputDir(path: string): string {
  return path === "/" ? "" : path.replace(/^\/|\/$/g, "");
}
