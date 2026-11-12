---
description: What changed between two runs of the same questions
argument-hint: "[old round] [new round]"
allowed-tools: mcp__askround__askround_diff, mcp__plugin_askround_askround__askround_diff
---

Compare two runs of the same questions, asking no provider: $ARGUMENTS

Use `askround_diff`, with `old` and `new` set from the arguments when they name rounds, and
without them for the latest round against the one before it. Report what moved: shares
won or lost, rivals that appeared or left, cited pages and claims that changed. A change
within the spread of a few runs is noise, so say how many runs each side had.
