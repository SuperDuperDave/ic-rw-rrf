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
