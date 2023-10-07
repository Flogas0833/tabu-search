from __future__ import annotations

import itertools
import os
from collections import deque
from multiprocessing import pool
from typing import ClassVar, Deque, List, Optional, Tuple, Set, TYPE_CHECKING

from .base import BasePathNeighborhood
from .bundle import IPCBundle
if TYPE_CHECKING:
    from ..solutions import PathSolution


__all__ = ("Swap",)


class Swap(BasePathNeighborhood[Tuple[int, int, int, int]]):

    __slots__ = (
        "_first_length",
        "_second_length",
    )
    _maxlen: ClassVar[int] = 100
    _tabu_list: ClassVar[Deque[Tuple[int, int]]] = deque()
    _tabu_set: ClassVar[Set[Tuple[int, int]]] = set()
    if TYPE_CHECKING:
        _first_length: int
        _second_length: int

    def __init__(self, solution: PathSolution, *, first_length: int, second_length: int) -> None:
        super().__init__(solution)
        self._first_length = first_length
        self._second_length = second_length

    def swap(self, first_head: int, first_tail: int, second_head: int, second_tail: int) -> PathSolution:
        solution = self._solution

        before = list(solution.before)
        after = list(solution.after)

        if first_head == after[second_tail]:
            first_head, first_tail, second_head, second_tail = second_head, second_tail, first_head, first_tail

        if first_tail == before[second_head]:
            before_first = before[first_head]
            after_second = after[second_tail]

            cost = (
                solution.cost()
                + solution.distances[before_first][second_head]
                + solution.distances[second_tail][first_head]
                + solution.distances[first_tail][after_second]
                - solution.distances[before_first][first_head]
                - solution.distances[first_tail][second_head]
                - solution.distances[second_tail][after_second]
            )

            after[before_first], before[second_head] = second_head, before_first
            after[second_tail], before[first_head] = first_head, second_tail
            after[first_tail], before[after_second] = after_second, first_tail

        else:
            before_first = before[first_head]
            before_second = before[second_head]
            after_first = after[first_tail]
            after_second = after[second_tail]

            cost = (
                solution.cost()
                + solution.distances[before_first][second_head] + solution.distances[second_tail][after_first]
                + solution.distances[before_second][first_head] + solution.distances[first_tail][after_second]
                - solution.distances[before_first][first_head] - solution.distances[first_tail][after_first]
                - solution.distances[before_second][second_head] - solution.distances[second_tail][after_second]
            )

            after[before_first], before[second_head] = second_head, before_first
            after[before_second], before[first_head] = first_head, before_second
            after[second_tail], before[after_first] = after_first, second_tail
            after[first_tail], before[after_second] = after_second, first_tail

        return self.cls(after=after, before=before, cost=cost)

    def find_best_candidate(self, *, pool: pool.Pool) -> Optional[PathSolution]:
        concurrency = os.cpu_count() or 1
        solution = self._solution

        args: List[IPCBundle[Swap, List[Tuple[int, int, int, int]]]] = [IPCBundle(self, []) for _ in range(concurrency)]
        args_index_iteration = itertools.cycle(range(concurrency))

        for first_head_index in range(solution.dimension):
            first_tail_index = (first_head_index + self._first_length - 1) % solution.dimension

            for d in range(solution.dimension - self._first_length - self._second_length + 1):
                second_head_index = (first_tail_index + d + 1) % solution.dimension
                second_tail_index = (second_head_index + self._second_length - 1) % solution.dimension

                # Guaranteed order: first_head - first_tail - second_head - second_tail
                arg = (
                    solution.path[first_head_index],
                    solution.path[first_tail_index],
                    solution.path[second_head_index],
                    solution.path[second_tail_index],
                )
                args[next(args_index_iteration)].data.append(arg)

        result: Optional[PathSolution] = None
        min_swap: Optional[Tuple[int, int, int, int]] = None
        for result_temp, min_swap_temp in pool.map(self.static_find_best_candidate, args):
            if result_temp is None or min_swap_temp is None:
                continue

            if result is None or result_temp < result:
                result = result_temp
                min_swap = min_swap_temp

        if min_swap is not None:
            self.add_to_tabu(min_swap)

        return result

    @staticmethod
    def static_find_best_candidate(bundle: IPCBundle[Swap, List[Tuple[int, int, int, int]]]) -> Tuple[Optional[PathSolution], Optional[Tuple[int, int, int, int]]]:
        neighborhood = bundle.neighborhood
        neighborhood._ensure_imported_data()

        result: Optional[PathSolution] = None
        min_swap: Optional[Tuple[int, int, int, int]] = None
        for swap in bundle.data:
            swapped = neighborhood.swap(*swap)
            if result is None or swapped < result:
                result = swapped
                min_swap = swap

        return result, min_swap
