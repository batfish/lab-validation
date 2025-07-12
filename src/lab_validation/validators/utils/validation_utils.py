import math
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import attr

from ..batfish_models.routes import BgpRibRoute

T = TypeVar("T")
S = TypeVar("S")
CostResult = Union[Sequence[Union[Tuple[str, float], float]], float]
CostFn = Callable[[S, T], CostResult]


def cost_total(left: S, right: T, cost: CostFn) -> float:
    """Returns the total cost after applying the given cost function to left and right.

    Handles all the union complexities of CostFn."""
    result: CostResult = cost(left, right)
    if isinstance(result, float):
        return result
    ret = 0.0
    for c in result:
        if isinstance(c, float):
            ret += c
        else:
            ret += c[1]
    return ret


def match_pairs(
    left: Sequence[S],
    right: Sequence[T],
    cost: CostFn,
) -> Sequence[Tuple[Optional[S], Optional[T], CostResult]]:
    """
    Tries to match elements in the left sequence to elements in the right sequence. Pairing is done by going through
    each element on the left (say e_left) and pairing it with an element on the right (say e_right) such that the cost
    of peering is minimum with respect to "e_left". While matching is greedy with respect to e_right, if there is a
    perfect match on the left, that will be accounted for.

    If we have elements remaining on either side after all matching is done, those elements are paired with None in the
    result.

    Neither lists should contain None.

    Cost function: The cost function should take in an element from left and right and should return a cost. To indicate
    that two elements should never be paired together, it should return a cost of infinity (math.inf). It can be assumed
    that the cost function will never be called with None elements.

    :param left: Left sequence
    :param right: Right sequence
    :param cost: Cost function to be used to determine cost between elements from left and right
    :return: list of tuples of (element_left, element_right, cost_of_this_match)
    """
    result: List[Tuple[Optional[S], Optional[T], CostResult]] = []
    used_left: List[
        S
    ] = (
        []
    )  # should ideally be set but not all real route objects are hashable (e.g., Panos)
    used_right: Set[T] = set()

    # match right with perfect matches if any
    for r in right:
        matched_left = next(
            (l for l in left if l not in used_left and cost_total(l, r, cost) == 0),
            None,
        )
        if matched_left is not None:
            result.append((matched_left, r, 0))
            used_left.append(matched_left)
            used_right.add(r)

    # greedy matching for the left for what remains
    for l in left:
        if l in used_left:
            continue
        best_right = min(
            (
                r
                for r in right
                if r not in used_right and cost_total(l, r, cost) != math.inf
            ),
            key=lambda r: cost_total(l, r, cost),
            default=None,
        )
        if best_right is not None:
            # appending cost also for now for debugging purposes
            result.append((l, best_right, cost(l, best_right)))
            used_right.add(best_right)
        else:
            result.append((l, None, math.inf))
    for r in set(right) - used_right:
        result.append((None, r, math.inf))
    return result


def preprocess_batfish_bgp_route(batfish_route: BgpRibRoute) -> BgpRibRoute:
    """
    preprocess batfish route as necessary before comparing it with real show data
    """
    nhip: Optional[str] = batfish_route.next_hop_ip
    if nhip == "AUTO/NONE(-1l)":
        return attr.evolve(batfish_route, next_hop_ip=None)
    return batfish_route


def matched_pairs_to_failures(
    matched_pairs: Sequence[Tuple[Any, Any, Any]],
) -> Dict[str, str]:
    failures: Dict[str, str] = {}
    for left, right, cost in matched_pairs:
        if left is None:
            failures[f"Right_element: {right}"] = "No_match_found_on_the_left"
        elif right is None:
            failures[f"Left_element: {left}"] = "No_match_found_on_the_right"
        elif cost:
            failures[f"Left_element: {left}"] = f"Right_element: {right} (cost {cost})"
    return failures
