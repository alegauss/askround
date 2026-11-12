import { Fragment } from "react";

// A command line, coloured the way a terminal would show it: the program, its subcommand,
// flags, quoted text and comments. Written out rather than taken from a highlighter library,
// since the page shows three short blocks and a dependency would weigh more than they do.
// A slash command (/plugin ...) is typed into Claude Code, so it gets no shell prompt.

type Kind = "cmd" | "sub" | "flag" | "str" | "comment" | "text";

function tokens(line: string): { kind: Kind; text: string }[] {
  const out: { kind: Kind; text: string }[] = [];
  const hash = line.search(/\s#\s/);
  const body = hash >= 0 ? line.slice(0, hash) : line;
  const comment = hash >= 0 ? line.slice(hash) : "";
  // words, quoted strings and the spaces between them, kept so the line reads as typed
  const parts = body.match(/"[^"]*"|\s+|[^\s"]+/g) ?? [];
  let words = 0;
  for (const part of parts) {
    if (/^\s+$/.test(part)) out.push({ kind: "text", text: part });
    else if (part.startsWith('"')) out.push({ kind: "str", text: part });
    else if (part.startsWith("--")) out.push({ kind: "flag", text: part });
    else {
      words += 1;
      const kinds: Record<number, Kind> = { 1: "cmd", 2: "sub" };
      out.push({ kind: kinds[words] ?? "text", text: part });
    }
  }
  if (comment) out.push({ kind: "comment", text: comment });
  return out;
}

export function Shell({ code }: Readonly<{ code: string }>) {
  return (
    <code className="shell">
      {code.split("\n").map((line, i) => (
        <Fragment key={i}>
          {i > 0 && "\n"}
          {!line.startsWith("/") && (
            <span className="sh-prompt" aria-hidden="true">
              ${" "}
            </span>
          )}
          {tokens(line).map((t, j) =>
            t.kind === "text" ? t.text : (
              <span key={j} className={`sh-${t.kind}`}>
                {t.text}
              </span>
            ),
          )}
        </Fragment>
      ))}
    </code>
  );
}
