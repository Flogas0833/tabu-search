from __future__ import annotations

import random
from multiprocessing import Pool
from typing import Any, Callable, List, Literal, Sequence, Set, Union, TYPE_CHECKING

from matplotlib import axes, pyplot
from tqdm import tqdm
if TYPE_CHECKING:
    from typing_extensions import Self

from .costs import BaseMulticostComparison
from ..types import _BaseSolution
if TYPE_CHECKING:
    from .neighborhoods import MultiObjectiveNeighborhood


__all__ = ("MultiObjectiveSolution",)


def _accept_all(*args: Any) -> Literal[True]:
    return True


class MultiObjectiveSolution(_BaseSolution, BaseMulticostComparison):
    """Base class for solutions to a multi-objective optimization problem"""

    __slots__ = ()

    def get_neighborhoods(self) -> Sequence[MultiObjectiveNeighborhood[Self, Any]]:
        raise NotImplementedError

    @classmethod
    def tabu_search(
        cls,
        *,
        pool_size: int,
        iterations_count: int,
        use_tqdm: bool,
        propagation_predicate: Callable[[Self, Set[Self]], bool] = _accept_all,
        shuffle_after: int,
        max_propagation: Union[int, Callable[[Set[Self]], int], None] = None,
        plot_pareto_front: bool = False,
    ) -> Set[Self]:
        """Run the tabu search algorithm to find the Pareto front for this multi-objective optimization problem.

        Parameters
        -----
        pool_size: `int`
            The size of the process pool to perform parallelism
        iterations_count: `int`
            The number of iterations to improve from the initial solution
        use_tqdm: `bool`
            Whether to display the progress bar
        propagation_predicate: Callable[[`MultiObjectiveSolution`, Set[`MultiObjectiveSolution`]], bool]
            A function taking 2 arguments: The first one is the solution S, the second one is the currently considered Pareto front.
            It must return a boolean value indicating whether the solution S should be added to the search tree. The provided function
            mustn't change the Pareto front by any means.
        shuffle_after: `int`
            After the specified number of non-improving iterations, shuffle the current solutions set
        max_propagation: Union[`int`, Callable[[Set[`MultiObjectiveSolution`]], `int`], None]
            An integer or a function that takes the current Pareto front as a single parameter and return the maximum number of
            propagating solutions at a time
        plot_pareto_front: `bool`
            Plot the Pareto front for 2-objective optimization problems only, default to False

        Returns
        -----
        Set[`MultiObjectiveSolution`]
            The Pareto front among the iterated solutions

        See also
        -----
        - https://en.wikipedia.org/wiki/Pareto_efficiency
        - https://en.wikipedia.org/wiki/Pareto_front
        """
        initial = cls.initial()
        results: Set[Self] = set()
        results.add(initial)
        iterations: Union[range, tqdm[int]] = range(iterations_count)
        if use_tqdm:
            iterations = tqdm(iterations, ascii=" █")

        current = results.copy()
        candidate_costs = [initial.cost()] if plot_pareto_front else None
        if len(initial.cost()) != 2:
            message = f"Cannot plot the Pareto front when the number of objectives is not 2"
            raise ValueError(message)

        with Pool(pool_size) as pool:
            last_improved = 0
            for iteration in iterations:
                if isinstance(iterations, tqdm):
                    iterations.set_description_str(f"Tabu search ({len(current)}/{len(results)} solution(s))")

                propagate: List[Self] = []
                for solution in current:
                    neighborhoods = solution.get_neighborhoods()
                    for candidate in random.choice(neighborhoods).find_best_candidates(pool=pool, pool_size=pool_size):
                        if candidate_costs is not None:
                            candidate_costs.append(candidate.cost())

                        if candidate.add_to_pareto_set(results) or propagation_predicate(candidate, results):
                            propagate.append(candidate)

                for candidate in propagate:
                    current.add(candidate)
                    last_improved = iteration

                if max_propagation is not None:
                    max_propagation_value = max_propagation if isinstance(max_propagation, int) else max_propagation(results)
                    remove_count = len(current) - max_propagation_value
                    if remove_count > 0:
                        for candidate in random.sample(list(current), remove_count):
                            current.remove(candidate)

                if iteration - last_improved >= shuffle_after:
                    current = set(s.shuffle(use_tqdm=use_tqdm) for s in current)

        if candidate_costs is not None:
            _, ax = pyplot.subplots()
            assert isinstance(ax, axes.Axes)

            ax.scatter(
                [cost[0] for cost in candidate_costs],
                [cost[1] for cost in candidate_costs],
                c="gray",
                label=f"Found solutions ({len(candidate_costs)})",
            )
            ax.scatter(
                [result.cost()[0] for result in results],
                [result.cost()[1] for result in results],
                c="red",
                label=f"Pareto front ({len(results)})",
            )

            ax.grid(True)

            pyplot.legend()
            pyplot.show()

        return set(r.post_optimization(pool=pool, pool_size=pool_size, use_tqdm=use_tqdm) for r in results)
