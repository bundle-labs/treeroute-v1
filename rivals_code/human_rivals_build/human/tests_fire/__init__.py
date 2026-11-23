"""Toy tests of the fire human rivals (SPEC_HUMAN_PARTB.txt section 5, builder B3), as a package: its conftest is then
imported as tests_fire.conftest, never as the top-level module `conftest` (INTEGRATE_REPORT.txt I4), so one pytest
run can collect rivals_human/tests, tests_builder_b, tests_builder_c, review_tests and tests_fire together."""
