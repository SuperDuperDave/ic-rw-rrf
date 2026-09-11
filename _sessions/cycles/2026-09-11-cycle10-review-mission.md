# Cycle10 interpretation and next-question review

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

# Cycle10 position and endpoint controls

Local labels and checks below are evaluator metadata. Only sealed packet files
are candidate solver inputs. There are two programs and six root certificates.

## R0

~~~python
a = 2
b = 3
a = a + b
b = a - b
a = a + b
result = (a % 2 == 0)
~~~

| Step | V complete state | I complete state | F complete state |
| --- | --- | --- | --- |
| 1 | {"a":2} | {"a":2} | {"a":2} |
| 2 | {"a":2,"b":3} | {"a":2,"b":3} | {"a":2,"b":3} |
| 3 | {"a":5,"b":3} | {"a":6,"b":3} | {"a":5,"b":3} |
| 4 | {"a":5,"b":2} | {"a":6,"b":3} | {"a":5,"b":2} |
| 5 | {"a":7,"b":2} | {"a":9,"b":3} | {"a":7,"b":2} |
| 6 | {"a":7,"b":2,"result":false} | {"a":9,"b":3,"result":false} | {"a":7,"b":2,"result":true} |

| Certificate | Root ID | Valid | First invalid step |
| --- | --- | --- | --- |
| V | r_fd33def23bfb8121 | true | None |
| I | r_2d9aaba0809eb3ea | false | 3 |
| F | r_4b61b62bf4ebb888 | false | 6 |

## R1

~~~python
a = 2
b = 3
a = a + b
b = a - b
a = a + b
result = (a % 2 == 1)
~~~

| Step | V complete state | I complete state | F complete state |
| --- | --- | --- | --- |
| 1 | {"a":2} | {"a":2} | {"a":2} |
| 2 | {"a":2,"b":3} | {"a":2,"b":3} | {"a":2,"b":3} |
| 3 | {"a":5,"b":3} | {"a":6,"b":3} | {"a":5,"b":3} |
| 4 | {"a":5,"b":2} | {"a":6,"b":3} | {"a":5,"b":2} |
| 5 | {"a":7,"b":2} | {"a":9,"b":3} | {"a":7,"b":2} |
| 6 | {"a":7,"b":2,"result":true} | {"a":9,"b":3,"result":true} | {"a":7,"b":2,"result":false} |

| Certificate | Root ID | Valid | First invalid step |
| --- | --- | --- | --- |
| V | r_07f8548c5b839904 | true | None |
| I | r_926fd49e10515fb3 | false | 3 |
| F | r_53a36be6236c8c95 | false | 6 |

## Packet order and exact UTF-8 bytes

| Request | Packet | Private slot order | Bytes | Difference from R0-P1 |
| --- | --- | --- | --- | --- |
| 1 | R0-P1 | V, I, F | 1080 | +0 |
| 2 | R1-P2 | F, V, I | 1079 | -1 |
| 3 | R0-P3 | I, F, V | 1080 | +0 |
| 4 | R1-P1 | V, I, F | 1079 | -1 |
| 5 | R0-P2 | F, V, I | 1080 | +0 |
| 6 | R1-P3 | I, F, V | 1079 | -1 |

Equal slots or byte lengths do not establish equal native token exposure.

## Reference judgments

| Policy | Correct / valid / planned | Vector differs from exact checker |
| --- | --- | --- |
| exact_checker | 18 / 18 / 18 | false |
| always_valid | 6 / 18 / 18 | true |
| always_invalid | 12 / 18 / 18 | true |
| position_1 | 10 / 18 / 18 | true |
| position_2 | 10 / 18 / 18 | true |
| position_3 | 10 / 18 / 18 | true |
| endpoint_matches_truth | 12 / 18 / 18 | true |
| endpoint_boolean | 9 / 18 / 18 | true |

These 18 planned judgments reuse six roots on two endpoint variants of one
arithmetic skeleton. They are not 18 independent cases or solver outcomes.
Any empirical phase requires its own execution freeze.

Actual scored observations, copied from sealed outputs:

