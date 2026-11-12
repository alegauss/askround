import {
  SiteButton,
  SiteFooter,
  SiteNav,
  SiteSponsor,
  SiteThemeToggle,
  type SiteBrand,
} from "@viglet/viglet-design-system/site";
import { BASE, THEME_KEY, asset, hero, parentUrl, repoUrl, sponsor, words } from "../content";
import { Ad } from "./Ad";
import { ConsentSettings } from "./Consent";
import { Ripples } from "./Ripples";

// The nav and the footer, drawn by the design system's site layer so askround sits in the
// family beside FreeHarbor, roadkeep and Modelado. What is here is this product's half: which
// links, which words, the house ad that closes the page and the rings the footer opens on.

const brand: SiteBrand = { href: BASE, name: "askround", logo: asset("icon.svg") };

export function Nav() {
  return (
    <SiteNav
      brand={brand}
      parent={{ href: parentUrl, name: "alegauss", pre: "part of", title: "alegauss: small developer tools" }}
      links={words.nav.links}
      actions={
        <>
          <SiteButton href={`${BASE}#install`}>{words.nav.cta}</SiteButton>
          <SiteButton variant="ghost" href={repoUrl}>
            {hero.github}
          </SiteButton>
          <SiteThemeToggle storageKey={THEME_KEY} label={words.nav.themeLabel} />
        </>
      }
    />
  );
}

export function Footer() {
  return (
    <SiteFooter
      brand={brand}
      links={words.footer.links}
      sponsor={
        <SiteSponsor declaration={sponsor} moreLabel="More at" note="Both Apache 2.0 and self-hostable." />
      }
      disclaimer={
        <>
          {words.footer.disclaimer} <ConsentSettings />
        </>
      }
      // the house ad closes the page's content, above the footer
      before={<Ad slot="page-end" />}
    >
      <Ripples quiet />
    </SiteFooter>
  );
}
