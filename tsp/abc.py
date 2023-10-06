from __future__ import annotations

import itertools
from functools import total_ordering
from multiprocessing import Pool, pool
from typing import Any, Dict, Generic, Optional, Tuple, Type, TypeVar, Union, TYPE_CHECKING

from tqdm import tqdm
if TYPE_CHECKING:
    from typing_extensions import Self


__all__ = (
    "BaseSolution",
    "BaseNeighborhood",
)


@total_ordering
class BaseSolution:
    """Base class for objects holding a solution to the problem"""

    __slots__ = ()

    def cost(self) -> float:
        """Calculate the cost for this solution"""
        raise NotImplementedError

    def get_neighborhoods(self) -> Tuple[BaseNeighborhood[Self], ...]:
        """Returns all neighborhoods of the current solution"""
        raise NotImplementedError

    def shuffle(self, use_tqdm: bool = True) -> Self:
        """Shuffle the current solution

        After a certain (or random) number of iterations and the solution does not improve,
        shuffle it randomly.

        The default implementation does nothing.

        Parameters
        -----
        use_tqdm: `bool`
            Whether to display the progress bar
        """
        return self

    def post_optimization(self) -> Self:
        """Perform post-optimization for this solution

        The default implementation does nothing.
        """
        return self

    @classmethod
    def initial(cls) -> Self:
        """Generate the initial solution for tabu search"""
        raise NotImplementedError

    @classmethod
    def tabu_search(cls, *, iterations_count: int, use_tqdm: bool = True, shuffle_after: int = 50) -> Self:
        result = current = cls.initial()
        iterations: Union[range, tqdm[int]] = range(iterations_count)
        if use_tqdm:
            iterations = tqdm(iterations, desc="Tabu search", ascii=" █")

        with Pool() as pool:
            last_improved = 0
            neighborhood_iterations = itertools.cycle(range(len(current.get_neighborhoods())))
            for iteration in iterations:
                neighborhoods = current.get_neighborhoods()
                best_candidate = neighborhoods[next(neighborhood_iterations)].find_best_candidate(pool=pool)

                if best_candidate is None:
                    break

                if best_candidate < current:
                    current = best_candidate
                    last_improved = iteration

                result = min(result, current)

                if iteration - last_improved >= shuffle_after:
                    current = current.shuffle(use_tqdm=use_tqdm)

        return result.post_optimization()

    def __hash__(self) -> int:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} hash={self.__hash__()}>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.cost() == other.cost()

        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.cost() < other.cost()

        return NotImplemented


T = TypeVar("T", bound=BaseSolution)


class BaseNeighborhood(Generic[T]):
    """Base class for generating neighborhood of a solution"""

    __slots__ = (
        "_solution",
        "extras",
    )
    if TYPE_CHECKING:
        _solution: T
        extras: Dict[Any, Any]

    def __init__(self, solution: T, /) -> None:
        self._solution = solution
        self.extras = {}

    @property
    def cls(self) -> Type[T]:
        return type(self._solution)

    def find_best_candidate(self, *, pool: pool.Pool) -> Optional[T]:
        """Find the best candidate solution within the neighborhood of the current one.

        Subclasses should implement the tabu logic internally.
        """
        raise NotImplementedError
