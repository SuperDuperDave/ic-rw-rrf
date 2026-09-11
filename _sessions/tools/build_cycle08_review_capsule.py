from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
base = root / 'results/cycle08-2026-09-10/prepared'
panel = json.loads((base / 'panel.json').read_text())
manifest = json.loads((base / 'manifest.json').read_text())
lines = ['''# Cycle08 interpretation review

You are Fable5.1, Dave's scientific collaborator in curiosity-led rank-fusion
and agent research. Review only this capsule; tools/MCP/agents are disabled.
Give a concise evidence assessment and recommend ONE next discriminating
checkpoint, with an alternative explanation, observable and stopping rule.
Target350 words. Return the marker delivered through Relay and request Codex's
consumption ACK; do not invent a marker if absent. This is interpretation work,
not an experimental solver observation. Do not solve the programs for a new
measurement or request reserved data.

Origin: distinguish useful specialist dissent from noise and repeated copies
of evidence. Retrieval experiments had narrow/confounded results. An exact
finite binary model separated copy lineage, calibration and error dependence;
actual Opus responses closely reproduced its supplied Bayesian probabilities.
That measured use of stipulated numbers, not discovery of evidence reliability.
An uncertain-lineage pilot stayed incomplete after a provider refusal. Cycle07
then obtained16 valid answers on8 simple programs, two separate solver prompts:
both were all correct. Its error-variation gate failed;16 reserves remain unsent.

Cycle08 is LOCAL ONLY. Before enumeration, a committed design fixed four fresh
operator templates and a matched N=4 versus64 intervention. A Python RNG seed,
operator order and32-attempt cap selected the first4 syntactically valid,
bounded, structurally novel templates. We did not replace candidates based on
their answers/traces. Old data supplied only structural hashes for exclusion.
Actual instrumented Python plus a separate AST interpreter agree on sources,
states, branches, truths, counts and candidate order. No provider solved these.
The within-pair contrast changes only N; the whole family differs from cycle07.

Park if fewer than4 templates, any custody/truth failure, all8 Boolean answers
equal, any identical final(a,b,c) acrossbounds, a repeated full state within64
iterations, or a demonstrated shortcut making N irrelevant. Finite constant
Boolean traces and equal endpoint Booleans alone were explicitly descriptive
before enumeration. The actual records follow, generated directly from artifacts.
''']
lines += [f"Prepared manifest SHA256: `{hashlib.sha256((base/'manifest.json').read_bytes()).hexdigest()}`.", '',
          f"Candidates: {panel['generation']['attempt_count']}; accepted templates: {len(panel['templates'])}; programs: {len(panel['items'])}.",
          'Local decision: `' + panel['decision']['status'] + '`; reasons: `' + json.dumps(panel['decision']['park_reasons']) + '`.', '',
          '| Operators | N=4 truth / steps | N=64 truth / steps | First cycle | Same final triple | Constant prefix truth |',
          '| --- | --- | --- | --- | --- | --- |']
for template in panel['templates']:
    items = {row['n']: row for row in panel['items'] if row['template_id'] == template['template_id']}
    fields = [' / '.join(template['operators'])]
    for n in (4, 64):
        record = items[n]['python_truth']
        fields.append(f"{str(record['answer']).lower()} / {record['executed_statements']}")
    audit = template['audit']
    fields += [json.dumps(audit['first_cycle']), str(audit['same_final_state']).lower(), str(audit['constant_prefix_answer']).lower()]
    lines.append('| ' + ' | '.join(fields) + ' |')
lines += ['', 'One actual source (first item); its answer/count appears in the table:', '', '~~~python',
          panel['items'][0]['program'].rstrip(), '~~~', '''
Source review found an exact partial reduction: when OP2 is minus, the final a
equals (b_old*c_old)%997 from just before the last iteration. When OP2 is plus,
it equals (b_old*c_old+2*a_new)%997. These retain the evolving prior state;
neither demonstrates N irrelevance. No discovered shortcut is not hardness proof.

A passing local gate permits consideration of a separate fixed8-call G-only
development batch, not automatic launch. Same Opus/high/native constraints,
all4 paired correctness transitions reported; invalid outputs separate, no
first-mixed-result stopping or reserve/role/exposure wave. Its unresolved value:
harder arithmetic could expose a shared bottleneck without producing useful
dissent. Execution count and thinking tokens do not prove reasoning difficulty.

A competing candidate skips difficulty induction and asks whether a coordinator
can extract support from actual checkable execution certificates and resist
copies of erroneous support. Local checkers know validity; the coordinator would
see transitions, with validity/corruption locations hidden. Copy identity is
provenance, never correctness. An invalid transition with a correct final claim
could separate evidence checking from agreement with an answer. This is a
candidate, not a frozen experiment. Supplied error rates would not stand in for
checking content. One verifier with identical evidence/total inference budget
is the eventual fair comparator; executable verification is the practical ceiling.

Choose between the final difficulty-only checkpoint, a local certificate
construction audit, or a more informative bounded alternative. Do not treat
more errors, useful dissent and successful collaboration as the same milestone.
No multiagent superiority, generalization or novelty claim is sought. Model
tiers and scouts should serve information value; no extra agent wave is needed
for this compact decision. A justified park is a useful result.
''']
mission = '\n'.join(lines)
output = root / '_sessions/cycles/2026-09-10-cycle08-review-mission.md'
with output.open('x') as stream:
    stream.write(mission)
receipt = {'source_artifacts_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (base/'panel.json', base/'manifest.json')},
           'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'mission_sha256': hashlib.sha256(mission.encode()).hexdigest(),
           'numeric_capsule_source': 'Program/count/truth/gate table and source copied programmatically from sealed panel; no handwritten case labels.'}
(root/'_sessions/evidence/2026-09-10-cycle08-capsule-check.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'mission_words':len(mission.split()), **receipt}))
