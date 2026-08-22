# Saga Language Edition 1.0 Draft conformance profiles

## Portable Core Level 1

A small compatibility subset retained for historical and bootstrap testing. Both implementations continue to run it, but Saga Go 0.13.0 now targets the full Standard Core rather than stopping at PCL1.

## Standard Core

Includes the Unicode source profile, static type model, exact numbers, option values, immutable collections, functions, generics, source units, classes/interfaces, exceptions, deterministic core evaluation, isolated tasks, structured diagnostics, project locking, verification, and canonical source packaging. Saga Python 0.13.0 and the independent Saga Go 0.13.0 implementation both target this profile.

## Hosted Standard

Adds capability-controlled files, networking, databases, GUI, process execution, plugins, image/video, cloud and other host services. Process-based CPU parallel functions `task.cpu_map`, `task.cpu_filter`, and `task.cpu_reduce` are Hosted Standard facilities in the 0.9 reference implementation.

Saga Language Edition 1.0 Draft has no fixed normative numeric resource ceiling. Conformance statements describe host resource characteristics and watchdog policies separately from language semantics.
