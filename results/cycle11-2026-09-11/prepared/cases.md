# Cycle11 evidence-selection cases

Private labels and exact checks below are evaluator metadata.
The sealed packets are candidate solver inputs, not observed responses.

| Request | Packet | Private slots | Program answer | Bytes |
| --- | --- | --- | --- | --- |
| 1 | R0-A | F, V, F, F | false | 1394 |
| 2 | R1-B | V, V, V, F | true | 1394 |
| 3 | R0-B | V, F, V, V | false | 1396 |
| 4 | R1-A | F, F, F, V | true | 1396 |

## R0-A

| Slot | Submission ID | Parent root ID | Valid | Endpoint |
| --- | --- | --- | --- | --- |
| 1 | s_91f3566434fea697 | r_4b61b62bf4ebb888 | false | true |
| 2 | s_5c428586190a3918 | r_fd33def23bfb8121 | true | false |
| 3 | s_58bf69dccb455f7e | r_4b61b62bf4ebb888 | false | true |
| 4 | s_b770221e0a5978fc | r_4b61b62bf4ebb888 | false | true |

## R1-B

| Slot | Submission ID | Parent root ID | Valid | Endpoint |
| --- | --- | --- | --- | --- |
| 1 | s_f57f313545160dde | r_07f8548c5b839904 | true | true |
| 2 | s_bd297196c33f0474 | r_07f8548c5b839904 | true | true |
| 3 | s_b2d72ac829e6abf7 | r_07f8548c5b839904 | true | true |
| 4 | s_dd85cddf0b41a60d | r_53a36be6236c8c95 | false | false |

## R0-B

| Slot | Submission ID | Parent root ID | Valid | Endpoint |
| --- | --- | --- | --- | --- |
| 1 | s_5c428586190a3918 | r_fd33def23bfb8121 | true | false |
| 2 | s_91f3566434fea697 | r_4b61b62bf4ebb888 | false | true |
| 3 | s_348acc5c93347b16 | r_fd33def23bfb8121 | true | false |
| 4 | s_4afc266e1cb17918 | r_fd33def23bfb8121 | true | false |

## R1-A

| Slot | Submission ID | Parent root ID | Valid | Endpoint |
| --- | --- | --- | --- | --- |
| 1 | s_dd85cddf0b41a60d | r_53a36be6236c8c95 | false | false |
| 2 | s_cacb852807c97d6a | r_53a36be6236c8c95 | false | false |
| 3 | s_5e1f9f8f0a27e03f | r_53a36be6236c8c95 | false | false |
| 4 | s_f57f313545160dde | r_07f8548c5b839904 | true | true |

## Answer references

| Policy | Correct / answered / planned | Abstentions | Ordered answer vector |
| --- | --- | --- | --- |
| exact_replay | 4 / 4 / 4 | 0 | [false,true,false,true] |
| majority | 2 / 4 / 4 | 0 | [true,true,false,false] |
| minority | 2 / 4 / 4 | 0 | [false,false,true,true] |
| position_1 | 2 / 4 / 4 | 0 | [true,true,false,false] |
| position_2 | 2 / 4 / 4 | 0 | [false,true,true,false] |
| position_3 | 2 / 4 / 4 | 0 | [true,true,false,false] |
| position_4 | 2 / 4 / 4 | 0 | [true,false,false,true] |
| always_true | 2 / 4 / 4 | 0 | [true,true,true,true] |
| always_false | 2 / 4 / 4 | 0 | [false,false,false,false] |
| deduplicated_root_vote | 0 / 0 / 4 | 4 | [null,null,null,null] |

## Validity references

| Policy | Correct / valid / planned | Ordered validity vector |
| --- | --- | --- |
| exact_checker | 16 / 16 / 16 | [false,true,false,false,true,true,true,false,true,false,true,true,false,false,false,true] |
| endpoint_matches_truth | 16 / 16 / 16 | [false,true,false,false,true,true,true,false,true,false,true,true,false,false,false,true] |
| always_valid | 8 / 16 / 16 | [true,true,true,true,true,true,true,true,true,true,true,true,true,true,true,true] |
| always_invalid | 8 / 16 / 16 | [false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false] |

Root deduplication abstains on all four 1:1 ties; it does not make four errors.
Copies are artifact instances, not independent acquisitions or independent samples.
The parent programs and all parent certificates remain unchanged.
A passing local audit does not authorize empirical calls.
