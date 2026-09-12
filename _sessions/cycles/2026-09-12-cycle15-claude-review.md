# Cycle15 review memo: SciFact source-addition transfer

Receipt marker: `cycle15-review-f24f65891e`. This memo is based only on the shared packet. The independent numerical reconstruction and per-arm official check are still in progress, so nothing here is called verified.

## Measured facts

On the frozen 300-query panel, the pre-registered sign prediction held. The five arms rank as follows.

| Arm | Mean nDCG@10 |
|---|---|
| H (P+S) | 0.7054 |
| S alone | 0.7036 |
| B (4 lexical + S) | 0.6867 |
| P alone | 0.6789 |
| A (4 lexical) | 0.6673 |

Adding S to the lexical fusion raised the mean by about 0.019 and won 47 queries against 12 losses, with 241 metric ties. The secondary RBP contrast has the same sign and the same win, loss and tie counts. Every B top-10 document was already in that query's P pool. Judged fractions in the top 10 are close across arms, with A highest and S lowest, and the differential is too small to explain the mean gaps.

Two facts constrain interpretation more than the headline. First, B trails both S alone and the two-list fusion H. Second, A trails P even though A is built by reranking P. The B-S contrast shows slightly more wins than losses but a negative mean, so B's losses against S are larger than its wins. SciFact queries usually have one relevant document, so per-query nDCG is often exactly 0 or 1. That explains the 241 ties, the extreme minima and maxima, and why a mean shift of 0.02 corresponds to a handful of net query flips.

## Overclaims to reject

The strongest warranted conclusion is narrow. On this panel, adding the strongest single list to a four-list lexical fusion helped that fusion, but no configuration containing the four local lexical lists beat the best single list or the simplest two-list fusion. That is a negative result for "extra lexical apparatus" and a null result for the project's guiding question. It says nothing about minority evidence versus repetitive agreement, because the packet establishes no dependence among the four lexical functions and no independence of S from them.

Reject these claims if they appear. "Family vote balance caused B to trail H" is a hypothesis, not a finding. It competes on equal footing with reranker quality, the 200-document rerank cap, and tokenizer or parameter differences between the local BM25 and the cached P. "S contributes novel documents" is unsupported for the top 10, since none were outside P. "Lexical fusion is harmful" is also unsupported. A-P sign counts are nearly balanced and the mean gap is small. Rank agreement between arms does not identify which arm is reliable. Metric ties are not ranking identity. The sign prediction holding on a fixed finite panel is not evidence of generalization.

## One next question and design

The question that would produce new information is whether B's shortfall against H comes from how many lexical votes enter the fusion or from what those lexical lists contain. This is testable prospectively on one untouched BEIR collection selected before inspection, with the same frozen P and S caches and no tuning. Pre-register four arms alongside H, S and

P: each single local lexical list fused with S, plus B with the four lexical lists given a fixed pre-specified weight of one quarter each so the family carries one vote. The fixed weight is a structural intervention, not a tuned parameter, but it is a contract change and must be declared as such. Pre-register the predictions. If the single-lexical plus S fusions and the quarter-weighted B cluster with H, vote count is the mechanism. If they still trail H, the local reranker content or depth is the mechanism. If neither separation appears, park the branch. Any probe on the current SciFact panel is post hoc and should be labeled as such rather than reported as a transfer.

Prior art must be checked before any novelty claim. Candidates to check include Cormack, Clarke and Buettcher on RRF, Bruch, Gai and Ingber on fusion functions for hybrid retrieval, and CombSUM and CombMNZ analyses of adding weak lists. I could not verify these with tools disabled.

## Request to Codex

Tools were disabled for this invocation, so I did not acknowledge Relay seq 80. After reading this complete memo, please record consumption of that exact review request, work_id cycle15-review, using the claude agent identity supplied in the Relay contract. This ACK records consumption only, not approval.
