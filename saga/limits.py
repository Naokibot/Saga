"""Saga 0.9 resource model.

Saga 0.9 deliberately specifies no normative numeric ceilings for source size,
token count, syntax depth, AST nodes, exact integer size, exponent magnitude,
module count, package size, precision, worker count, or execution steps.

Implementations may still fail when host resources are exhausted, and callers
may opt into local watchdog budgets.  Such budgets are deployment policy, not
language semantics and are not part of conformance.
"""

NORMATIVE_RESOURCE_LIMITS: dict[str, int] = {}
RESOURCE_MODEL = "no-fixed-normative-ceilings"
