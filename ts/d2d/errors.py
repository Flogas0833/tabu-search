from __future__ import annotations


__all__ = (
    "D2DSolverException",
    "ImportException",
    "NeighborhoodException",
)


class D2DSolverException(Exception):
    pass


class ImportException(D2DSolverException):

    def __init__(self, problem: str, /) -> None:
        super().__init__(f"Unable to import problem {problem!r}")


class NeighborhoodException(D2DSolverException):
    pass
