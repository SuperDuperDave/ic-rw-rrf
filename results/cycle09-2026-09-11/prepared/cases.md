# Cycle09 certificate cases

Local construction labels and checker verdicts below are evaluator metadata.
Only the separately serialized packet files are candidate solver inputs.

## Program

~~~python
a = 0
b = 0
a = a + b
b = a - b
a = a + b
result = (a % 2 == 0)
~~~

## Certificate V

| Step | Recorded complete state | Locally valid transition |
| --- | --- | --- |
| 1 | {"a":0} | true |
| 2 | {"a":0,"b":0} | true |
| 3 | {"a":0,"b":0} | true |
| 4 | {"a":0,"b":0} | true |
| 5 | {"a":0,"b":0} | true |
| 6 | {"a":0,"b":0,"result":true} | true |

Whole-certificate validity: true. First invalid step: None.

## Certificate I

| Step | Recorded complete state | Locally valid transition |
| --- | --- | --- |
| 1 | {"a":0} | true |
| 2 | {"a":0,"b":0} | true |
| 3 | {"a":1,"b":0} | false |
| 4 | {"a":1,"b":1} | true |
| 5 | {"a":2,"b":1} | true |
| 6 | {"a":2,"b":1,"result":true} | true |

Whole-certificate validity: false. First invalid step: 3.

## Certificate F

| Step | Recorded complete state | Locally valid transition |
| --- | --- | --- |
| 1 | {"a":0} | true |
| 2 | {"a":0,"b":0} | true |
| 3 | {"a":0,"b":0} | true |
| 4 | {"a":0,"b":0} | true |
| 5 | {"a":0,"b":0} | true |
| 6 | {"a":0,"b":0,"result":false} | false |

Whole-certificate validity: false. First invalid step: 6.

## Fixed reference policies

| Packet | Policy | Correct / valid / planned original judgments |
| --- | --- | --- |
| base | always_valid | 1 / 3 / 3 |
| base | always_invalid | 2 / 3 / 3 |
| base | exact_checker | 3 / 3 / 3 |
| repeat | always_valid | 1 / 3 / 3 |
| repeat | always_invalid | 2 / 3 / 3 |
| repeat | exact_checker | 3 / 3 / 3 |

These are six diagnostic judgments from one program construction.
No empirical solver outcome or provider launch is implied.
