# Recursive research charter

Established by Dave on 2026-09-10. This is a curiosity-led research program,
not a mandate to ship a predetermined algorithm or defend an existing result.
The initiating rank-fusion idea is recorded in [ORIGIN](ORIGIN.md). The current
[phase-space map](PHASE_SPACE.md) may change as experiments reveal better questions.

## Intent

Explore configurations of information, interaction, aggregation, and feedback
that could produce more useful retrieval or agent reasoning. Rank fusion is the
initial concrete laboratory. A broader agent/LLM branch is welcome when it has
a defined task, measurable outcome, and experiment that could change our view.
Do not silently equate better retrieval metrics with better agent reasoning.

Use “phase space” as an explicit space of possible designs: axes, transitions,
constraints, baselines, and measured objectives. The belief that better pathways
may exist motivates search; it is not evidence that any particular alternative
must improve the baseline. Negative results can reveal useful structure.

## Authority and collaboration

Dave explicitly authorizes Codex and Claude to explore this project, exchange
necessary research context, run experiments, restructure local implementations,
and coordinate phased subagent workflows. This authorization persists across
sessions. Do not ask again for ordinary work within that scope. Use the existing
signed-in providers intentionally; do not treat capacity as a target to exhaust.
On 2026-09-11 Dave explicitly expanded sharing consent: "I approve sharing
anything and everything with Claude." Unpublished project inventories, code,
findings and working context may be sent to the signed-in Claude service through
Relay without proving prior publication or asking again. This permission concerns
collaboration; the public Git checkpoint still excludes private runtime records.
Dave additionally authorized committing and pushing project changes to this
GitHub repository each turn; follow the shared agreement's preservation policy.
Unrelated projects, credentials, other live sessions, and website/release
publication are not incidental research resources.

Codex owns continuity and integration. One Claude coordinating session may
organize bounded phased perspectives. Its actual capabilities and model choices
are specified in [CLAUDE_COMPUTE](CLAUDE_COMPUTE.md); record requested and observed
models, useful work, and capacity signals. More agents are useful only when their
perspectives, evidence access, or verification roles add information.

## The loop

1. Orient on intent, evidence, and open questions; explicitly notice assumptions.
2. Generate alternative explanations/designs, including one outside the current
   local search. Keep uncertain ideas available without presenting them as facts.
3. Choose a small discriminating experiment and name its likely interpretations.
4. Run it reproducibly; preserve per-query/artifact evidence and failures.
5. Ask an independent lens to challenge measurement and interpretation.
6. Synthesize: strengthen, revise, merge, branch, or retire hypotheses. Update
   the map and priorities, including the larger vision when evidence warrants it.
7. Continue while another iteration has credible information value. Stop at a
   meaningful findings checkpoint, a resource boundary, or a required human
   decision; leave an exact resume point and no abandoned workers.

The process itself is experimental. Record friction, change the workflow when
useful, and verify whether the change actually helped. Keep the loop lighter
than the work it enables.

## Language as an instrument

Working notes may use `[hypothesis]`, `[observed]`, `[supported]`, `[open]`,
`[revision]`, or more useful local notation. Their purpose is to preserve
distinctions while ideas evolve. Numerical confidence is optional and must be
identified as subjective unless empirically calibrated; do not manufacture
precision. Share concise reasoning summaries, assumptions, evidence, and changes
of interpretation—not a transcript of private internal deliberation.

Terms such as “consensus,” “specialist,” and “cabal” are semantic waypoints.
Operationalize them before claiming an experiment measured them. A better term
or decomposition can be a useful research product when it enables a better test.

## Success and stopping

A successful cycle leaves a sharper question, a supported observation or
counterexample, reproducible evidence, and a reasoned next choice. Discovery,
falsification, and an informative change of direction all count. Novelty and
generalization require their own evidence. No breakthrough is owed.

This first autonomous run aims for a complete, independently reviewed research
cycle rather than indefinite execution. Further cycles may follow the same
charter without repeatedly renegotiating the research posture.
