"""Builder B's toy tests as a package (integration, INTEGRATE_REPORT.txt): its conftest is then imported as
tests_builder_b.conftest, not as the top-level module `conftest`, which the common toy builders reserve for the
engine's tests/conftest.py (D:/treeroute/rivals_build/rivals/tests/toy_runs.py:189). This lets one pytest run collect
rivals_human/tests, tests_builder_b and tests_builder_c together."""
