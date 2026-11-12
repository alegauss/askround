import {
  SiteButton,
  SiteHero,
  SiteRich as Rich,
  SiteSectionHead,
} from "@viglet/viglet-design-system/site";
import type { ReactNode } from "react";
import { BASE, PROVIDER_NAMES, asset, hero, repoUrl, roadkeepUrl, words } from "../content";
import round from "../round.json";
import self from "../self-round.json";
import { HeroSession } from "./HeroSession";
import { Ripples } from "./Ripples";
import { Shell } from "./Shell";

// The landing page's sections, after FreeHarbor's: the design system's hero and section heads,
// cards that rise into place as they scroll in (.reveal, observed in App.tsx), and every word
// from content.ts.

function Section({
  id,
  eyebrow,
  title,
  lead,
  tinted = false,
  narrow = false,
  children,
}: Readonly<{
  id: string;
  eyebrow: string;
  title: string;
  lead?: ReactNode;
  tinted?: boolean;
  narrow?: boolean;
  children: ReactNode;
}>) {
  return (
    <section id={id} className={tinted ? "tinted" : undefined}>
      <div className={narrow ? "vg-site-wrap narrow" : "vg-site-wrap"}>
        <div className="reveal">
          <SiteSectionHead eyebrow={eyebrow} title={title}>
            {lead}
          </SiteSectionHead>
        </div>
        {children}
      </div>
    </section>
  );
}

export function Hero() {
  return (
    <SiteHero
      icon={{ src: asset("icon.svg"), alt: "askround logo" }}
      badge={hero.badge}
      title={hero.title}
      titleAccent={hero.titleAccent}
      sub={<Rich runs={hero.sub} />}
      actions={
        <>
          <SiteButton href={`${BASE}#install`}>{hero.install}</SiteButton>
          <SiteButton variant="ghost" href={repoUrl}>
            {hero.github}
          </SiteButton>
        </>
      }
      feature={<HeroSession />}
      meta={hero.meta}
      pills={hero.pills.map((runs, i) => (
        <Rich runs={runs} key={i} />
      ))}
    >
      <Ripples />
    </SiteHero>
  );
}

export function Round() {
  const w = words.round;
  const lists: Record<string, { names: string[]; how: string }> = {
    openai: { names: round.openai_recommends, how: w.readBy(round.read_by) },
    gemini: { names: round.gemini_names, how: w.headings },
  };
  return (
    <Section id="round" eyebrow={w.eyebrow} title={w.title} lead={w.lead(round.asked_on)}>
      <figure className="question reveal">
        <figcaption>{w.question}</figcaption>
        <blockquote>{round.question}</blockquote>
      </figure>
      <ul className="answers">
        {round.answers.map((a) => {
          const list = lists[a.provider];
          return (
            <li key={a.provider} className="answer reveal">
              <h3>{PROVIDER_NAMES[a.provider] ?? a.provider}</h3>
              <p className="answer-model">{a.model}</p>
              <p className={a.named ? "verdict is-named" : "verdict"}>
                {round.product}: {a.named && a.position ? w.named(a.position) : w.missing}
              </p>
              {list && (
                <>
                  <p className="answer-label">
                    {w.answered} <span>({list.how})</span>
                  </p>
                  <ol className="answer-list">
                    {list.names.map((name) => (
                      <li key={name} className={name.startsWith(round.product) ? "is-product" : undefined}>
                        {name}
                      </li>
                    ))}
                  </ol>
                </>
              )}
            </li>
          );
        })}
      </ul>
      <p className="sec-note">
        {w.cost(`$${round.cost.toFixed(2)}`)} {w.note}
      </p>
    </Section>
  );
}

function Cards({ items, columns }: Readonly<{ items: readonly { icon: string; title: string; body: string }[]; columns: 2 | 3 }>) {
  return (
    <div className={`grid grid-${columns}`}>
      {items.map((item) => (
        <div className="card reveal" key={item.title}>
          <div className="ico" aria-hidden="true">
            {item.icon}
          </div>
          <h3>{item.title}</h3>
          <p>{item.body}</p>
        </div>
      ))}
    </div>
  );
}

export function How() {
  const w = words.how;
  return (
    <Section id="how" eyebrow={w.eyebrow} title={w.title} tinted>
      <Cards items={w.items} columns={3} />
    </Section>
  );
}

export function Agents() {
  const w = words.agents;
  return (
    <Section id="agents" eyebrow={w.eyebrow} title={w.title} lead={w.lead}>
      <Cards items={w.items} columns={2} />
      <p className="sec-note">
        {w.family} <a href={roadkeepUrl}>{w.familyLink}</a>
      </p>
    </Section>
  );
}

export function Install() {
  const w = words.install;
  return (
    <Section id="install" eyebrow={w.eyebrow} title={w.title} tinted narrow>
      <ol className="steps">
        {w.steps.map((step) => (
          <li key={step.label} className="reveal">
            <p>{step.label}</p>
            <pre tabIndex={0}>
              <Shell code={step.code} />
            </pre>
          </li>
        ))}
      </ol>
      <p className="sec-note">{w.keys}</p>
    </Section>
  );
}

export function Cost() {
  const w = words.cost;
  return (
    <Section id="cost" eyebrow={w.eyebrow} title={w.title} lead={w.lead} narrow>
      <table className="facts reveal">
        <thead>
          <tr>
            <th scope="col">{w.head.tool}</th>
            <th scope="col">{w.head.tokens}</th>
            <th scope="col">{w.head.budget}</th>
          </tr>
        </thead>
        <tbody>
          {w.rows.map((row) => (
            <tr key={row.tool}>
              <th scope="row">{row.tool}</th>
              <td>{row.tokens}</td>
              <td>{row.budget}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="sec-note">{w.note}</p>
    </Section>
  );
}

export function Self() {
  const w = words.self;
  const providers = self.questions[0]?.answers.map((a) => a.provider) ?? [];
  return (
    <Section id="self" eyebrow={w.eyebrow} title={w.title} lead={w.lead(self.asked_on, `$${self.cost.toFixed(2)}`)} tinted>
      {/* It scrolls sideways on a phone, so it takes focus for a keyboard to scroll it. */}
      <section className="self-scroll reveal" tabIndex={0} aria-label={w.tableLabel}>
        <table className="facts self-table">
          <thead>
            <tr>
              <th scope="col">{w.head.question}</th>
              {providers.map((p) => (
                <th scope="col" key={p}>
                  {PROVIDER_NAMES[p] ?? p}
                </th>
              ))}
              <th scope="col">{w.head.rivals}</th>
            </tr>
          </thead>
          <tbody>
            {self.questions.map((q) => (
              <tr key={q.text}>
                <th scope="row">{q.text}</th>
                {q.answers.map((a) => (
                  <td key={a.provider}>{w.cell(a.named, a.runs, a.best)}</td>
                ))}
                <td>{q.rivals.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <p className="sec-note">
        {w.file} <a href={`${repoUrl}/blob/main/examples/askround.toml`}>examples/askround.toml</a>
      </p>
    </Section>
  );
}
