# Saga 0.9 resource model

Saga 0.9 has no fixed normative numeric ceiling for source bytes, tokens, syntax nesting, AST nodes, module files, module depth, package size, exact-integer bits, exponent magnitude, decimal precision, function arity, worker count, project-name length, or execution steps.

This does not mean a physical host has unlimited resources. Memory, address space, process slots, host recursion capacity, storage, decimal-provider capacity, external service budgets, or administrator policy may still be exhausted. Recoverable exhaustion is mapped to stable Saga resource diagnostics; unavoidable host termination is an implementation characteristic and must be documented.

`--step-limit N` is an opt-in local watchdog. It is disabled by default and does not participate in language conformance.
