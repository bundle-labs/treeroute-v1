"""treeroute (placeholder name): a generic tree-routing forecasting engine.

One engine, one dataset package per problem. The engine names no problem, unit, year, drive or
store; the only hand-set input is the dataset package (see APP_PLAN.md Section 1).

Importing this package has no side effects: it imports no numeric library, sets no environment
variable, patches nothing and reads no command-line arguments (G-IMPORT). Start the engine with
``py -3.9 -m treeroute``, which pins every thread pool first (treeroute/launch.py).

This is the boilerplate skeleton: launcher, constants, CLI stubs, run plumbing (runs/) and the
package schema and loader (package/). No science module exists yet.
"""

__version__ = "0.0.1-skeleton"
