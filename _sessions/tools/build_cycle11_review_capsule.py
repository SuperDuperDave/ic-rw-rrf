#!/usr/bin/env python3
"""Generate the cycle11 review capsule directly from sealed research artifacts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle11-2026-09-11'
MISSION = ROOT / '_sessions/cycles/2026-09-11-cycle11-review-mission.md'
RECEIPT = ROOT / '_sessions/evidence/2026-09-11-cycle11-capsule-check.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    inputs = [BASE / name for name in ('prepared/manifest.json', 'prepared/fixture.json',
              'prepared/cases.md', 'observations/manifest.json', 'scored/scores.json')]
    inputs.append(ROOT / '_sessions/evidence/2026-09-11-cycle11-empirical-audit.json')
    identities = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    fixture = json.loads(inputs[1].read_text())
    observed = json.loads(inputs[3].read_text())
    scores = json.loads(inputs[4].read_text())
    audit = json.loads(inputs[5].read_text())
    capsule = '''# Cycle11 interpretation and research-direction checkpoint

You are Fable5.1, Dave's research collaborator. Tools, MCP and agents are disabled.
Review the supplied capsule; do not claim file or raw-stream inspection. Target
450 words. Return the marker delivered through Relay and request Codex's
consumption ACK for the actual request. This review is separate from solver data.

The original curiosity is useful minority evidence versus noisy dissent and
repeated agreement. Retrieval experiments found a narrow configuration-specific
gain, failed annual transfer, and incompletely observed specialist relevance.
Controlled known-truth models then separated lineage from error dependence and
calibration. Actual Opus calls nearly saturated fully supplied probability laws.
A small two-role program pilot produced no errors, so reserve calls stayed unsent.
Cycle09 verified trace judgments but left a first-position shortcut. Cycle10
returned18/18 correct judgments across two program endpoints and three report
orders, differing from named position/endpoint policies without identifying an
internal method. No successor rank-fusion algorithm or multiagent gain exists.

Cycle11 is the prespecified final bridge in this arithmetic laboratory. Reuse
cycle10's exact R0/R1 programs and V/F certificate bytes and roots. Four packets
cross truth with valid-minority/majority status; each has three instances of one
root and one of its opponent. Copies are not independent acquisitions. Distinct
submission IDs preserve per-instance judgments; root identity includes program
context even where certificate bytes coincide. No new arithmetic, corruption,
RNG, replacement, source search or difficulty screen.

Four fresh isolated Opus5/high calls were planned in fixed order. Each receives
only a common instruction and its packet, no review/prior-response context.
The response is one atomic JSON answer plus four submission-validity Booleans.
First native/format/custody/resource failure stops; wrong well-formed maps remain
observations. $1 scheduling allowance,120s/call,300s/batch,500 output tokens per
API response including thinking. No repair, retries, cap changes or extra agents.

The frozen decision rule: if all four answers and sixteen validity judgments
are correct, park multiagent work in this restricted laboratory. Any failure is
preserved as its precise error/inconsistency, without causal diagnosis or an
automatic repair probe. Correct outputs do not establish necessary evidence use,
copy robustness, internal sequence, generalization or novelty. Exact program
execution is the practical reference; a direct solver can produce all outputs.

Actual readable construction, generated from the sealed fixture:

'''
    capsule += inputs[2].read_text()
    capsule += '\nReused program sources and V/F certificates, copied from the fixture:\n\n```json\n'
    capsule += json.dumps([{'program_id': p['program_id'], 'program': p['program'],
        'certificates': {label: p['certificates'][label] for label in ('V', 'F')}}
        for p in fixture['programs']], sort_keys=True, separators=(',', ':')) + '\n```\n'
    measurement = {key: scores[key] for key in ('status', 'observed_counts', 'invocations', 'diagnostics')}
    measurement['reference_policy_totals'] = fixture['policy_totals']
    measurement['native'] = {key: observed[key] for key in
        ('known_native_cost_usd', 'wall_seconds', 'stop_reason')}
    capsule += '\nActual measurements copied from sealed outputs:\n\n```json\n'
    capsule += json.dumps(measurement, sort_keys=True, indent=2) + '\n```\n'
    capsule += '\nIndependent audit summary:\n\n```json\n'
    capsule += json.dumps({key: value for key, value in audit.items() if key in
        ('status', 'checks_passed', 'raw_streams_verified', 'raw_streams_unavailable', 'accounting')},
        sort_keys=True, indent=2) + '\n```\n'
    capsule += '''
Please challenge the narrow conclusion and honor the stopping rule. Then suggest
one useful research direction outside repeated hardening of this arithmetic
laboratory, or a consolidation checkpoint if further measurement lacks value.
Explain what genuinely new information that direction would expose and the
smallest local feasibility gate before any provider batch or acquisition.
Do not merely add stages, agents, reliability tables or another harder toy.
Unvalidated possibilities are welcome; distinguish them from demonstrated facts.
No new empirical launch follows from a suggestion alone. Keep workflow effort
proportional: we now have extensive audit machinery around very small panels.
'''
    if any(sha(ROOT / name) != value for name, value in identities.items()):
        raise ValueError('review inputs changed')
    with MISSION.open('x', encoding='utf-8') as stream:
        stream.write(capsule)
    receipt = {'source_artifacts_sha256': identities, 'generator_sha256': sha(Path(__file__)),
               'mission_sha256': sha(MISSION), 'empirical_observations_in_capsule': True}
    with RECEIPT.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'mission_sha256': sha(MISSION), 'words': len(capsule.split())}))


if __name__ == '__main__':
    build()
