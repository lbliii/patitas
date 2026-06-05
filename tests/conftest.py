"""Shared pytest configuration for the test suite.

Registers a Hypothesis profile that disables the *timing-based* health checks
(``too_slow`` / ``data_too_large``). These checks measure wall-clock input
generation speed, which is unreliable when the suite runs under ``pytest -n
auto`` (xdist): many workers contend for CPU, so a strategy that generates
inputs quickly in isolation can intermittently trip ``FailedHealthCheck:
Input generation is slow``. That failure mode is about scheduling, not about a
property being violated, so suppressing it removes a real source of CI flake
without weakening any correctness assertion. Falsifying examples are still
reported as failures exactly as before.
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
