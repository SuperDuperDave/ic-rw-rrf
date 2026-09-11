"""Build the cycle09 interpretation capsule from sealed local evidence; no calls."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/cycle09-2026-09-11/prepared'


def main():
    fixture = json.loads((BASE / 'fixture.json').read_text())
    lines = ['''# Cycle09 local-evidence and execution-decision review

You are Fable5.1, Dave's scientific collaborator on curiosity-led rank-fusion
and agent evidence research. Tools/MCP/agents are disabled. Review only this
capsule. Target350 words: recommend RUN or PARK for the specifically bounded
two-call pilot below, identify what could falsify the narrow hypothesis, and
name the most informative next question after that checkpoint. Return the
marker delivered through Relay and request Codex's consumption ACK; do not
invent a missing marker. This is a design review, not a solver observation.

Origin: distinguish useful minority evidence from noise and repeated agreement.
Earlier actual models reproduced supplied Bayesian probabilities; that did not
measure extracting reliability from content. A program-error pilot had no errors.
A later local loop audit passed its gate but its label imbalance let always-false
answers mimic a short/long accuracy decline. We parked that provider batch and
chose evidence-content verification with your preceding review.

Cycle09's local design was committed before drawing parameters. One exact
six-assignment program, one seeded A/B/R draw, one seeded shuffle and five ID
draws; no replacement. V is valid; I injects +1 after assignment3 then propagates
the altered state; its final a changes by2 so parity survives. F flips only the
final Boolean. Python and an independently written AST checker verify complete
submitted states, all local transitions, first-invalid rows, schema and custody.
Malformed/ill-typed traces are construction failures, not mathematical errors.

The solver-candidate base packet has three originals plus two null slots; the
repeat packet adds two exact F-certificate copies with new instance IDs and F's
root ID. Copy identity never supplies validity or independence. Private labels
and checker verdicts shown here do not appear in candidate solver payloads.
The actual facts below are generated directly from sealed artifacts.
''']
    lines += [f"Manifest SHA256: `{hashlib.sha256((BASE/'manifest.json').read_bytes()).hexdigest()}`.",
              'Parameters: `' + json.dumps(fixture['generation']['parameters'], sort_keys=True) + '`.',
              'Private shuffled order: `' + ','.join(fixture['generation']['private_order']) + '`.',
              'Packet bytes: `' + json.dumps({row['packet_id']: len(row['payload'].encode())
                                             for row in fixture['packets']}) + '`.', '',
              (BASE / 'cases.md').read_text(), '''
This actual draw is the all-zero program; I invents conspicuous nonzero states.
The valid original happens to be first. Always-valid scores1/3; always-invalid
and final-answer-only score2/3; first-original-only scores3/3 in each packet.
These pre-response reference-policy facts limit any perfect result. The exact
local gate passed; do not seek a new seed, order or corruption to harden the case.

Candidate empirical pilot: exactly two native Opus5/high calls, base then repeat,
fresh isolated contexts. Common fixed system instruction requests a validity
Boolean for each original ID, explicitly checking complete steps and noting
that a correct endpoint is insufficient. Only the corresponding canonical packet
is the user input. Accept exactly the original-ID-to-Boolean JSON map; no extra
keys, numbers, duplicate keys or partial salvage. First native/format/custody/
resource failure stops scheduling. No retries, alternate model, repair, reserve
or prompt search. Current binary remains2.1.267 with the prior hash; official
Opus/Fable IDs and prices rechecked. Tools/hooks/MCP/agents disabled for empirical
calls. Use$1 native scheduling allowance,120s/call,300s/batch,500 output tokens
per API response including thinking; continuations can exceed500 perinvocation.
The execution protocol/source/payload seal remains pending this local checkpoint.

Primary requires both maps: preserve all6 original-ID decisions, exact correct/
accepted/planned counts and each original's base→repeat transition. Partial
counts are separate with full primary null. No imputed mathematical errors.
Wrong V or accepted I/F would falsify successful instruction following on this
minimal case; six correct decisions would be consistent with checking, while
also matching the position heuristic. This is a semantic/format feasibility
pilot, not difficult reasoning, internal strategy, independence or generalization.

F-only duplication, added text, fixed call order and stochastic responses prevent
a pure-copy causal claim. No multiagent comparison exists. Machine execution is
the practical verifier for these programs. A later collaboration claim would
need a single verifier with identical evidence and total inference resources.
The local fixture is already complete. Is one bounded actual observation worth
its cost, or is a more discriminating prospective local design the better next
step? Do not treat either decision as requiring new permission from Dave.
''']
    mission = '\n'.join(lines)
    path = ROOT / '_sessions/cycles/2026-09-11-cycle09-review-mission.md'
    with path.open('x') as stream:
        stream.write(mission)
    receipt = {'source_artifacts_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (BASE/'fixture.json', BASE/'manifest.json', BASE/'cases.md')},
               'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'mission_sha256': hashlib.sha256(mission.encode()).hexdigest(),
               'empirical_observations_in_capsule': False}
    with (ROOT/'_sessions/evidence/2026-09-11-cycle09-capsule-check.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'words': len(mission.split()), **receipt}))


if __name__ == '__main__':
    main()
