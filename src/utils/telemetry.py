from __future__ import annotations
from functools import wraps
from time import perf_counter
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


def _default_counts(result: Any) -> Dict[str, int]:
    if isinstance(result, list):
        return {"items": len(result)}
    if isinstance(result, dict):
        # convenção: se tiver "accounts"/"users"/"failures"/etc podes querer contar
        return {}
    return {}



def instrument(
    *,
    label: Optional[str] = None,
    count_fn: Optional[Callable[[Any], Dict[str, int]]] = None,
    swallow_exceptions: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., Dict[str, Any]]]:
    """
    Wrap any function returning T into a standard envelope:

      {
        "ok": bool,
        "label": str,
        "duration_s": float,
        "counts": dict[str,int],
        "result": Any,
        "error": str|None
      }

    - count_fn: if provided, must return a dict of counts.
    - swallow_exceptions:
        False (default): re-raises exception after building envelope? -> No (keeps consistent envelope)
        True: returns ok=False envelope and does not raise.

      NOTE: for a project-wide standard, it's usually better to swallow and return ok=False.
    """
    def deco(fn: Callable[..., T]) -> Callable[..., Dict[str, Any]]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            t0 = perf_counter()
            try:
                res = fn(*args, **kwargs)
                dt = perf_counter() - t0
                counts = count_fn(res) if count_fn else _default_counts(res)

                return {
                    "ok": True,
                    "label": label or fn.__name__,
                    "duration_s": round(dt, 4),
                    "counts": counts,
                    "result": res,
                    "error": None,
                }
            except Exception as ex:
                dt = perf_counter() - t0
                envelope = {
                    "ok": False,
                    "label": label or fn.__name__,
                    "duration_s": round(dt, 4),
                    "counts": {},
                    "result": None,
                    "error": str(ex),
                }
                if swallow_exceptions:
                    return envelope
                # default: return envelope (project consistency) instead of throwing
                return envelope
        return wrapper
    return deco


def wrap(
    fn: Callable[..., T],
    *,
    label: Optional[str] = None,
    count_fn: Optional[Callable[[Any], Dict[str, int]]] = None,
) -> Callable[..., Dict[str, Any]]:
    """
    Non-decorator version (useful for dynamic wrapping).
    """
    return instrument(label=label, count_fn=count_fn)(fn)