import { SiteButton } from "@viglet/viglet-design-system/site";
import { BASE, PROVIDER_NAMES, repoUrl, roadkeepUrl, words } from "../content";
import round from "../round.json";
import self from "../self-round.json";
import { Shell } from "./Shell";

function Head({ id, eyebrow, title }: { id: string; eyebrow: string; title: string }) {
  return (
    <div className="sec-head">
      <p className="eyebrow">{eyebrow}</p>
      <h2 id={id}>{title}</h2>
    </div>
  );
}

export function Intro() {
  const w = words.intro;
  return (
    <section className="intro" aria-labelledby="intro-title">
      <div className="wrap">
        <p className="eyebrow">{w.eyebrow}</p>
        <h1 id="intro-title">{w.title}</h1>
        <p className="intro-lead">{w.lead}</p>
        <p className="intro-lead">{w.agent}</p>
        <div className="intro-actions">
          <SiteButton href={`${BASE}#install`}>{w.install}</SiteButton>
          <SiteButton href={repoUrl} variant="ghost" rel="noopener">
            {w.source}
          </SiteButton>
        </div>
      </div>
    </section>
  );
}

export function Round() {
  const w = words.round;
  const lists: Record<string, { names: string[]; how: string }> = {
    openai: { names: round.openai_recommends, how: w.readBy(round.read_by) },
    gemini: { names: round.gemini_names, how: w.headings },
  };
  return (
    <section className="round" aria-labelledby="round">
      <div className="wrap">
        <Head id="round" eyebrow={w.eyebrow} title={w.title} />
        <p className="sec-lead">{w.lead(round.asked_on)}</p>
        <figure className="question">
          <figcaption>{w.question}</figcaption>
          <blockquote>{round.question}</blockquote>
        </figure>
        <ul className="answers">
          {round.answers.map((a) => {
            const list = lists[a.provider];
            return (
              <li key={a.provider} className="answer">
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
      </div>
    </section>
  );
}

export function Self() {
  const w = words.self;
  const providers = self.questions[0]?.answers.map((a) => a.provider) ?? [];
  return (
    <section aria-labelledby="self">
      <div className="wrap">
        <Head id="self" eyebrow={w.eyebrow} title={w.title} />
        <p className="sec-lead">{w.lead(self.asked_on, `$${self.cost.toFixed(2)}`)}</p>
        {/* It scrolls sideways on a phone, so it takes focus for a keyboard to scroll it. */}
        <div className="self-scroll" tabIndex={0} role="region" aria-label={w.tableLabel}>
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
        </div>
        <p className="sec-note">
          {w.file} <a href={`${repoUrl}/blob/main/examples/askround.toml`}>examples/askround.toml</a>
        </p>
      </div>
    </section>
  );
}

export function How() {
  const w = words.how;
  return (
    <section className="tinted" aria-labelledby="how">
      <div className="wrap">
        <Head id="how" eyebrow={w.eyebrow} title={w.title} />
        <ul className="cards cards-3">
          {w.items.map((item) => (
            <li key={item.title} className="card">
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function Agents() {
  const w = words.agents;
  return (
    <section aria-labelledby="agents">
      <div className="wrap">
        <Head id="agents" eyebrow={w.eyebrow} title={w.title} />
        <p className="sec-lead">{w.lead}</p>
        <ul className="cards cards-2">
          {w.items.map((item) => (
            <li key={item.title} className="card">
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
        <p className="sec-note">
          {w.family} <a href={roadkeepUrl}>{w.familyLink}</a>
        </p>
      </div>
    </section>
  );
}

export function Install() {
  const w = words.install;
  return (
    <section className="tinted" aria-labelledby="install">
      <div className="wrap narrow">
        <Head id="install" eyebrow={w.eyebrow} title={w.title} />
        <ol className="steps">
          {w.steps.map((step) => (
            <li key={step.label}>
              <p>{step.label}</p>
              <pre tabIndex={0}>
                <Shell code={step.code} />
              </pre>
            </li>
          ))}
        </ol>
        <p className="sec-note">{w.keys}</p>
      </div>
    </section>
  );
}

export function Cost() {
  const w = words.cost;
  return (
    <section aria-labelledby="cost">
      <div className="wrap narrow">
        <Head id="cost" eyebrow={w.eyebrow} title={w.title} />
        <p className="sec-lead">{w.lead}</p>
        <table className="facts">
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
      </div>
    </section>
  );
}
