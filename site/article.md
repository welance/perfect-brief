# The Perfect Digital Product Brief

*A modest proposal for starting a build on the right foot.*

A digital product's success is maybe 20% the brief and 80% the team. So why would we spend our time on the 20%?

Because the brief is where the 80% is won or lost before it starts. A team can only be as good as the reality it's handed. A brief's real job isn't to be eloquent — it's to give the people who'll build the thing a solid grip on three things: **reality** (what problem, for whom, measured how), **doability** (what's in, what's out, what constrains it), and **scalability** (what it must hold up to once it's real). Get those right and a good team flies. Get them wrong and the best team in the world spends the first month renegotiating what you actually meant.

The usual fix for a thin brief is a workshop — get everyone in a room and rewrite it together. That works, but it's heavy, and it quietly makes us the gatekeepers of what "good" means. We wanted something lighter and more honest: a way to check a brief that anyone can read, anyone can argue with, and anyone can improve.

## So we built an open scorer

Two halves, with a wall between them.

On one side, an **open ruleset**: the things a good brief does, written in plain files, each with its reasoning and a verifiable source. On the other, an **LLM** that reads your brief and judges, criterion by criterion, whether each is met — and points at the evidence. The model judges; it never decides the score. All the weighing and the arithmetic happen in code, in the open, the same way every time.

That wall is the whole point. It means a score isn't a black box: you can take any result apart and see exactly which rules fired and why. It means the bar can be *argued with* — "we should care more about measurable outcomes" is a one-line change to a file, reviewed like any other code, not a mood buried in a prompt. And it means the model's fluency can't flatter an empty brief, because every criterion is anchored to something checkable.

## Not a grade — a progress bar

When you run a brief through it, you don't get a verdict on your worth. You get a number, a band, and — more useful — a short list: what already works (we say so plainly), and what would raise the brief, each with a concrete rewrite and a source you can check. And one line that matters most: *the single change that would cross the next threshold.* The number is a progress bar toward publication, not a report card.

On welance/Directory, the bands map to a simple gate: **75 and up** is published without reservation; **40 to 74** is published, pending a human or community check; **below 40** isn't accepted yet — refine and resubmit, as many times as you like.

## Open, because we have skin in the game

We run the Directory *and* the bar that gates it. That's a conflict of interest, and we know it. The answer isn't to ask you to trust us — it's to make the bar impossible to rig quietly. So the whole ruleset is open source on GitHub. Anyone can propose a change. Whether it's accepted is decided by a public set of example briefs in CI, not by whether we like it. And if you ever think the bar is unfair, you can fork it and run your own. That exit keeps everyone honest better than any promise we could make.

We're not the gatekeepers of the good brief. The public examples are.

## What a good brief does — the nine

The ruleset will grow, but it starts here. A strong brief:

1. **States the problem before the solution** — who feels it, what it costs today.
2. **Names the users specifically** enough to actually design for them.
3. **Defines success as a measurable outcome**, not a deliverable.
4. **Makes deliverables concrete** — each one checkable by a third party.
5. **States what's out of scope**, not only what's in.
6. **States the real constraints** — budget, timeline, stack, integrations.
7. **Surfaces its assumptions and risks** — names at least one of each.
8. **Names the data/privacy basis** when personal data is in play (GDPR, DPA).
9. **Makes accessibility an explicit expectation** — a named bar, not an afterthought.

None of these is exotic. Together they're the difference between a brief that gives a team a fighting start and one that hands them a month of guessing.

## What's deliberately missing — your first PR

There's an obvious tenth rule we left out on purpose: **name one accountable decision-maker.** A brief with no single owner of "yes" stalls the moment two stakeholders disagree. We think it belongs — but rather than ship it ourselves, we left it as an open invitation. It's a clean first pull request: a rule file, two or three example briefs, a source on accountability (RACI, the *single wringable neck*). If you've read this far, the repo is waiting.

## Try it

Submit your brief to welance/Directory and see where it lands. Or just run it to sharpen a brief before you send it to anyone — that's the part we're actually proud of. And if you think a rule is wrong, the repo is open: tell us why, in a pull request.

*The scorer is open source. The bar is forkable. The good brief belongs to everyone who has to build from it.*