```json
{
  "by_root_position": {
    "r_07f8548c5b839904": [
      {
        "correct": true,
        "packet_id": "R1-P2",
        "position": 2,
        "private_type": "V",
        "program_id": "R1",
        "returned_validity": true,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R1-P1",
        "position": 1,
        "private_type": "V",
        "program_id": "R1",
        "returned_validity": true,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R1-P3",
        "position": 3,
        "private_type": "V",
        "program_id": "R1",
        "returned_validity": true,
        "status": "accepted"
      }
    ],
    "r_2d9aaba0809eb3ea": [
      {
        "correct": true,
        "packet_id": "R0-P1",
        "position": 2,
        "private_type": "I",
        "program_id": "R0",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R0-P3",
        "position": 1,
        "private_type": "I",
        "program_id": "R0",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R0-P2",
        "position": 3,
        "private_type": "I",
        "program_id": "R0",
        "returned_validity": false,
        "status": "accepted"
      }
    ],
    "r_4b61b62bf4ebb888": [
      {
        "correct": true,
        "packet_id": "R0-P1",
        "position": 3,
        "private_type": "F",
        "program_id": "R0",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R0-P3",
        "position": 2,
        "private_type": "F",
        "program_id": "R0",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R0-P2",
        "position": 1,
        "private_type": "F",
        "program_id": "R0",
        "returned_validity": false,
        "status": "accepted"
      }
    ],
    "r_53a36be6236c8c95": [
      {
        "correct": true,
        "packet_id": "R1-P2",
        "position": 1,
        "private_type": "F",
        "program_id": "R1",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R1-P1",
        "position": 3,
        "private_type": "F",
        "program_id": "R1",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R1-P3",
        "position": 2,
        "private_type": "F",
        "program_id": "R1",
        "returned_validity": false,
        "status": "accepted"
      }
    ],
    "r_926fd49e10515fb3": [
      {
        "correct": true,
        "packet_id": "R1-P2",
        "position": 3,
        "private_type": "I",
        "program_id": "R1",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R1-P1",
        "position": 2,
        "private_type": "I",
        "program_id": "R1",
        "returned_validity": false,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R1-P3",
        "position": 1,
        "private_type": "I",
        "program_id": "R1",
        "returned_validity": false,
        "status": "accepted"
      }
    ],
    "r_fd33def23bfb8121": [
      {
        "correct": true,
        "packet_id": "R0-P1",
        "position": 1,
        "private_type": "V",
        "program_id": "R0",
        "returned_validity": true,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R0-P3",
        "position": 3,
        "private_type": "V",
        "program_id": "R0",
        "returned_validity": true,
        "status": "accepted"
      },
      {
        "correct": true,
        "packet_id": "R0-P2",
        "position": 2,
        "private_type": "V",
        "program_id": "R0",
        "returned_validity": true,
        "status": "accepted"
      }
    ]
  },
  "native_cost_usd": "0.088035000000000004",
  "native_wall_seconds": 19.69404851802392,
  "observed_counts": {
    "accepted": 18,
    "correct": 18,
    "planned": 18
  },
  "per_packet": {
    "R0-P1": {
      "accepted": 3,
      "correct": 3,
      "planned": 3,
      "status": "accepted"
    },
    "R0-P2": {
      "accepted": 3,
      "correct": 3,
      "planned": 3,
      "status": "accepted"
    },
    "R0-P3": {
      "accepted": 3,
      "correct": 3,
      "planned": 3,
      "status": "accepted"
    },
    "R1-P1": {
      "accepted": 3,
      "correct": 3,
      "planned": 3,
      "status": "accepted"
    },
    "R1-P2": {
      "accepted": 3,
      "correct": 3,
      "planned": 3,
      "status": "accepted"
    },
    "R1-P3": {
      "accepted": 3,
      "correct": 3,
      "planned": 3,
      "status": "accepted"
    }
  },
  "policy_comparisons": {
    "always_invalid": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 6,
      "planned": 18
    },
    "always_valid": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 12,
      "planned": 18
    },
    "endpoint_boolean": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 9,
      "planned": 18
    },
    "endpoint_matches_truth": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 6,
      "planned": 18
    },
    "exact_checker": {
      "compared": 18,
      "matches_full_vector": true,
      "mismatches": 0,
      "planned": 18
    },
    "position_1": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 8,
      "planned": 18
    },
    "position_2": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 8,
      "planned": 18
    },
    "position_3": {
      "compared": 18,
      "matches_full_vector": false,
      "mismatches": 8,
      "planned": 18
    }
  },
  "reference_policy_totals": {
    "always_invalid": {
      "correct": 12,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    },
    "always_valid": {
      "correct": 6,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    },
    "endpoint_boolean": {
      "correct": 9,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    },
    "endpoint_matches_truth": {
      "correct": 12,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    },
    "exact_checker": {
      "correct": 18,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": false
    },
    "position_1": {
      "correct": 10,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    },
    "position_2": {
      "correct": 10,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    },
    "position_3": {
      "correct": 10,
      "planned": 18,
      "valid": 18,
      "vector_differs_from_exact": true
    }
  },
  "status": "complete",
  "stop_reason": "all_invocations_finished"
}
```

Independent empirical audit receipt:

```json
{
  "accounting": {
    "all_observed_costs_known": true,
    "collection_wall_seconds": 19.69404851802392,
    "max_observed_message_output_tokens": 152,
    "messages_per_invocation": [
      1,
      1,
      1,
      1,
      1,
      1
    ],
    "missing_thinking_counters": 0,
    "native_cost_usd": "0.088035000000000004",
    "output_tokens": 879,
    "provider_message_count": 6,
    "thinking_tokens": 561
  },
  "checks_passed": 3990,
  "raw_streams_unavailable": 0,
  "raw_streams_verified": 6,
  "status": "passed"
}
```

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
