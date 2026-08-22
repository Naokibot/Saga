# Saga Database Transaction Profile 0.21

The built-in persistent key/value database now supports explicit optimistic transactions:

- `db.begin(db)`
- `db.tx_get/tx_put/tx_delete`
- `db.commit(tx)`
- `db.rollback(tx)`

A transaction snapshots the opened database handle and records its version. Commit fails with `transaction conflict` when another successful mutation changed that handle since the transaction began. Writes use write-new-then-rename and a normalized path-level mutex to avoid concurrent temporary-file corruption.

The transaction conflict model is currently scoped to one process/open database state. It is not a replacement for PostgreSQL/SQLite multi-process ACID semantics.
