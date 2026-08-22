# Saga 0.9 grammar and static rules

The candidate normative grammar is `spec/saga-0.9.ebnf`. Prose requirements in `docs/iso/SAGA_LANGUAGE_WORKING_DRAFT_0.9.md` define semantics when the grammar alone cannot express a requirement.

Saga 0.9 has no fixed language-prescribed ceiling for source size, token count, nesting depth, AST nodes, function/call arity, or project-name length. Recoverable host exhaustion is reported as a resource condition.
