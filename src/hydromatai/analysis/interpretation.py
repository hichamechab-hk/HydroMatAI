"""General automatic interpretation engine."""


def interpret_convergence(summary: dict) -> str:

    iterations = summary.get("iterations", 0)

    if iterations == 0:
        return "Aucune énergie SCF détectée."

    if iterations < 10:
        return (
            f"La convergence SCF est rapide ({iterations} itérations "
            "détectées)."
        )

    if iterations < 40:
        return (
            f"La convergence SCF est raisonnable, avec "
            f"{iterations} itérations."
        )

    return (
        f"La convergence SCF est relativement lente "
        f"({iterations} itérations). Une optimisation du mélange "
        "électronique peut être envisagée."
    )
