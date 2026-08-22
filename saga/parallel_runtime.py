"""Process-based CPU parallel execution for Saga.

Workers reconstruct the checked program in a fresh interpreter and receive only
copyable Saga values.  No file/database/socket/UI/plugin capabilities are
inherited.  This gives CPU-bound work real multi-process parallelism while
preserving Saga's isolated-task value model.
"""
from __future__ import annotations


def execute_cpu_job(job: dict) -> object:
    # Imports happen in the worker process so this module is safe under the
    # Windows 'spawn' multiprocessing start method.
    from .interpreter import Cell, Interpreter
    from .native import Capabilities
    from .stdlib import MODULES

    interpreter = Interpreter(
        filename=job.get("filename", "<parallel>"),
        output=lambda _text: None,
        precision=int(job["precision"]),
        step_limit=None,
        capabilities=Capabilities.safe(),
    )
    try:
        program = job["program"]
        interpreter.program = program
        interpreter._register_declarations(program)
        for module_name in job.get("modules", ()):
            module = MODULES.get(module_name)
            if module is not None:
                if module_name in interpreter.globals.values:
                    interpreter.globals.values[module_name] = Cell(module, False)
                else:
                    interpreter.globals.define(module_name, module, False)
        for name, value in job.get("globals", {}).items():
            if name in interpreter.globals.values:
                interpreter.globals.values[name] = Cell(value, False)
            else:
                interpreter.globals.define(name, value, False)
        function = interpreter.functions[job["function"]]
        result = interpreter.invoke_callable(function, list(job["args"]))
        interpreter._assert_process_sendable(result, "parallel result")
        return result
    finally:
        interpreter.close()
