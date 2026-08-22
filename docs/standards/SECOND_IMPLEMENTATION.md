# Saga Go — Independent Second Implementation

`implementations/go` contains an interpreter written in Go. It has its own lexer, parser, AST, environments, exact-number evaluator, class/object support, exceptions and Unicode 15.1 tables. It does not import, execute or translate through the Python implementation.

The current verified profile covers the 13 tests in `conformance/manifest.json`: exact decimal and rational arithmetic, immutability, boolean conditions, ranges, functions, basic classes/interfaces, private fields, exceptions, bounds checks, Unicode identifiers, NFC rejection and bidirectional-control rejection.

It is not yet feature-equivalent to every hosted module in the Python implementation. This limitation is recorded rather than treating a wrapper as an independent implementation.
