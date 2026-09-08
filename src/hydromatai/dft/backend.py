from __future__ import annotations
"""Common interface for HydroMatAI DFT backends."""


from abc import ABC, abstractmethod
from typing import Any


class DFTBackend(ABC):
    """Common interface for all HydroMatAI DFT backends.

    The original HydroMatAI backend API used ``prepare()``,
    ``run()`` and ``parse()``.

    The newer API additionally exposes ``run_relax()`` and
    ``run_scf()``.

    ``run_relax()`` and ``run_scf()`` deliberately have default
    implementations so legacy backend implementations remain
    instantiable and backward compatible.
    """

    def __repr__(self) -> str:
        """Return a compact and stable backend representation."""
        return (
            f"{type(self).__name__}"
            f"(name={self.name!r})"
        )

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name."""
        raise NotImplementedError

    def run_relax(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a structural relaxation.

        Default compatibility implementation.

        Concrete backends that support a dedicated RELAX calculation
        should override this method.
        """
        run = getattr(self, "run", None)

        if not callable(run):
            raise NotImplementedError(
                "This backend does not implement RELAX."
            )

        return run(*args, **kwargs)

    def run_scf(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run an SCF calculation.

        Default compatibility implementation.

        Concrete backends that support a dedicated SCF calculation
        should override this method.
        """
        run = getattr(self, "run", None)

        if not callable(run):
            raise NotImplementedError(
                "This backend does not implement SCF."
            )

        return run(*args, **kwargs)
