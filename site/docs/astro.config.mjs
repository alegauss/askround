// The documentation area, at https://alegauss.com/askround/docs/, after roadkeep's.
//
// The README is the first screen; these pages are the reads a person needs to set askround up
// and an agent's user needs to trust what it reports. Starlight gives the sidebar, the
// per-page contents and a search indexed at build time, so nothing here runs on a server.
//
// The base is one segment under the site's (vite.config.ts names /askround/), and the output
// is a subdirectory of the site's dist/, because the deploy uploads that one directory. Astro
// empties outDir and `vite build` empties dist/, so this build runs last in the site's build.
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://alegauss.com",
  base: "/askround/docs",
  outDir: "../dist/docs",

  integrations: [
    starlight({
      title: "askround",
      description:
        "Ask ChatGPT, Gemini, Claude and Perplexity the same question through their APIs and read what they recommend.",
      pagefind: true,
      social: [{ icon: "github", label: "GitHub", href: "https://github.com/alegauss/askround" }],
      customCss: ["./src/styles/area.css"],
      sidebar: [
        { label: "What askround is", link: "/" },
        { label: "Install", link: "/install/" },
        { label: "A first session", link: "/first-session/" },
        { label: "Prompt sets", link: "/prompt-sets/" },
        { label: "Budget and consent", link: "/budget/" },
        { label: "Reports and diffs", link: "/reports/" },
        {
          label: "Reference",
          items: [
            { label: "MCP tools", link: "/reference/mcp/" },
            { label: "Command line", link: "/reference/cli/" },
          ],
        },
      ],
      editLink: {},
      lastUpdated: true,
    }),
  ],
});
