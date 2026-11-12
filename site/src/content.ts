// Every word on the page, in English only. What is not a word (the base, the links) is
// written once here too. The round itself is not here: it is ./round.json, which
// tests/test_site.py holds to askround's own reading of the recorded live answers.

export const THEME_KEY = "askround-theme";
export const BASE = "/askround/";
export const repoUrl = "https://github.com/alegauss/askround";
export const roadkeepUrl = "https://alegauss.github.io/roadkeep/";

/** A file under public/, with the base. */
export const asset = (path: string) => `${BASE}${path}`;

export const PROVIDER_NAMES: Record<string, string> = {
  openai: "ChatGPT (OpenAI API)",
  gemini: "Gemini (Google API)",
  anthropic: "Claude (Anthropic API)",
  perplexity: "Perplexity (Sonar API)",
};

export const words = {
  meta: {
    title: "askround: see what ChatGPT, Gemini, Claude and Perplexity recommend",
    description:
      "Ask ChatGPT, Gemini, Claude and Perplexity the same question through their APIs, with web search, and read whether your product is named, where, beside which rivals, and what they claim about it. A CLI and an MCP server your agent calls itself.",
  },
  nav: {
    links: [
      { href: `${BASE}#round`, label: "A real round" },
      { href: `${BASE}#agents`, label: "For agents" },
      { href: `${BASE}#install`, label: "Install" },
      { href: `${BASE}#cost`, label: "Cost" },
      { href: `${BASE}docs/`, label: "Docs" },
      { href: repoUrl, label: "Source" },
    ],
    cta: "Install",
    themeLabel: (next: string) => `Switch to the ${next} theme`,
  },
  intro: {
    eyebrow: "askround · open source · Python",
    title: "You cannot see what assistants say about your product. Now you can ask them.",
    lead:
      "People ask ChatGPT, Gemini, Claude and Perplexity which tool to use, and you never see the answer. askround asks them the same question through their APIs, with web search on, several times each, and reads what comes back: whether your product is named, at which position, beside which rivals, what is claimed about it and which pages are cited.",
    agent:
      "Your coding agent can ask them too. With askround's MCP server it runs the question itself instead of asking you to paste ChatGPT's answer back.",
    install: "Install it",
    source: "See the source",
  },
  round: {
    eyebrow: "A real round",
    title: "One question, two assistants, two different answers",
    lead: (date: string) =>
      `Asked on ${date} through the APIs with web search, one answer each, about Modelado, a Windows app by the same author. Recorded, not mocked: these are the answers askround reads in its own tests.`,
    question: "The question",
    named: (position: number) => `Named, #${position}`,
    missing: "Not named",
    answered: "What it recommended, in order",
    readBy: (model: string) => `as the extraction pass read it, with ${model.replace(/^\w+:/, "")}`,
    headings: "its own bold headings",
    cost: (usd: string) => `The round cost ${usd} on the author's keys.`,
    note:
      "Answers vary from run to run, so a real round asks each question several times and reports how many runs name the product. askround measures the APIs, not the chat apps, which add memory and personalisation of their own.",
  },
  self: {
    eyebrow: "Measured on itself",
    title: "Do the assistants name askround? Not yet.",
    lead: (date: string, cost: string) =>
      `askround keeps a prompt set about itself, the questions a developer would ask without knowing it exists, and this is its latest round, from ${date}: one run per question on each provider, ${cost} in all. It is shown as it came back.`,
    head: { question: "Question", rivals: "What they named instead" },
    cell: (named: number, runs: number, best: number | null) => {
      if (!named) return `not named (0/${runs})`;
      const at = best ? `, #${best}` : "";
      return `named ${named}/${runs}${at}`;
    },
    tableLabel: "askround's own prompt set, by question and provider",
    file: "The set is examples/askround.toml in the repository.",
  },
  how: {
    eyebrow: "What a round reports",
    title: "Read the answers as data, not anecdotes",
    items: [
      {
        title: "Named, and where",
        body: "For each product, how many runs name it and its position in each, per provider and per locale. A table's \"best fit\" row counts as a position.",
      },
      {
        title: "Rivals and claims",
        body: "The products named beside yours, and what each answer claims about yours, quoted, with the answer it came from, checked against the facts in your product file.",
      },
      {
        title: "Pages cited",
        body: "Which of your pages the assistants cite, and the ones they cite instead. A prompt set runs the same questions every week, and diff says what moved.",
      },
    ],
  },
  agents: {
    eyebrow: "For agents",
    title: "Built for the agent that asks, not the person who pastes",
    lead:
      "askround is a CLI and an MCP server with zero runtime dependencies, in the family of roadkeep: small answers on purpose, refusals before money is spent, and nothing an agent has to read twice.",
    items: [
      {
        title: "A brief, not a transcript",
        body: "askround_ask returns a few hundred tokens for a whole round: each product's runs and positions, the rivals, the claims, each fact with the ids of the answers it came from. askround_answer returns one answer, or only the passage behind a fact.",
      },
      {
        title: "Refused before it is paid for",
        body: "A question that names the product it tests, personal data, a missing key or a round estimated above the cap is refused before the first call, every problem at once, each with a code and its fix.",
      },
      {
        title: "The person sets the money",
        body: "A day and a month budget in a config file no tool writes. An agent cannot raise it, and a round that would pass it waits for the person's approval.",
      },
      {
        title: "Long rounds as jobs",
        body: "A round takes minutes. Started in the background, it returns a job id at once and keeps every answer as it lands, so an interrupted round loses nothing it paid for.",
      },
    ],
    family: "The same discipline as roadkeep, the roadmap tool these were built with.",
    familyLink: "See roadkeep",
  },
  install: {
    eyebrow: "Install",
    title: "Python 3.11 and the API keys you already have",
    steps: [
      {
        label: "In Claude Code, the plugin: the MCP server, four slash commands and the skill",
        code: "/plugin marketplace add alegauss/askround\n/plugin install askround@askround",
      },
      {
        label: "Or the command line, from a checkout until the first release",
        code: "pip install .\naskround doctor\naskround ask \"What Windows app can turn a photo into a 3D model?\" --product \"Modelado\" --extract",
      },
      {
        label: "Wire a project for everyone who clones it",
        code: "askround install           # names the plugin in .claude/settings.json\naskround install --vendor  # and a copy for Claude Code on the web",
      },
    ],
    keys:
      "Keys are read from OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY and PERPLEXITY_API_KEY. askround never stores them, and doctor names the variables, never their values.",
  },
  cost: {
    eyebrow: "Cost",
    title: "Measured, in money and in tokens",
    lead:
      "Every round prints an estimate before it runs and its actual cost after, from a dated price table. What each MCP response costs the agent is measured in the tests on recorded rounds, against a budget per tool that a change cannot pass unnoticed.",
    head: { tool: "MCP response", tokens: "Tokens", budget: "Budget" },
    rows: [
      { tool: "askround_ask, the brief", tokens: "304", budget: "400" },
      { tool: "askround_ask with detail", tokens: "1,360", budget: "1,800" },
      { tool: "askround_answer", tokens: "868", budget: "1,100" },
      { tool: "askround_answer around a quote", tokens: "175", budget: "250" },
      { tool: "askround_run, a whole prompt set", tokens: "760", budget: "1,000" },
      { tool: "askround_diff", tokens: "112", budget: "200" },
    ],
    note: "Two providers, three runs, extraction on; one token per four characters of JSON.",
  },
  footer: {
    links: [
      { href: repoUrl, label: "GitHub" },
      { href: `${BASE}docs/`, label: "Docs" },
      { href: `${repoUrl}/blob/main/docs/CHANGELOG.md`, label: "Changelog" },
      { href: roadkeepUrl, label: "roadkeep" },
    ],
    disclaimer:
      "askround calls the providers' public APIs with your keys. It is not affiliated with OpenAI, Google, Anthropic or Perplexity.",
  },
};
