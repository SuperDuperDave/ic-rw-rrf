# IC(R/W)-RRF — agent working agreement

This is an exploratory rank-fusion research project. The question is how much
signal can be recovered from ranker agreement, disagreement, document identity,
and optional scores. A supported improvement, a useful counterexample, and a
well-explained negative result are all worthwhile outcomes. Follow promising
ideas, but distinguish measured evidence from a proposed mechanism or novelty.

## Initialize and resume

Read `_sessions/RESEARCH_CHARTER.md` for Dave's standing autonomous research
intent and `_sessions/PHASE_SPACE.md` for the evolving hypothesis/design map.
The research may reconfigure its direction; the backlog is a proposal, not a
requirement to keep tuning RRF when better questions emerge.

1. Read `_sessions/WORKFLOW.md`, `_sessions/MAP.md`, and
   `_sessions/PLANNING.md` (surface any unresolved **NEEDS DAVE** item).
2. Read `_sessions/RESEARCH_STATE.md` and the latest relevant stream. On resume,
   read the current stream's Resume and recent evidence before continuing.
3. Run `python3 _sessions/tools/session.py status`; preserve existing dirty and
   untracked work. Start one coordinating stream with
   `python3 _sessions/tools/session.py start <short-slug>` if this task has none.
   Continue that stream through compaction; do not create duplicate journals.
4. Consult `_sessions/RELAY.md` for project-local collaboration. Reconcile scope
   with any live ownership before assigning overlapping work.

`AGENTS.md` is the shared operating agreement; `CLAUDE.md` is its Claude entry
point. These ordinary repository files work without sibling repos, personal
memory, or private skills. Historical `.claude/skills` links are optional craft
resources, never prerequisites for initialization.

## Research discipline

- Write down the hypothesis, distinguishing prediction, baseline, data/ranker
  configuration, primary metric, and stopping rule before an experiment.
- Prefer the smallest experiment that distinguishes competing explanations.
  Keep a place for surprising ideas; expand scope when evidence warrants it.
- Before comparing scores, align rank origin, tie handling, candidate pools,
  query eligibility, qrels, and evaluation code. Record seeds and exact commands.
- Separate unsupervised inference, labeled development/tuning, within-corpus
  selection, and cross-corpus transfer. Oracle results are upper bounds.
- Reusing queries across ranker ensembles does not create independent samples.
  Hyperparameter/architecture search needs untouched evaluation or nested
  selection; repeated CV seeds do not create additional labeled queries.
- Report the comparator for every delta and p-value. Describe current p-values
  as exploratory where selection or approximation affects interpretation.
- Do not turn a local failure into an impossibility claim, or a local win into
  general superiority. Verify prior work before asserting novelty.
- Keep the standard-library demo working. Optional research dependencies need
  a specific purpose; do not replace the harness merely for convenience.
- For a research promotion, update hypothesis/spec → implementation → evidence
  and results → public narrative. Historical notebooks/specs are dated evidence;
  corrections belong in current summaries with pointers to the original.

## Collaboration and completion

Delegate bounded independent tasks with file ownership, constraints, and an
expected evidence artifact. Ordinary child agents return findings to the
coordinator; they do not create duplicate streams or edit the shared backlog.
Only send necessary project context through Relay. Keep runtime ledgers and
provider transcripts out of version control. Delivery, consumption, review,
and completion are different events.

Dave explicitly authorized ongoing Codex/Claude research collaboration and
phased subagents on 2026-09-10. Apply `_sessions/CLAUDE_COMPUTE.md` for intentional
model use; preserve this authorization rather than adding recurring approval
questions. Speculative notes may use qualitative evidence markers; do not
present subjective confidence numbers as calibrated probabilities.

Record friction when encountered. At wrap classify each item **SUBTRACT**,
**PROMOTE**, or **DROP**, route it to one durable home, and distinguish a landed
fix from observed improvement. Do the clear fixes within the authorized scope.
Update the backlog bodies; stream carryforward is a short list of pointers.
Report checks run, limitations, unfinished work, and any live collaborator.

## Preserve work each turn

Dave explicitly authorized committing and pushing this project's changes to its
GitHub repository each turn on 2026-09-10. Before ending a turn with project
changes, the coordinator reviews the staged work, runs appropriate checks,
commits the changes, and pushes to the current branch's configured upstream.
Verify the push and report the commit. Do not ask for this permission again.
If nothing changed, no empty commit is needed. If the push fails, preserve the
local commit and report the actual blocker; never claim an unverified push.

Include durable research code, protocols, results, notes, and workflow updates.
Keep ignored Relay state, raw provider transcripts, credentials, and local
scratch files excluded. Bounded workers return their changes to the coordinator
and do not independently commit shared work unless assigned that ownership.
Reconcile concurrent changes before committing; do not overwrite or force-push
another contributor's work. GitHub checkpoints are authorized; website
publication, release operations, and other projects' changes remain separate.
