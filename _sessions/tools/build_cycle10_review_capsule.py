#!/usr/bin/env python3
"""Build one artifact-derived interpretation capsule; no provider calls."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle10-2026-09-11'
MISSION = ROOT / '_sessions/cycles/2026-09-11-cycle10-review-mission.md'
RECEIPT = ROOT / '_sessions/evidence/2026-09-11-cycle10-capsule-check.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    inputs = [BASE / name for name in ('prepared/manifest.json', 'prepared/fixture.json',
              'prepared/cases.md', 'observations/manifest.json', 'scored/scores.json')]
    inputs.append(ROOT / '_sessions/evidence/2026-09-11-cycle10-empirical-audit.json')
    identities = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    scores = json.loads((BASE / 'scored/scores.json').read_text())
    observed = json.loads((BASE / 'observations/manifest.json').read_text())
    audit = json.loads(inputs[-1].read_text())
    measurement = {key: scores[key] for key in ('status', 'observed_counts', 'per_packet',
                   'policy_comparisons', 'by_root_position', 'reference_policy_totals')}
    measurement.update(native_cost_usd=observed['known_native_cost_usd'],
                       native_wall_seconds=observed['wall_seconds'], stop_reason=observed['stop_reason'])
    text = '''# Cycle10 interpretation and next-question review

You are Fable5.1, Dave's research collaborator. Tools/MCP/agents are disabled.
Review this supplied capsule; do not claim file or raw-stream inspection.
Target400 words. Return the marker delivered through Relay and request Codex's
consumption ACK for the actual request. This is review, not another solver case.

Origin: useful minority evidence versus noisy dissent and repeated agreement.
Supplied Bayesian tables were near-saturated; a program-error pilot exposed no
errors. Cycle09 then returned6/6 correct trace-validity judgments, including an
invalid trace with the correct endpoint. Its all-zero program and V-first order
let first-original-only also score perfectly. That exact result stays preserved.

Cycle10 prospectively fixed A2/B3, R0/R1, and three cyclic orders per program.
No RNG, replacement, difficulty screening or reserve. Local gate requires exact
states, first-invalid rows, content-hash IDs, all null tail slots, and named
policy separation. Endpoint/position appearances are balanced; validity is not.
Six isolated Opus5/high calls were planned, same system instruction/parser as09,
fixed interleaved order, no shared responses/reviewer context. $1 scheduling,
120s/call,300s/batch,500output/APIresponse including thinking, first native/format/
custody/resource failure stops. No retry, repair, prompt/model search or next wave.
Wrong well-formed maps are judgments, while invalid/unsent rows are separate.

Actual readable construction follows, generated from the sealed fixture:

'''
    text += (BASE / 'prepared/cases.md').read_text()
    text += '\nActual scored observations, copied from sealed outputs:\n\n```json\n'
    text += json.dumps(measurement, sort_keys=True, indent=2) + '\n```\n'
    text += '\nIndependent empirical audit receipt:\n\n```json\n'
    text += json.dumps({k: v for k, v in audit.items() if k in
        ('status', 'checks_passed', 'raw_streams_verified', 'raw_streams_unavailable', 'accounting')},
        sort_keys=True, indent=2) + '\n```\n'
    text += '''
Interpretation boundary:18 judgments reuse six certificates from two endpoint
variants of one arithmetic skeleton. Full agreement excludes only the named
deterministic output vectors on this fixture, not unlisted shortcuts or internal
mechanisms. Imperfect agreement does not prove the matched heuristic was used.
Fixed order/stochastic outputs prevent isolated causal effects. No multiagent
comparison or population inference. Machine execution is the practical verifier.

We intend to close this diagnostic rather than keep hardening arithmetic. One
independent lens proposes a consequential decision next: can a single verifier
choose the correct answer when a valid minority faces repeated bad support,
while also resisting an invalid minority? A tiny prospective design could use
two truth/validity regimes with extra-majority-copy conditions. Apparent majority
must be defined explicitly (two opposing originals alone are tied); distinguish
copy count from independent acquisitions. Exact replay is a strong baseline.
Start with one equally informed single verifier; if it solves the panel, park
multiagent work here instead of adding stages merely to create a comparison.

Please (1) challenge the measured conclusion, (2) choose this evidence-selection
bridge, a different laboratory, or a stop, and explain what would change that
choice, (3) give one smallest concrete prospective test and its failure/stop rule.
Do not infer causal copy robustness, internal strategy, novelty, or improved
collaboration from these small cases. Do not require user permission for existing
authorized research. No new empirical launch follows from your suggestion alone.
'''
    if any(sha(ROOT / name) != value for name, value in identities.items()):
        raise ValueError('review inputs changed')
    with MISSION.open('x', encoding='utf-8') as handle:
        handle.write(text)
    receipt = {'source_artifacts_sha256': identities, 'generator_sha256': sha(Path(__file__)),
               'mission_sha256': sha(MISSION), 'empirical_observations_in_capsule': True}
    with RECEIPT.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'mission_sha256': receipt['mission_sha256'], 'words': len(text.split())}))


if __name__ == '__main__':
    build()
