"""The `askround` command.

    askround ask "<question>" [--provider NAME ...] [--model PROVIDER=MODEL ...]
                 [--runs N] [--product NAME[,ALIAS...]] [--locale COUNTRY[:LANG] ...]
                 [--no-search] [--out DIR] [--json]
    askround run PRODUCT.toml [--provider NAME ...] [--runs N] [--extract] [--out DIR]
    askround report [ROUND] [--product NAME[,ALIAS...] ...] [--out DIR] [--json]
    askround doctor [--provider NAME ...] [--model PROVIDER=MODEL ...] [--no-check] [--json]

`ask` sends the question to every provider whose API key is in the environment (or the
ones named with --provider), --runs times each (default 3), with web search on unless
--no-search, prints each answer under its provider's heading with the sources it
cited, then for each --product the share of runs that named it and its positions, and
saves the round under --out (default `.askround/rounds`, or `ASKROUND_DIR`).

`report` reads a stored round back (by default the latest) and sums it up in one short
report, Markdown or --json, without the answers' text.

`doctor` says which providers can run here: key variable (never the value), model,
search tool and a free check call. It exits 2 when no provider can run.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path

from askround import (
    __version__,
    citations,
    costs,
    diff,
    discover,
    export,
    gaps,
    leading,
    links,
    lookup,
    private,
    product,
    research,
    series,
    sets,
)
from askround import report as report_
from askround.claims import product_claims
from askround.doctor import Status, diagnose
from askround.extract import choose, extract_round
from askround.provenance import schema
from askround.providers import Answer, Locale, all_providers, by_name
from askround.rivals import key as rival_key
from askround.rivals import rivals
from askround.round import (
    DEFAULT_RUNS,
    Round,
    cost,
    failures,
    frequency,
    run_round,
    save_round,
    summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="askround", description="Ask several AI assistants the same question."
    )
    parser.add_argument("--version", action="version", version=f"askround {__version__}")
    paid = argparse.ArgumentParser(add_help=False)
    paid.add_argument(
        "--max-cost",
        type=float,
        metavar="USD",
        help="refuse, before anything is sent, a run estimated above this (or ASKROUND_MAX_COST)",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--provider",
        action="append",
        dest="providers",
        metavar="NAME",
        help="only this provider (repeatable)",
    )
    common.add_argument(
        "--model",
        action="append",
        dest="models",
        type=_pin,
        metavar="PROVIDER=MODEL",
        help="pin the model one provider uses (repeatable)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser(
        "ask", parents=[common, paid], help="send one question to every configured provider"
    )
    ask.add_argument("question")
    ask.add_argument(
        "--no-search",
        dest="search",
        action="store_false",
        help="ask without web search, to compare with a searched round",
    )
    ask.add_argument(
        "--runs",
        type=_positive,
        default=DEFAULT_RUNS,
        help=f"times each provider is asked, in fresh conversations (default {DEFAULT_RUNS})",
    )
    ask.add_argument(
        "--product",
        action="append",
        dest="products",
        type=_names,
        metavar="NAME[,ALIAS...]",
        help="report how often this product is named and where (repeatable)",
    )
    ask.add_argument(
        "--locale",
        action="append",
        dest="locales",
        type=_locale,
        metavar="COUNTRY[:LANGUAGE]",
        help="ask as someone in this country, e.g. BR:pt-BR; repeat to compare (each "
        "locale is a full set of runs)",
    )
    ask.add_argument(
        "--extract",
        nargs="?",
        const="auto",
        metavar="PROVIDER",
        help="read each answer's recommendations in order with a model (one extra call "
        "per answer), so a product's rank counts tables and prose; default extractor: the "
        "first of openai, gemini, anthropic with a key",
    )
    ask.add_argument(
        "--check-rivals",
        nargs="?",
        type=_positive,
        const=10,
        metavar="N",
        help="look up whether the top N rivals (default 10) exist: GitHub, then one "
        "searched call each; needs --extract",
    )
    ask.add_argument(
        "--product-file",
        action="append",
        dest="product_files",
        type=Path,
        metavar="PATH",
        help="a product file (TOML: names, places, facts); with --extract, the answers' "
        "claims are compared with its facts (repeatable)",
    )
    ask.add_argument(
        "--brand",
        action="store_true",
        help="the question names the product on purpose; without this it is refused",
    )
    ask.add_argument(
        "--check-links",
        action="store_true",
        help="follow the links each answer gives beside a --product, and flag the ones "
        "that land on someone else's page",
    )
    ask.add_argument("--out", type=Path, help="where rounds are saved")
    ask.add_argument("--json", action="store_true", help="print the round as JSON")
    run = commands.add_parser(
        "run", parents=[common, paid], help="ask every question of a product file (a prompt set)"
    )
    run.add_argument("file", type=Path, metavar="PRODUCT.toml")
    run.add_argument(
        "--runs", type=_positive, help="runs per question, over what the file sets for each"
    )
    run.add_argument("--no-search", dest="search", action="store_false", help="no web search")
    run.add_argument(
        "--extract",
        nargs="?",
        const="auto",
        metavar="PROVIDER",
        help="read recommendations and claims, and compare the claims with the file's facts",
    )
    run.add_argument("--check-links", action="store_true", help="follow the product's links")
    run.add_argument("--out", type=Path, help="where rounds are saved")
    run.add_argument("--json", action="store_true", help="print the set's report as JSON")
    disc = commands.add_parser(
        "discover",
        parents=[common, paid],
        help="find which way of asking leads the assistants to a product",
    )
    disc.add_argument("file", type=Path, metavar="PRODUCT.toml")
    disc.add_argument("--seed", help="the question to vary (default: the file's first one)")
    disc.add_argument("--variants", type=_positive, default=6, help="how many (default 6)")
    disc.add_argument("--runs", type=_positive, default=1, help="runs per question (default 1)")
    disc.add_argument(
        "--extract",
        nargs="?",
        const="auto",
        metavar="PROVIDER",
        help="also rank by the extraction pass (one more call per answer)",
    )
    disc.add_argument("--out", type=Path, help="where rounds are saved")
    disc.add_argument("--json", action="store_true", help="print the ranking as JSON")
    find = commands.add_parser(
        "lookup", help="check whether products exist: GitHub, then one searched call each"
    )
    find.add_argument("names", nargs="+", metavar="NAME")
    find.add_argument("--context", default="", help="what they were recommended for")
    find.add_argument("--no-web", dest="web", action="store_false", help="GitHub only, free")
    find.add_argument("--json", action="store_true", help="print the verdicts as JSON")
    dif = commands.add_parser("diff", help="what changed between two rounds or prompt set runs")
    dif.add_argument("old", nargs="?", type=Path, help="the earlier round or set (directory)")
    dif.add_argument("new", nargs="?", type=Path, help="the later one")
    dif.add_argument("--product", type=_names, metavar="NAME[,ALIAS...]", help="compare for it")
    dif.add_argument("--out", type=Path, help="where rounds are saved")
    dif.add_argument("--json", action="store_true", help="print the changes as JSON")
    serie = commands.add_parser(
        "series", help="a product's share of answers over time, from every round kept"
    )
    serie.add_argument(
        "--product", dest="product", metavar="NAME", help="the product to follow (required)"
    )
    serie.add_argument("--by", choices=series.PERIODS, default="week", help="default: week")
    serie.add_argument("--question", help="only questions containing this text")
    serie.add_argument(
        "--rebuild", action="store_true", help="write the series again from every round.json"
    )
    serie.add_argument("--out", type=Path, help="where rounds are saved")
    serie.add_argument("--json", action="store_true", help="print the table as JSON")
    research_ = commands.add_parser(
        "research",
        parents=[common, paid],
        help="ask a research question everywhere and merge the answers' claims and sources",
    )
    research_.add_argument("question")
    research_.add_argument(
        "--runs", type=_positive, default=1, help="runs per provider (default 1)"
    )
    research_.add_argument(
        "--extract", metavar="PROVIDER", default="auto", help="who reads and merges (default: auto)"
    )
    research_.add_argument("--out", type=Path, help="where rounds are saved")
    research_.add_argument("--json", action="store_true", help="print the merged claims as JSON")
    serve = commands.add_parser("mcp", help="serve askround to an agent as an MCP server (stdio)")
    serve.add_argument("--out", type=Path, help="where rounds are saved")
    exp = commands.add_parser("export", help="a product's numbers from the series, for a dashboard")
    exp.add_argument("--product", required=True, metavar="NAME", help="the product to export")
    exp.add_argument("--from", dest="since", metavar="YYYY-MM-DD", default="", help="first day")
    exp.add_argument("--to", dest="until", metavar="YYYY-MM-DD", default="", help="last day")
    exp.add_argument("--format", choices=("csv", "json", "daily"), default="csv")
    exp.add_argument("--key", help="the product's key in --format daily (default: its name)")
    exp.add_argument("--file", type=Path, help="write here instead of printing")
    exp.add_argument("--out", type=Path, help="where rounds are saved")
    report = commands.add_parser(
        "report", help="sum a stored round up: Markdown for a person, JSON for a pipeline"
    )
    report.add_argument(
        "round",
        nargs="?",
        type=Path,
        help="a round's directory or round.json (default: the latest round under --out)",
    )
    report.add_argument(
        "--product",
        action="append",
        dest="products",
        type=_names,
        metavar="NAME[,ALIAS...]",
        help="report on this product (default: the products the round was asked about)",
    )
    report.add_argument("--out", type=Path, help="where rounds are saved")
    report.add_argument("--json", action="store_true", help="print the report as JSON")
    report.add_argument(
        "--brief",
        action="store_true",
        help="the round in a few hundred tokens, each fact with its answers' ids (JSON)",
    )
    doctor = commands.add_parser(
        "doctor", parents=[common], help="say which providers can run here"
    )
    doctor.add_argument(
        "--no-check", dest="check", action="store_false", help="make no network call"
    )
    doctor.add_argument("--json", action="store_true", help="print the report as JSON")
    return parser


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _pin(value: str) -> tuple[str, str]:
    provider, sep, model = value.partition("=")
    if not sep or not provider.strip() or not model.strip():
        raise argparse.ArgumentTypeError("expected PROVIDER=MODEL, e.g. openai=gpt-5")
    return provider.strip(), model.strip()


def _locale(value: str) -> Locale:
    try:
        return Locale.parse(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def _names(value: str) -> list[str]:
    names = [n.strip() for n in value.split(",") if n.strip()]
    if not names:
        raise argparse.ArgumentTypeError("a product needs a name")
    return names


def main(argv: list[str] | None = None, post=None, fetch=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "report":
        return run_report(args)
    if args.command == "lookup":
        return run_lookup(args, post)
    if args.command == "series":
        return run_series(args)
    if args.command == "diff":
        return run_diff(args)
    if args.command == "export":
        return run_export(args)
    if args.command == "mcp":
        from askround import mcp

        mcp.serve(out=str(args.out) if args.out else None)
        return 0
    kwargs = {"post": post} if post is not None else {}
    kwargs["models"] = dict(args.models or [])
    try:
        providers = by_name(args.providers, **kwargs) if args.providers else all_providers(**kwargs)
    except ValueError as error:
        print(f"askround: {error}", file=sys.stderr)
        return 2
    if args.command == "doctor":
        return run_doctor(providers, args.check, args.json)
    if args.command == "run":
        return run_prompt_set(args, providers, post, fetch)
    if args.command == "discover":
        return run_discover(args, providers, post)
    if args.command == "research":
        return run_research(args, providers, post)
    return run_ask(args, providers, post, fetch)


def _budget(est, max_cost: float | None) -> None:
    """Print the estimate; refuse, before anything is paid, a run above the cap (L5)."""
    print(f"askround: {costs.describe(est)}", file=sys.stderr)
    limit = costs.cap(max_cost)
    if limit is not None and est.total > limit:
        raise Refused(
            f"the estimate ${est.total:.4f} is above the cap ${limit:.4f} "
            "(--max-cost or ASKROUND_MAX_COST); nothing was sent"
        )


def run_research(args, providers, post) -> int:
    providers = [p for p in providers if p.configured()]
    try:
        if not providers:
            raise Refused("no provider has an API key in the environment")
        found = private.scan(args.question)
        if found:
            raise Refused(private.refusal("the question", args.question, found))
        try:
            reader = choose(args.extract, **_post(post))
        except ValueError as error:
            raise Refused(str(error)) from None
        _budget(costs.estimate(providers, args.runs, True, reader), args.max_cost)
    except Refused as refusal:
        print(f"askround: {refusal}", file=sys.stderr)
        return 2
    round_ = run_round(args.question, providers, runs=args.runs)
    before = reader.spent
    found = research.merge(args.question, research.read(round_, reader), reader)
    round_.extraction_cost = reader.spent - before
    directory = save_round(round_, _rounds_dir(args.out))
    names = list(dict.fromkeys(r.provider for r in round_.results if r.answer))
    text = research.markdown(args.question, found, names)
    (directory / "research.md").write_text(text, encoding="utf-8")
    data = {
        "schema": schema("research"),
        "question": args.question,
        "providers": names,
        **research.as_json(found),
    }
    (directory / "research.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.json:
        print(json.dumps({**data, "saved": str(directory)}, ensure_ascii=False, indent=2))
    else:
        print(text, end="")
        print(f"\n{_cost_line(cost(round_))}\nsaved: {directory}")
    return 0


def run_discover(args, providers, post) -> int:
    providers = [p for p in providers if p.configured()]
    try:
        if not providers:
            raise Refused("no provider has an API key in the environment")
        try:
            item = product.load(args.file)
            writer = choose(args.extract or "auto", **_post(post))
        except (OSError, ValueError) as error:
            raise Refused(str(error)) from None
        seed = args.seed or (item.questions[0].text if item.questions else "")
        if not seed:
            raise Refused(f"{args.file} has no [[question]]; give a --seed")
        hits = leading.leads(seed, item.names, item.phrases)
        if hits:
            raise Refused(leading.refusal(seed, hits))
        found = private.scan(seed)
        if found:
            raise Refused(private.refusal("the seed", seed, found))
        calls = args.runs * (args.variants + 1)
        _budget(
            costs.estimate(providers, calls, True, writer if args.extract else None), args.max_cost
        )
    except Refused as refusal:
        print(f"askround: {refusal}", file=sys.stderr)
        return 2
    variants, dropped = discover.generate(seed, item, writer, args.variants)
    questions = [product.Question(seed, "seed"), *variants]
    trial = dataclasses.replace(item, questions=questions)
    directory, rounds = sets.run_set(
        trial,
        providers,
        _rounds_dir(args.out),
        runs=args.runs,
        extractor=writer if args.extract else None,
        source=str(args.file),
    )
    ranked = discover.rank(questions, rounds, item.names)
    lines = [f"# Discovery: which question leads to {item.name}", ""]
    lines += ["| rank | score | named | best | axis | question |", "|---|---|---|---|---|---|"]
    for n, r in enumerate(ranked, 1):
        q = r.question
        where = f" ({q.locale})" if q.locale else ""
        best = f"#{r.best}" if r.best else "-"
        named = f"{r.named}/{r.answers}"
        lines.append(f"| {n} | {r.score:.2f} | {named} | {best} | {q.purpose} | {q.text}{where} |")
    lines += [
        "",
        "score: 1/position where it is recommended, 1/2 where only named, over every answer.",
    ]
    if args.runs < 3:
        lines += [
            f"With {args.runs} run(s) per question this is a sketch: answers vary from run to "
            "run. Add the promising questions to the product file and `askround run` them.",
        ]
    if dropped:
        lines += [
            "",
            "Dropped for naming the product or carrying personal data: " + "; ".join(dropped),
        ]
    text = "\n".join(lines) + "\n"
    (directory / "discovery.md").write_text(text, encoding="utf-8")
    if args.json:
        data = {
            "schema": schema("discovery"),
            "product": item.name,
            "saved": str(directory),
            "ranked": [
                {
                    "question": r.question.text,
                    "axis": r.question.purpose,
                    "locale": str(r.question.locale) if r.question.locale else None,
                    "score": round(r.score, 4),
                    "named": r.named,
                    "answers": r.answers,
                    "best": r.best,
                }
                for r in ranked
            ],
            "dropped": dropped,
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(text, end="")
        print(f"\nsaved: {directory}")
    return outcome([r for round_ in rounds for r in round_.results])


def run_prompt_set(args, providers, post, fetch=None) -> int:
    providers = [p for p in providers if p.configured()]
    try:
        if not providers:
            raise Refused("no provider has an API key in the environment")
        try:
            item = product.load(args.file)
        except (OSError, ValueError) as error:
            raise Refused(str(error)) from None
        if not item.questions:
            raise Refused(f"{args.file} has no [[question]] to ask")
        try:
            sets.check(item)
        except ValueError as error:
            raise Refused(str(error)) from None
        try:
            extractor = choose(args.extract, **_post(post)) if args.extract else None
        except ValueError as error:
            raise Refused(str(error)) from None
        _budget(sets.estimate(item, providers, args.runs, args.search, extractor), args.max_cost)
    except Refused as refusal:
        print(f"askround: {refusal}", file=sys.stderr)
        return 2
    get = (fetch or links.fetch) if args.check_links else None
    directory, rounds = sets.run_set(
        item,
        providers,
        _rounds_dir(args.out),
        search=args.search,
        runs=args.runs,
        extractor=extractor,
        get=get,
        source=str(args.file),
    )
    data = report_.build_set(directory / "set.json")
    if args.json:
        print(json.dumps({**data, "saved": str(directory)}, ensure_ascii=False, indent=2))
    else:
        print(report_.set_markdown(data), end="")
        print(f"\nsaved: {directory}")
    return outcome([r for round_ in rounds for r in round_.results])


class Refused(Exception):
    """A run stopped before anything was paid for (law L2)."""


# the exit codes are the contract a script, a hook or a CI job reads
OK, FAILED, REFUSED, PARTIAL = 0, 1, 2, 3


def outcome(results) -> int:
    """OK when every answer came back, PARTIAL when some failed, FAILED when none did."""
    answered = sum(r.ok for r in results)
    if answered == len(results):
        return OK
    return PARTIAL if answered else FAILED


def _preflight(args, providers, post):
    """Everything that could refuse, decided before the round: the providers that can
    run, the product files, the products and the extractor."""
    providers = [p for p in providers if p.configured()]
    if not providers:
        raise Refused(
            "no provider has an API key in the environment "
            "(OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, PERPLEXITY_API_KEY)"
        )
    try:
        files = [product.load(path) for path in args.product_files or []]
    except (OSError, ValueError) as error:
        raise Refused(str(error)) from None
    products = [*(args.products or []), *(f.names for f in files)]
    _check_question(args.question, products, [p for f in files for p in f.phrases], args.brand)
    if args.check_rivals and not args.extract:
        raise Refused("--check-rivals reads the rivals from --extract; add it")
    if args.check_links and not products:
        raise Refused("--check-links follows a --product's links; name one")
    try:
        extractor = choose(args.extract, **_post(post)) if args.extract else None
    except ValueError as error:
        raise Refused(str(error)) from None
    calls = args.runs * max(1, len(args.locales or []))
    est = costs.estimate(providers, calls, args.search, extractor)
    _budget(est, args.max_cost)
    args.estimate = costs.as_dict(est)
    return providers, files, products, extractor


def _check_question(question: str, products, phrases, brand: bool) -> None:
    """No personal data (private.py), and no naming the product unless on purpose."""
    found = private.scan(question)
    if found:
        raise Refused(private.refusal("the question", question, found))
    if brand:
        return
    hits = [t for names in products for t in leading.leads(question, names, phrases)]
    if hits:
        raise Refused(leading.refusal(question, list(dict.fromkeys(hits))))


def _after(args, round_, files, products, extractor, post, fetch) -> None:
    """The passes over a round that already answered."""
    if extractor is not None:
        before = extractor.spent
        extract_round(round_, extractor)
        for f in files:
            if f.facts:
                round_.gaps[f.name] = gaps.compare(round_, f, extractor)
        round_.extraction_cost = extractor.spent - before
    if args.check_rivals:
        top = rivals(round_, products).rivals[: args.check_rivals]
        web = lookup.web_lookup(**_post(post))
        verdicts = lookup.check([v.name for v in top], args.question, web=web, **_post(post))
        round_.checks = {rival_key(v.name): v for v in verdicts}
    if args.check_links:
        for names in products:
            round_.links[names[0]] = links.check_links(round_, names, **_fetch(fetch))


def run_ask(args, providers, post, fetch=None) -> int:
    try:
        providers, files, products, extractor = _preflight(args, providers, post)
    except Refused as refusal:
        print(f"askround: {refusal}", file=sys.stderr)
        return 2
    round_ = run_round(
        args.question, providers, search=args.search, runs=args.runs, locales=args.locales
    )
    round_.brand = args.brand
    round_.estimate = args.estimate
    _after(args, round_, files, products, extractor, post, fetch)
    directory = save_round(round_, _rounds_dir(args.out), products)
    if args.json:
        data = {**summary(round_, products), "saved": str(directory)}
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render(round_, directory, products))
    return outcome(round_.results)


def _rounds_dir(out: Path | None) -> Path:
    return out or Path(os.environ.get("ASKROUND_DIR", ".askround/rounds"))


def _post(post) -> dict:
    return {"post": post} if post is not None else {}


def _fetch(fetch) -> dict:
    return {"get": fetch} if fetch is not None else {}


def run_lookup(args, post) -> int:
    for text in [*args.names, args.context]:
        found = private.scan(text)
        if found:
            print(f"askround: {private.refusal('the lookup', text, found)}", file=sys.stderr)
            return 2
    web = lookup.web_lookup(**_post(post)) if args.web else None
    verdicts = lookup.check(args.names, args.context, web=web, **_post(post))
    if args.json:
        data = {"schema": schema("lookup"), "verdicts": [v.__dict__ for v in verdicts]}
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for v in verdicts:
            where = f" <{v.url}>" if v.url else ""
            print(f"{v.name}: {v.status.replace('_', ' ')}{where}")
            if v.evidence:
                print(f"    {v.evidence} ({v.via or 'no lookup'})")
    return 0


def run_export(args) -> int:
    items = export.rows(series.load(_rounds_dir(args.out)), args.product, args.since, args.until)
    if args.format == "csv":
        text = export.to_csv(items)
    elif args.format == "json":
        data = {"schema": schema("export"), "product": args.product, "rows": items}
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    else:
        key = args.key or args.product.lower()
        text = json.dumps(export.daily(items, key), ensure_ascii=False, indent=2) + "\n"
    if args.file:
        args.file.write_text(text, encoding="utf-8")
        print(f"exported {len(items)} rows to {args.file}")
    else:
        print(text, end="")
    return 0


def run_diff(args) -> int:
    out = _rounds_dir(args.out)
    try:
        if args.old and args.new:
            old = report_.find_round(args.old, out)
            new = report_.find_round(args.new, out)
        elif args.old or args.new:
            raise FileNotFoundError("give both rounds to compare, or neither for the latest two")
        else:
            old, new = diff.latest_pair(out)
        changes = diff.compare(old, new, args.product)
        only = diff.unmatched(old, new)
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"askround: {error}", file=sys.stderr)
        return 2
    if args.json:
        data = {
            "schema": schema("diff"),
            "old": str(old),
            "new": str(new),
            "changes": [c.__dict__ for c in changes],
            "only_old": only[0],
            "only_new": only[1],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(diff.markdown(changes, old, new, only), end="")
    return 0


def run_series(args) -> int:
    out = _rounds_dir(args.out)
    if args.rebuild:
        skipped: list[str] = []
        print(f"series rebuilt: {series.rebuild(out, skipped)} answers from the rounds under {out}")
        for line in skipped:
            print(f"  skipped {line}", file=sys.stderr)
        if not args.product:
            return 0
    if not args.product:
        print("askround: name the product to follow with --product", file=sys.stderr)
        return 2
    table = series.frequency(series.load(out), args.product, args.by, args.question)
    if args.json:
        data = {
            "schema": schema("series"),
            "product": args.product,
            "by": args.by,
            "periods": table,
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if not table:
        print(f"no answers tracked {args.product} under {out}; ask with --product first")
        return 0
    providers = sorted({p for cells in table.values() for p in cells})
    print(f"{args.product}: answers naming it, by {args.by}")
    print("| " + args.by + " | " + " | ".join(providers) + " |")
    print("|---|" + "---|" * len(providers))
    for period, cells in table.items():
        shown = []
        for p in providers:
            cell = cells.get(p)
            shown.append(f"{cell['named']}/{cell['answers']}" if cell else "-")
        print(f"| {period} | " + " | ".join(shown) + " |")
    return 0


def run_report(args) -> int:
    try:
        path = report_.find_round(args.round, _rounds_dir(args.out))
        if path.name == "set.json":
            data = report_.build_set(path)
            text = report_.set_markdown(data)
        else:
            round_, asked = report_.load_round(path)
            if args.brief:
                found = report_.brief(round_, args.products or asked, str(path.parent))
                print(json.dumps(found, ensure_ascii=False, separators=(",", ":")))
                return 0
            data = report_.build(round_, args.products or asked, str(path))
            text = report_.markdown(data)
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"askround: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(text, end="")
    return 0


def run_doctor(providers, check: bool, as_json_: bool) -> int:
    statuses = diagnose(providers, check=check)
    if as_json_:
        data = {"schema": schema("doctor"), "providers": [_status_json(s) for s in statuses]}
        print(json.dumps(data, indent=2))
    else:
        print(render_doctor(statuses))
    return 0 if any(s.can_run for s in statuses) else 2


def _status_json(s: Status) -> dict:
    return {
        "provider": s.provider,
        "model": s.model,
        "search_tool": s.search_tool,
        "key_var": s.key_var,
        "checked": s.checked,
        "ok": s.ok,
        "can_run": s.can_run,
        "detail": s.detail,
    }


def render_doctor(statuses: list[Status]) -> str:
    rows = [("provider", "key", "model", "search", "status")]
    for s in statuses:
        mark = "ok" if s.ok else ("-" if not s.checked else "FAIL")
        status = s.detail if s.detail == "ok" else f"{mark}: {s.detail}"
        rows.append((s.provider, s.key_var or "-", s.model, s.search_tool, status))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    lines = [
        "  ".join(cell.ljust(w) for cell, w in zip(row[:4], widths, strict=True)) + "  " + row[4]
        for row in rows
    ]
    can = [s.provider for s in statuses if s.can_run]
    lines.append("")
    lines.append(f"can run: {', '.join(can)}" if can else "no provider can run")
    return "\n".join(lines)


def render(round_: Round, directory: Path, products: list[list[str]] | None = None) -> str:
    lines = [f"Q: {round_.question}", ""]
    if not round_.search:
        lines[0] += "  (web search off)"
    for r in round_.results:
        run = f", run {r.run}/{round_.runs}" if round_.runs > 1 else ""
        lines.append(f"=== {r.provider} ({_model(r)}{run}){_place(r)} ===")
        lines.extend(_answer_lines(r.answer) if r.answer else [f"[error] {r.error}"])
        lines.append("")
    for names in products or []:
        lines.extend(_frequency_lines(round_, names))
        lines.append("")
    lines.extend(_rival_lines(round_, products or []))
    failed = failures(round_)
    if failed:
        lines.append(f"failed: {len(failed)} of {len(round_.results)} answers")
        for r in failed:
            where = f" {r.locale}" if r.locale else ""
            lines.append(f"  {r.provider}{where} run {r.run}: {r.error}")
        lines.append("")
    lines.append(_cost_line(cost(round_)))
    lines.append(f"saved: {directory}")
    return "\n".join(lines)


def _cost_line(spent: dict) -> str:
    """'cost: $0.0412 (openai $0.0301, ...), estimated $0.05' from round.cost()."""
    actual = spent["actual"] or {}
    parts = ", ".join(
        f"{k} ${v:.4f}" if v is not None else f"{k} (no price)" for k, v in actual.items()
    )
    total = f"${spent['total']:.4f}" if spent["total"] is not None else "unknown"
    estimate = spent["estimate"]
    guessed = f", estimated ${estimate['total']:.4f}" if estimate else ""
    return f"cost: {total} ({parts or 'nothing billed'}){guessed}"


RIVALS_SHOWN = 10


def _rival_lines(round_: Round, products: list[list[str]]) -> list[str]:
    found = rivals(round_, products)
    if not found.read or not found.rivals:
        return []
    title = "rivals" if products else "recommended"
    lines = [f"{title} (in {found.read} answers read):"]
    for rival in found.rivals[:RIVALS_SHOWN]:
        ranks = ", ".join(f"#{rank}" for rank in rival.ranks)
        by = ", ".join(f"{p} {n}" for p, n in rival.providers.items())
        verdict = round_.checks.get(rival_key(rival.name))
        tag = f"   [{verdict.status.replace('_', ' ')}]" if verdict else ""
        lines.append(
            f"  {rival.name:<24} {rival.answers}/{found.read}   ranks: {ranks}   ({by}){tag}"
        )
    hidden = len(found.rivals) - RIVALS_SHOWN
    if hidden > 0:
        lines.append(f"  ... and {hidden} more in round.json")
    lines.append("")
    return lines


def _model(r) -> str:
    served = r.answer.served_model if r.answer else ""
    return f"{r.model} -> {served}" if served and served != r.model else r.model


def _place(r) -> str:
    if r.locale is None:
        return ""
    ignored = r.answer.locale_ignored if r.answer else []
    note = f", {' and '.join(ignored)} ignored by the API" if ignored else ""
    return f" [{r.locale}{note}]"


def _frequency_lines(round_: Round, names: list[str]) -> list[str]:
    lines = [f"{names[0]}: named in"]
    extracted = False
    for f in frequency(round_, names):
        marks = ["*" if by == "extraction" else "" for by in f.ranked_by]
        extracted = extracted or any(marks)
        places = ", ".join(
            "-" if p is None else f"#{p}{mark}" for p, mark in zip(f.positions, marks, strict=True)
        )
        where = f"{str(f.locale):<9}" if round_.locales else ""
        lines.append(
            f"  {f.provider:<11} {where}{f.share} runs   positions: {places or '-'}   ({f.model})"
        )
    if extracted:
        lines.append("  * ranked by the extraction pass")
    lines.extend(_claim_lines(round_, names))
    lines.extend(_cited_lines(round_, names))
    lines.extend(_gap_lines(round_, names[0]))
    lines.extend(_link_lines(round_, names[0]))
    return lines


def _gap_lines(round_: Round, product: str) -> list[str]:
    found = round_.gaps.get(product)
    if found is None:
        return []
    if not found:
        return [f"{product}: no fact gaps; every claim compared agrees with its facts"]
    lines = [f"{product}: fact gaps"]
    for g in found:
        by = ", ".join(f"{p} {n}" for p, n in g.providers.items())
        lines.append(f'  {g.attribute}: {g.value}   ({by})  {g.verdict} "{g.fact}"')
        lines.append(f"      {g.why}")
        if g.page:
            lines.append(f"      say it plainly on {g.page}")
    return lines


def _link_lines(round_: Round, product: str) -> list[str]:
    checks = round_.links.get(product)
    if checks is None:
        return []
    wrong = [c for c in checks if c.verdict != "ok"]
    lines = [f"{product}: links given for it, {len(checks)} followed, {len(wrong)} not its own"]
    for c in wrong:
        lands = (c.title or c.final_url) if c.status else "unreachable"
        lines.append(f"  {c.provider} run {c.run}: {c.url}")
        lines.append(f"      {c.verdict}: {lands}")
    return lines


def _claim_lines(round_: Round, names: list[str]) -> list[str]:
    found = product_claims(round_, names)
    if not found:
        return []
    lines = [f"{names[0]}: what the answers claim"]
    for c in found:
        if c.answers:
            by = ", ".join(f"{p} {n}" for p, n in c.providers.items())
            lines.append(f"  {c.attribute}: {c.value}   ({by})")
            lines.append(f'      "{c.quote}"')
    unverified = sum(c.unverified for c in found)
    if unverified:
        lines.append(f"  ({unverified} more not found in the answer's text, in round.json)")
    return lines


def _cited_lines(round_: Round, names: list[str]) -> list[str]:
    if not citations.places(names):
        return [
            f"  (give {names[0]}'s domain, e.g. --product {names[0]},example.com, to see "
            "which of its pages are cited)"
        ]
    lines = [f"{names[0]}: its pages cited in"]
    for c in citations.product_citations(round_, names):
        kinds = ", ".join(f"{k} {n}" for k, n in sorted(c.kinds.items())) or "none"
        lines.append(f"  {c.provider:<11} {c.citing}/{c.answers} answers   ({kinds})")
        for page, n in sorted(c.pages.items(), key=lambda kv: -kv[1]):
            lines.append(f"      {n}x {page}")
    return lines


def _answer_lines(answer: Answer) -> list[str]:
    lines = [answer.text]
    if answer.recommendations:
        named = [rec.name + ("" if rec.verified else " (?)") for rec in answer.recommendations]
        lines += ["", "recommends: " + ", ".join(f"{i}. {n}" for i, n in enumerate(named, 1))]
    elif answer.extraction_error:
        lines += ["", f"[extraction failed] {answer.extraction_error}"]
    if answer.sources:
        lines += ["", "sources:"]
        lines += [f"  - {s.title} <{s.url}>" if s.title else f"  - {s.url}" for s in answer.sources]
    return lines
