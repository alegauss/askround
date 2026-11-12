// The house ad slot, after FreeHarbor's (its DD186).
//
// japode-ads is the author's own network: one script, one request per page however many
// slots it finds, every banner drawn inside its own shadow root, no impressions counted and
// no identifiers. The loader resolves the theme as it draws and never looks again, so when
// the reader flips the page's theme the slots are given the new one and the script is run
// again, which redraws them from the catalogue the browser has already cached.

import { useEffect } from "react";
import { createSiteTheme, type SiteTheme as Theme } from "@viglet/viglet-design-system/site";
import { THEME_KEY } from "../content";

const theme = createSiteTheme(THEME_KEY);

const SRC = "https://ads.japode.com/v1/ads.js";

/** The theme every slot on this page is currently drawn in, or null before the first run. */
let drawn: Theme | null = null;

function draw(next: Theme): void {
  for (const slot of Array.from(document.querySelectorAll("[data-japode-ads]"))) {
    slot.setAttribute("data-ad-theme", next);
  }
  if (drawn === next) return;
  drawn = next;
  document.querySelector(`script[src="${SRC}"]`)?.remove();
  const script = document.createElement("script");
  script.src = SRC;
  script.async = true;
  document.body.appendChild(script);
}

/** Keep the page's ad slots on the theme the page shows: the toggle, and the OS preference
 *  for a reader who never touches it. Nothing is requested before this runs. */
export function useAds(): void {
  useEffect(() => {
    const sync = () => draw(theme.effective());
    sync();
    const toggle = new MutationObserver(sync);
    toggle.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const os = matchMedia("(prefers-color-scheme: dark)");
    os.addEventListener("change", sync);
    return () => {
      toggle.disconnect();
      os.removeEventListener("change", sync);
    };
  }, []);
}
