# Saga Unicode Identifier Profile 0.5

## Normative profile

1. Source files are UTF-8 and malformed sequences are rejected.
2. The character repertoire is fixed to Unicode 15.1.0 for Saga 0.7.
3. The first identifier character is `_` or Unicode `XID_Start`.
4. Later characters are `_` or Unicode `XID_Continue`.
5. The complete identifier must already be in NFC. Implementations reject rather than silently normalize it.
6. Keywords are the exact lowercase ASCII spellings listed by the grammar.
7. U+061C, U+200E, U+200F, U+202A–U+202E and U+2066–U+2069 are rejected as source tokens outside comments and string literals.
8. Identifier comparison is code-point equality after the required NFC check. There is no case folding.

The Python implementation requires the host Unicode database to be exactly 15.1.0. The Go implementation contains generated XID, canonical decomposition, combining-class and composition tables for Unicode 15.1.0.

## Rationale

Rejecting non-NFC names prevents two canonically equivalent spellings from becoming separate bindings. Rejecting bidirectional controls outside data literals reduces source-display ambiguity. Saga does not ban mixed scripts because legitimate identifiers may combine Japanese scripts and Latin abbreviations; editors should provide confusable warnings as a non-normative aid.
