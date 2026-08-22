from __future__ import annotations

import json
import time
import tracemalloc
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .api import compile_file
from .interpreter import BuiltinFunction, Environment, Interpreter, SagaClass, UserFunction
from .native import Capabilities, NativeModule
from .tokens import Token


def _environment_snapshot(interpreter: Interpreter, env: Environment) -> dict[str, str]:
    # Walk lexical parents so a breakpoint inside a nested block can still
    # inspect the function/module variables that are actually in scope. Inner
    # bindings win, matching normal Saga name lookup.
    chain: list[Environment] = []
    current: Environment | None = env
    while current is not None:
        chain.append(current)
        current = current.parent
    visible: dict[str, object] = {}
    for scope in reversed(chain):
        for name, cell in scope.values.items():
            visible[name] = cell.value
    values: dict[str, str] = {}
    for name in sorted(visible):
        value = visible[name]
        if isinstance(value, (BuiltinFunction, NativeModule, SagaClass, UserFunction)):
            continue
        values[name] = interpreter.format_value(value)
    return values


def _environment_summary(interpreter: Interpreter, env: Environment) -> str:
    values = _environment_snapshot(interpreter, env)
    return "{" + ", ".join(f"{name}={value}" for name, value in values.items()) + "}"


def _write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def debug_file(
    path: str | Path,
    *,
    trace: bool = False,
    breakpoints: Iterable[int] = (),
    watches: Iterable[str] = (),
    record_path: str | Path | None = None,
    max_events: int = 100_000,
    output: Callable[[str], None] = print,
    debug_output: Callable[[str], None] = print,
    precision: int = 50,
    step_limit: int | None = None,
    capabilities: Capabilities | None = None,
) -> dict[str, Any]:
    """Run a checked Saga program with deterministic statement-level debugging.

    The debugger remains non-interactive so it is reproducible in terminals, CI
    and editors. 0.37 adds watch values and a bounded JSON execution recording;
    the recording can be inspected backwards to reproduce state at a statement
    boundary without mutating the debugged process.
    """
    entry_input = Path(path).expanduser()
    loaded = compile_file(str(entry_input))
    entry = loaded.entry
    selected = {int(line) for line in breakpoints}
    watched = tuple(dict.fromkeys(str(name) for name in watches if str(name)))
    if any(line < 1 for line in selected):
        raise ValueError("breakpoint lines must be >= 1")
    if max_events < 1:
        raise ValueError("max_events must be >= 1")

    interpreter: Interpreter
    events: list[dict[str, Any]] = []
    dropped = 0
    sequence = 0

    def hook(token: Token, env: Environment) -> None:
        nonlocal dropped, sequence
        sequence += 1
        snapshot = _environment_snapshot(interpreter, env)
        is_break = token.line in selected
        if trace or is_break:
            label = "break" if is_break else "trace"
            filename = token.filename or str(entry)
            watch_text = ""
            if watched:
                selected_values = ", ".join(f"{name}={snapshot.get(name, '<unbound>')}" for name in watched)
                watch_text = f" watches={{{selected_values}}}"
            debug_output(
                f"[{label}] {filename}:{token.line}:{token.column} "
                f"locals=" + "{" + ", ".join(f"{k}={v}" for k, v in snapshot.items()) + "}" + watch_text
            )
        if record_path is not None:
            if len(events) < max_events:
                events.append({
                    "seq": sequence,
                    "file": token.filename or str(entry),
                    "line": token.line,
                    "column": token.column,
                    "breakpoint": is_break,
                    "locals": snapshot,
                    "watches": {name: snapshot.get(name) for name in watched},
                    "watch": {name: snapshot.get(name, "<unbound>") for name in watched},
                })
            else:
                dropped += 1

    interpreter = Interpreter(
        str(entry), output=output, precision=precision, step_limit=step_limit,
        capabilities=capabilities, debug_hook=hook,
    )
    try:
        interpreter.interpret(loaded.program)
    finally:
        interpreter.close()

    report = {
        "schema": "saga.debug-record.v1",
        "source": str(entry),
        "events_recorded": len(events),
        "events_dropped": dropped,
        "truncated": dropped > 0,
        "breakpoints": sorted(selected),
        "watches": list(watched),
        "events": events,
    }
    if record_path is not None:
        _write_json(record_path, report)
    return report


def profile_file(
    path: str | Path,
    *,
    output: Callable[[str], None] = lambda _text: None,
    precision: int = 50,
    step_limit: int | None = None,
    capabilities: Capabilities | None = None,
    report_path: str | Path | None = None,
    top: int = 20,
) -> dict[str, Any]:
    """Profile statement-boundary execution time, hit counts and Python heap peak.

    Time between two statement hooks is attributed to the previous source
    location. This produces a low-overhead line/statement profile suitable for
    finding hot control paths. It is deliberately described as interval time,
    not CPU-instruction attribution.
    """
    if top < 1:
        raise ValueError("top must be >= 1")
    entry_input = Path(path).expanduser()
    loaded = compile_file(str(entry_input))
    entry = loaded.entry
    hits: dict[tuple[str, int, int], int] = defaultdict(int)
    interval_ns: dict[tuple[str, int, int], int] = defaultdict(int)
    previous_key: tuple[str, int, int] | None = None
    previous_ns = time.perf_counter_ns()
    interpreter: Interpreter

    def hook(token: Token, _env: Environment) -> None:
        nonlocal previous_key, previous_ns
        now = time.perf_counter_ns()
        if previous_key is not None:
            interval_ns[previous_key] += max(0, now - previous_ns)
        key = (token.filename or str(entry), token.line, token.column)
        hits[key] += 1
        previous_key = key
        previous_ns = now

    tracemalloc.start()
    started = time.perf_counter_ns()
    interpreter = Interpreter(
        str(entry), output=output, precision=precision, step_limit=step_limit,
        capabilities=capabilities, debug_hook=hook,
    )
    try:
        interpreter.interpret(loaded.program)
    finally:
        finished = time.perf_counter_ns()
        if previous_key is not None:
            interval_ns[previous_key] += max(0, finished - previous_ns)
        interpreter.close()
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    rows = []
    for key in sorted(hits):
        file_name, line, column = key
        ns = interval_ns.get(key, 0)
        rows.append({
            "file": file_name,
            "line": line,
            "column": column,
            "hits": hits[key],
            "interval_ns": ns,
            "avg_interval_ns": ns // hits[key] if hits[key] else 0,
        })
    rows.sort(key=lambda row: (-row["interval_ns"], row["file"], row["line"], row["column"]))
    report = {
        "schema": "saga.statement-profile.v1",
        "source": str(entry),
        "elapsed_ns": max(0, finished - started),
        "python_heap_current_bytes": current_bytes,
        "python_heap_peak_bytes": peak_bytes,
        "statement_events": sum(hits.values()),
        "locations": rows,
        "top": rows[:top],
        "timing_model": "time from one Saga statement hook to the next is attributed to the previous location",
    }
    if report_path is not None:
        _write_json(report_path, report)
    return report
