# Cycle18 — where the geometric diagnostic sits

Bounded primary-source check, 2026-09-25. This positions the predeclared scalar
feasibility test; it does not change the experiment or establish novelty. No
selected BITEM variant effectiveness was searched or inspected.

- Vogt and Cottrell, *Fusion Via a Linear Combination of Scores* (1999), studies
  weighted score fusion and conditions associated with its effectiveness.
  Weighted-score fusion is established prior work; our fixed reciprocal-rank
  vectors are one input representation for such a sum. [Author-hosted paper](https://cseweb.ucsd.edu/~gary/pubs/info-retrieval-1999.pdf).
- Asudeh, Jagadish, Miklau and Stoyanovich, *On Obtaining Stable Rankings*,
  PVLDB12(3):237–250 (2018), treats the regions of weight space producing a
  ranking and addresses both full rankings and top-k outputs. Our inference:
  intersecting scalar head-boundary inequalities is a restricted, exact
  representability check within this established geometric perspective, not a
  new discovery of ranking regions. [Published paper](https://www.vldb.org/pvldb/vol12/p237-asudeh.pdf).
- Ge and coauthors, *Axioms for AI Alignment from Human Feedback*, section2 and
  footnote4, describes feature-linear ranking feasibility through intersections
  of half-spaces and linear inequalities. Its domain is preference aggregation,
  with restricted linear reward models; that is distinct from measured retrieval
  relevance. Our inference: the shared representability question supplies a
  possible conceptual bridge, not evidence that our retrieval result improves
  RLHF or agent reasoning. [Author-hosted paper](https://www.cs.toronto.edu/~emicha/papers/rlhf.pdf).

The local diagnostic retains document-ID tie boundaries, fixed original
candidate access and per-query versus common-weight distinctions. Its empirical
value would be a concrete certificate explaining why these new head sets
cannot be reproduced by changing one old coefficient. Feasibility and relevance
remain separate. A general statement about the whole phase space would require
a specified model family and a substantially broader analysis.

An exact synthetic fixture was checked while the implementations were underway:
A=S=[y,x01,...,x99], D=T=[x01,...,x99,y]. H contains y and x01...x09; F contains
x01...x10. All sources have the same candidate set. F's x10-minus-y margin is
16579/7276080, while both original sources favor y by10/4331. Thus every finite
nonnegative old A weight fails this boundary. Reversing the two relevance labels
reverses the benefit; capability alone cannot imply improved precision. This
fixture is a software/mathematical check, not a new benchmark observation.
