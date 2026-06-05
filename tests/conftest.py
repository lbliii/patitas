"""Shared pytest configuration for the test suite.

Registers a Hypothesis profile that disables two health checks:
``too_slow`` (timing-based) and ``data_too_large``. ``too_slow`` measures
wall-clock input generation speed, which is unreliable when the suite runs
under ``pytest -n auto`` (xdist): many workers contend for CPU, so a strategy
that generates inputs quickly in isolation can intermittently trip
``FailedHealthCheck: Input generation is slow``. ``data_too_large`` fires when
Hypothesis must draw an unusually large amount of data to build an example,
which our composite strategies can legitimately do. Both failure modes are
about generation cost rather than a property being violated, so suppressing
them removes a real source of CI flake without weakening any correctness
assertion. Falsifying examples are still reported as failures exactly as
before.
"""

from hypothesis import HealthCheck, settings

settings.register_profile(
    "patitas",
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
)
settings.load_profile("patitas")
