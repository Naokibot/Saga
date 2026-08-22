# Saga internationalization profile — 1.0 RC1

Saga source is UTF-8 and uses a vendored **Unicode 15.1** identifier profile. The language edition intentionally freezes the Unicode data version so a source file does not change meaning when an operating system or host library upgrades. A future language edition may update the Unicode profile only through the normal compatibility process.

Identifiers use XID_Start/XID_Continue plus `_`, require NFC, are case-sensitive, and reject bidi-formatting controls outside literals. Numeric literals use ASCII digits only so visually confusable decimal-digit sets cannot alter tokenization.

Diagnostic **IDs and structured fields are the compatibility contract**. Translated prose is never used for conformance or CI decisions. English is the normative fallback catalog. Japanese has broad built-in translations. French, Spanish and German currently provide a smaller built-in catalog and fall back to English for untranslated diagnostics. BCP-47-style tags are accepted by reducing to the supported primary language subtag.

LSP locations are converted to negotiated UTF-8/UTF-16/UTF-32 positions while Saga's own normative source columns count Unicode scalar values. This prevents IDE locations from moving merely because a line contains non-BMP characters.
