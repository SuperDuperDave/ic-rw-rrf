"""Explicit rank-fusion semantics for new experiments (Python 3.8+, stdlib).

Historical probes remain unchanged. Ranks here start at one, absent documents
contribute zero, and ties in computed scores use ascending string document IDs.
``math.fsum`` reduces dependence on ranker iteration order. This can change
near-ties relative to legacy repeated addition; document-ID ties also differ
from historical insertion-order ties. Floating contributions can distinguish
mathematical ties or collapse distinct mathematical scores. Default weights
are 1.0 per source, whose global scale does not affect the mathematical ranking.
"""

from collections import defaultdict
from collections.abc import Set
from fractions import Fraction
import math
from numbers import Real


def _sources(lists):
    """Snapshot the input, preserving ranks and rejecting ambiguous source data."""
    if isinstance(lists, (str, bytes, Set)):
        raise ValueError("lists must contain an ordered collection of ranked sequences")
    try:
        sources = list(lists)
    except TypeError as error:
        raise ValueError("lists must be iterable") from error
    validated = []
    for index, source in enumerate(sources):
        if isinstance(source, (str, bytes, Set)):
            raise ValueError("source {} must be an ordered ranked sequence".format(index))
        try:
            ranking = tuple(source)
        except TypeError as error:
            raise ValueError("source {} must be iterable".format(index)) from error
        if any(not isinstance(doc, str) for doc in ranking):
            raise ValueError("source {} contains a non-string document ID".format(index))
        if len(set(ranking)) != len(ranking):
            raise ValueError("source {} contains duplicate document IDs".format(index))
        validated.append(ranking)
    return validated


def _nonnegative_finite(value, name):
    if not isinstance(value, Real):
        raise ValueError("{} must be a finite nonnegative real number".format(name))
    if value < 0:
        raise ValueError("{} must be finite and nonnegative".format(name))
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError("{} must be representable as a finite float".format(name)) from error
    if not math.isfinite(number) or number < 0:
        raise ValueError("{} must be finite and nonnegative".format(name))
    return number


def canonical_rrf(lists, k=60, weights=None):
    """Return docs by descending fsum(weight / (k + one-based rank)).

    Sources contain unique string IDs. k and weights must be finite nonnegative
    real numbers representable as floats; weights must match the source count.
    Zero-weight sources still introduce candidates, so all-zero scores sort by ID.
    Empty input returns []. Inputs are never mutated. If a document's finite
    contributions overflow fsum's float result, use its exact rational sum;
    other documents retain their fsum scores, and no score clips to infinity.
    """
    sources = _sources(lists)
    k = _nonnegative_finite(k, "k")
    if weights is None:
        weights = [1.0] * len(sources)
    else:
        try:
            weights = list(weights)
        except TypeError as error:
            raise ValueError("weights must be iterable") from error
        if len(weights) != len(sources):
            raise ValueError("weights must match the number of sources")
        weights = [_nonnegative_finite(weight, "weight") for weight in weights]
    contributions = defaultdict(list)
    for source, weight in zip(sources, weights):
        for rank, doc in enumerate(source, 1):
            contributions[doc].append(weight / (k + rank))
    scores = {}
    for doc, values in contributions.items():
        try:
            scores[doc] = math.fsum(values)
        except OverflowError:
            scores[doc] = sum((Fraction.from_float(value) for value in values), Fraction())
    return sorted(scores, key=lambda doc: (-scores[doc], doc))


def _present_ranks(sources):
    ranks = defaultdict(list)
    for source in sources:
        for rank, doc in enumerate(source, 1):
            ranks[doc].append(rank)
    return ranks


def coverage_limit(lists):
    """Return the TWO-TERM large-k proxy: coverage, present-rank sum, doc ID.

    For equal-weight RRF, score = coverage/k - sum(ranks)/k**2 + O(k**-3).
    This proxy truncates that expansion: if coverage and rank sum tie, higher
    moments can distinguish RRF scores. The historical-convenience name does not
    mean a universal exact asymptotic ordering; use asymptotic_rrf for that.
    """
    ranks = _present_ranks(_sources(lists))
    return sorted(ranks, key=lambda doc: (-len(ranks[doc]), sum(ranks[doc]), doc))


coverage_rank_proxy = coverage_limit


def asymptotic_rrf(lists):
    """Return the eventual equal-weight RRF ordering as real k tends to infinity.

    Use (-coverage, sum(r), -sum(r**2), ..., (-1)**(M+1)*sum(r**M), ID),
    where M is the source count. Expanding 1/(k+r) gives these alternating moments;
    the first unequal coefficient determines the eventual order for fixed finite
    rankings. Equal-coverage rank multisets have at most M elements. By Newton's
    identities, equality of their first M power sums makes the multisets identical,
    so any remaining tie is an exact RRF tie and uses document ID.

    Integer moments avoid cancellation. Evaluating canonical_rrf at an enormous
    floating-point k can lose these distinctions and need not reproduce this order.
    No labels, source weights, or near-duplicate assumptions enter this ordering.
    """
    sources = _sources(lists)
    ranks = _present_ranks(sources)

    def key(doc):
        present = ranks[doc]
        moments = tuple((1 if power % 2 else -1) *
                        sum(rank ** power for rank in present)
                        for power in range(1, len(sources) + 1))
        return (-len(present),) + moments + (doc,)

    return sorted(ranks, key=key)


def duplicate_quotient(lists):
    """Return distinct exact ordered source lists, preserving first occurrence.

    This removes repeated evidence only when the entire ranking matches, including
    length and order. It neither clusters near-duplicates nor estimates dependence.
    Returned lists are copies; changing them does not mutate the source rankings.
    """
    seen = set()
    unique = []
    for source in _sources(lists):
        if source not in seen:
            seen.add(source)
            unique.append(list(source))
    return unique
