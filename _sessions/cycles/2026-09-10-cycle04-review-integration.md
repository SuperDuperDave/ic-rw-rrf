# Cycle04 review — verified results, a redundant branch, and corrected critique

## Execution and evidence

A fresh Fable5.1 coordinator with one Opus5 scout reviewed the frozen contract,
code, exact results and independent receipt. Native execution succeeded in
370.6 seconds, exit0, with $2.52308675 list-price accounting under the unchanged
$4 invocation cap. This is not subscription billing. The shorter context was a
new scoped handoff; the older coordinator transcript remains available privately.
Different review scopes prevent interpreting the cost difference as a controlled
efficiency comparison.

Native messages confirm `claude-fable-5-1` and `claude-opus-5`; the Opus usage
key includes `[1m]` and its canonical model is Opus5. The coordinator selected
an `opus` alias override despite the pinned agent definition; native metadata
resolves the identity. Its prose saying the scout ID was unverified is superseded
by that metadata. One scout was dispatched. The final memo exceeded its advisory
1,000-word target (1,096 words); native turn and spend limits succeeded.

Automatic approval review initially treated authorization as limited to the
old audit. Read-only inspection established the current synthetic artifact scope
and Dave's later ongoing Claude-collaboration authorization. The identical
bounded command was then accepted. No alternate egress path or new permission
was used; no provider launched from the rejected attempt.

Relay request25 supplied marker `cycle04-review-cca669293e`. Startup26,
turn-completed27 and session-ended28 match native session
`3aa95d47-60aa-4387-91a5-7020b8d04744`. After reading the complete request and
memo, Codex recorded the requested ACK29 for that exact session. This is a
coordinator-recorded consumption acknowledgement, not a Claude shell action or
automatic peer wakeup. [Receipt](../evidence/2026-09-10-cycle04-review-receipt.json)
preserves reviewed artifact hashes, requested/observed models and native status.
Raw transcripts stay ignored.

## Accepted findings

- No consequential arithmetic or input-leakage defect was found. The independent
  checker reconstructed every numerical field; code/tests separately establish
  the runtime packet boundary. A review agreement does not replace that evidence.
- Make the classification rules explicit: in the strong setting, optimal blind
  Bayes always chooses the specialist's sign. In the weak setting it chooses the
  sole generalist when padded, the common generalist sign when copied, and the
  generalist majority when independent. Its probability output still integrates
  the available observations. Accuracy cannot distinguish all those probabilities.
- The strong aware-versus-blind classification change is confined to unanimous
  independent generalists opposing S (both sign orientations). This is a designed
  threshold crossing under the fixed model; the report already disclaimed real
  coordination performance, and now makes the mechanism more explicit.
- The protected-minority trigger requires **three** non-null generalist reports.
  Padded packets contain one and cannot trigger it. The frozen wording already
  states this; add a presentation clarification, not a changed diagnostic or
  rerun. A proposed alternative rule would be a different experiment.
- Retire the candidate common-cause numerical run. At lambda=1/2 its marginalized
  truth/payload law equals the existing copied/independent mixture conditioned
  on non-null packets. Its two proposed policies correspond to existing blind
  Bayes and naive independence. Different root/cost metadata give a useful
  conceptual boundary but do not create new numerical evidence for those losses.

## Corrected or declined reviewer claims

**The prior threshold is correct; the claimed disappearance of the gain is not.**
Let w be the copied construction's prior share after conditioning on non-null
packets, *before observing their sign pattern*. It is not the posterior copy
probability after seeing unanimous answers. The unanimous-generalist likelihood
ratio is `(343+357w)/(27+273w)`. Against strong-S odds17/3, the decision switches
at `w=19/119`. Both Claude reviewers accepted the further claim that the
classification advantage vanishes below that threshold.

An independent algebra audit instead gives, conditional on non-null packets,

`error(blind)-error(aware) = min(3w/20, 57(1-w)/2000)`.

Below the threshold the benefit moves to the copied arm: blind follows unanimous
G, while aware copies still defer to strong S. Above it the benefit occurs in
the independent arm. It is positive for every `0<w<1`, and only vanishes at
the endpoints. For example w=1/10 gives3/200 conditional benefit, or1/100 when
retaining padded prior1/3. The fair tie preserves the continuous formula at the
threshold. This is post-result algebra, not a prior sweep or changed primary
experiment. No numerical artifact or frozen design was altered.

**Effect location is not unmatched acquisition confounding.** The information
benefit is concentrated in a particular arm, but aware and blind are evaluated
on exactly the same fixed construction mixture, packets and acquisition counts.
Do not describe their difference as caused by giving the aware policy extra
primitive observations. Trusted lineage itself is the declared extra input.
Separate varying effects across constructions from changing resources between
policies. Generalization beyond this specified mixture remains unestablished.

**The one-pattern statement applies to aware-versus-blind class changes.** It
does not apply to every comparator. For example equal-root weighting differs
from blind Bayes even on weak-S padded conflicts. Nor does a simple class rule
make the primary probability comparison meaningless: Brier loss measures the
probabilities that a hard decision discards.

**Do not turn an arbitrary tolerance into a general capability test.** Claude
suggested declaring success at9/12 aware responses within.05 of exact Bayes.
That can define an operational screen, but its failure cannot logically refute
general use of assumptions. The next design retains continuous posterior error,
paired probability contrasts, parsing failures and explicit denominators instead.
The proposed 20-request measurement has no model-repeat sampling guarantee.

## Next decision

Select [cycle05 coordinator packets](2026-09-10-cycle05-coordinator-packet-design.md):
one fixed Opus5 configuration,12 unique aware plus8 blind inputs, isolated
contexts, exact references, a bounded batch and no prompt/model search or retries.
The original [common-cause candidate](2026-09-10-cycle05-common-cause-design.md)
is retained as a retired proposal and derived information boundary. Neither
experiment ran during cycle04. The next coordinator must freeze request bytes,
observation weights, parsing and verified native context/resource controls
before the first empirical response.
