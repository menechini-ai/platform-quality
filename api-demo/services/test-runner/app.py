"""Test Runner API — FastAPI server that exposes all agent tools as testable endpoints.

Run with:
    uv run python api-demo/services/test-runner/app.py

Or in Docker:
    docker compose -f api-demo/docker-compose.yml up test-runner --build
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys
import traceback
from typing import Any

from fastapi import FastAPI

# Ensure api-demo is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

app = FastAPI(title="Test Runner API", version="0.1.0")

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "agents")


def _discover_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for fname in sorted(os.listdir(AGENTS_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        modname = f"agents.{fname[:-3]}"
        try:
            mod = importlib.import_module(modname)
        except Exception as e:
            tools.append({"module": modname, "status": "import_error", "error": str(e)})
            continue
        members = inspect.getmembers(mod, inspect.isclass)
        class_list = [
            {
                "name": cname,
                "methods": [
                    mname for mname, _ in inspect.getmembers(cls, inspect.iscoroutinefunction)
                ]
                + [
                    mname
                    for mname, _ in inspect.getmembers(cls, inspect.isfunction)
                    if not mname.startswith("_")
                ],
            }
            for cname, cls in members
            if cls.__module__ == modname
        ]
        tools.append({"module": modname, "classes": class_list})
    return tools


@app.get("/")
async def root():
    tools = _discover_tools()
    return {
        "service": "test-runner",
        "status": "ok",
        "tools_count": len(tools),
        "tools": tools,
    }


@app.get("/health")
async def health():
    return {"service": "test-runner", "status": "ok"}


@app.get("/health/check")
async def health_check():
    """Deep health: verify imports for all agent modules."""
    results: list[dict[str, Any]] = []
    errors = 0
    for fname in sorted(os.listdir(AGENTS_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        modname = f"agents.{fname[:-3]}"
        try:
            importlib.import_module(modname)
            results.append({"module": modname, "status": "ok"})
        except Exception as e:
            results.append({"module": modname, "status": "error", "error": str(e)})
            errors += 1
    return {
        "service": "test-runner",
        "status": "ok" if errors == 0 else "degraded",
        "total": len(results),
        "errors": errors,
        "modules": results,
    }


@app.get("/run/{module_name}")
async def run_module(module_name: str):
    """Import a module and return its public classes and functions."""
    try:
        mod = importlib.import_module(f"agents.{module_name}")
    except Exception as e:
        return {"status": "error", "error": str(e)}

    classes = []
    for cname, cls in inspect.getmembers(mod, inspect.isclass):
        if cls.__module__ == mod.__name__:
            methods = [
                mname
                for mname, m in inspect.getmembers(cls, inspect.isfunction)
                if not mname.startswith("_")
            ]
            classes.append({"name": cname, "methods": methods})

    functions = [
        fname
        for fname, fn in inspect.getmembers(mod, inspect.isfunction)
        if not fname.startswith("_") and fn.__module__ == mod.__name__
    ]

    return {
        "module": module_name,
        "status": "ok",
        "classes": classes,
        "functions": functions,
    }


@app.get("/run/{module_name}/{class_name}")
async def run_class_method(module_name: str, class_name: str):
    """Instantiate a class and return its methods."""
    try:
        mod = importlib.import_module(f"agents.{module_name}")
        cls = getattr(mod, class_name)
        instance = cls()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    methods = [
        mname
        for mname, m in inspect.getmembers(instance, inspect.ismethod)
        if not mname.startswith("_")
    ]
    return {
        "module": module_name,
        "class": class_name,
        "status": "ok",
        "methods": methods,
    }


@app.get("/run/{module_name}/{class_name}/{method_name}")
async def execute_method(module_name: str, class_name: str, method_name: str):
    """Execute a method on an instantiated class."""
    try:
        mod = importlib.import_module(f"agents.{module_name}")
        cls = getattr(mod, class_name)
        instance = cls()
        method = getattr(instance, method_name)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        result = method()
        # If it's a coroutine, await it
        if inspect.iscoroutine(result):
            result = await result
        return {"status": "ok", "result": str(result)[:2000]}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()[-1000:],
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
