#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sys
import statistics
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.registry import _index_connect, _index_candidates, registry_index_stats

RELEASE = "0.38.0"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    seq = sorted(values)
    pos = min(len(seq) - 1, max(0, round((len(seq) - 1) * p)))
    return seq[pos]


def qualify(names: int = 20_000, versions: int = 5, queries: int = 200) -> dict:
    with tempfile.TemporaryDirectory(prefix="saga-registry-scale-") as td:
        root = Path(td)
        started = time.perf_counter()
        with closing(_index_connect(root)) as db:
            rows = []
            for i in range(names):
                name = f"pkg-{i:05d}-motor-control" if i % 997 == 0 else f"pkg-{i:05d}-utility"
                for v in range(versions):
                    version = f"1.{v}.0"
                    rows.append((
                        name, name.casefold(), version, f"{(i * versions + v):064x}"[-64:],
                        1024 + v, "[]", "", f"packages/{name}/{version}/metadata.json",
                    ))
            db.executemany("""INSERT INTO packages(name,name_fold,version,sha256,size,capabilities,publisher_fingerprint,metadata_path)
                VALUES(?,?,?,?,?,?,?,?)""", rows)
            db.commit()
        inserted_s = time.perf_counter() - started
        stats = registry_index_stats(root)

        samples: list[float] = []
        hits = 0
        for i in range(queries):
            q = "motor-control" if i % 5 == 0 else f"pkg-{(i * 97) % names:05d}"
            t0 = time.perf_counter_ns()
            found = _index_candidates(root, q)
            samples.append((time.perf_counter_ns() - t0) / 1_000_000)
            hits += len(found)

        def reader(seed: int) -> tuple[int, float]:
            local_hits = 0
            worst = 0.0
            for j in range(40):
                q = f"pkg-{(seed * 379 + j * 31) % names:05d}"
                t0 = time.perf_counter_ns()
                found = _index_candidates(root, q)
                worst = max(worst, (time.perf_counter_ns() - t0) / 1_000_000)
                local_hits += len(found)
            return local_hits, worst

        t_conc = time.perf_counter()
        with ThreadPoolExecutor(max_workers=8) as pool:
            concurrent = list(pool.map(reader, range(8)))
        concurrent_s = time.perf_counter() - t_conc
        with closing(_index_connect(root)) as db:
            integrity = str(db.execute("PRAGMA integrity_check").fetchone()[0])
            indexed = int(db.execute("SELECT COUNT(*) FROM packages").fetchone()[0])

    expected = names * versions
    return {
        "schema": "saga.ecosystem-scale-qualification.v1",
        "release": RELEASE,
        "mode": "accelerated synthetic registry index; no claim of a real public community ecosystem",
        "simulated_package_names": names,
        "simulated_package_versions": expected,
        "versions_per_name": versions,
        "insert_seconds": inserted_s,
        "search_backend": stats.get("search_backend"),
        "search_queries": queries,
        "search_hits": hits,
        "search_latency_ms": {
            "mean": statistics.fmean(samples) if samples else 0.0,
            "p50": percentile(samples, 0.50),
            "p95": percentile(samples, 0.95),
            "p99": percentile(samples, 0.99),
            "max": max(samples, default=0.0),
        },
        "concurrent_readers": 8,
        "concurrent_queries": 8 * 40,
        "concurrent_seconds": concurrent_s,
        "concurrent_hits": sum(x[0] for x in concurrent),
        "concurrent_worst_query_ms": max((x[1] for x in concurrent), default=0.0),
        "integrity_check": integrity,
        "indexed_rows": indexed,
        "pass": indexed == expected and integrity == "ok" and stats.get("search_backend") in {"fts5-trigram", "sql-like-fallback"},
        "limitations": [
            "The corpus is synthetic metadata used to stress the registry index and concurrent search path.",
            "It does not represent adoption, package quality, publisher diversity, network/CDN load, or a hosted public registry.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", type=int, default=20_000)
    ap.add_argument("--versions", type=int, default=5)
    ap.add_argument("--queries", type=int, default=200)
    ap.add_argument("--output", default=str(ROOT / "validation" / "ecosystem-scale-0.38.0.json"))
    args = ap.parse_args()
    report = qualify(args.names, args.versions, args.queries)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
