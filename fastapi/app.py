from __future__ import annotations

import inspect
from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, get_type_hints

from . import responses
from .exceptions import HTTPException


@dataclass
class Route:
    method: str
    path: str
    handler: Callable[..., Any]
    response_model: Optional[type]

    def __post_init__(self) -> None:
        self._segments = [segment for segment in self.path.strip("/").split("/") if segment]
        self._signature = inspect.signature(self.handler)
        self._type_hints = get_type_hints(self.handler)

    def matches(self, path: str) -> Tuple[bool, Dict[str, str]]:
        request_segments = [segment for segment in path.strip("/").split("/") if segment]
        if len(request_segments) != len(self._segments):
            return False, {}
        params: Dict[str, str] = {}
        for pattern, value in zip(self._segments, request_segments):
            if pattern.startswith("{") and pattern.endswith("}"):
                params[pattern[1:-1]] = value
            elif pattern != value:
                return False, {}
        return True, params

    def invoke(self, *, path_params: Dict[str, str], body: Optional[Dict[str, Any]]) -> Any:
        kwargs: Dict[str, Any] = {}
        body_consumed = False
        for name, parameter in self._signature.parameters.items():
            if name in path_params:
                kwargs[name] = path_params[name]
                continue
            if not body_consumed:
                annotation = self._type_hints.get(name, parameter.annotation)
                if annotation is inspect._empty:
                    kwargs[name] = body
                else:
                    kwargs[name] = _parse_body(annotation, body or {})
                body_consumed = True
            else:
                kwargs[name] = None
        return self.handler(**kwargs)


class APIRouter:
    def __init__(self, prefix: str = "", tags: Optional[List[str]] = None) -> None:
        self.prefix = prefix.rstrip("/")
        self.tags = tags or []
        self.routes: List[Route] = []

    def add_api_route(self, path: str, handler: Callable[..., Any], *, methods: List[str], response_model: Optional[type] = None) -> None:
        full_path = f"{self.prefix}{path}" if self.prefix else path
        for method in methods:
            self.routes.append(Route(method=method.upper(), path=full_path, handler=handler, response_model=response_model))

    def get(self, path: str, *, response_model: Optional[type] = None):
        return self._route_decorator(path, methods=["GET"], response_model=response_model)

    def post(self, path: str, *, response_model: Optional[type] = None):
        return self._route_decorator(path, methods=["POST"], response_model=response_model)

    def _route_decorator(self, path: str, *, methods: List[str], response_model: Optional[type]):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, methods=methods, response_model=response_model)
            return func

        return decorator


class FastAPI(APIRouter):
    def __init__(self, *, title: str = "FastAPI", version: str = "0.1.0", description: str = "") -> None:
        super().__init__()
        self.title = title
        self.version = version
        self.description = description

    # ------------------------------------------------------------------
    # Minimal ASGI adapter so the shim can run under uvicorn
    # ------------------------------------------------------------------
    def __call__(self, scope):  # ASGI2 interface - returns an instance
        return _ASGIApp(self, scope)

    def include_router(self, router: APIRouter) -> None:
        self.routes.extend(router.routes)

    def get(self, path: str, *, response_model: Optional[type] = None):  # type: ignore[override]
        return super().get(path, response_model=response_model)

    def post(self, path: str, *, response_model: Optional[type] = None):  # type: ignore[override]
        return super().post(path, response_model=response_model)


class TestClient:
    __test__ = False

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def get(self, path: str) -> responses.Response:
        return self.request("GET", path)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> responses.Response:
        return self.request("POST", path, json=json)

    def request(self, method: str, path: str, json: Optional[Dict[str, Any]] = None) -> responses.Response:
        for route in self.app.routes:
            if route.method != method.upper():
                continue
            matched, params = route.matches(path)
            if matched:
                try:
                    result = route.invoke(path_params=params, body=json)
                except HTTPException as exc:
                    return responses.Response(status_code=exc.status_code, body={"detail": exc.detail})
                return responses.Response(status_code=200, body=responses.serialize(result))
        return responses.Response(status_code=404, body={"detail": "Not Found"})


def _parse_body(annotation: type, payload: Dict[str, Any]) -> Any:
    if hasattr(annotation, "from_dict"):
        return annotation.from_dict(payload)
    return payload

__all__ = ["APIRouter", "FastAPI", "HTTPException", "TestClient"]


class _ASGIApp:
    def __init__(self, app: FastAPI, scope: Dict[str, Any]) -> None:
        self.app = app
        self.scope = scope

    async def __call__(self, receive, send) -> None:
        if self.scope.get("type") != "http":
            # Only HTTP supported; return 404 for others
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": b"Not Found"})
            return

        method: str = self.scope.get("method", "GET").upper()
        path: str = self.scope.get("path", "/")

        # Read request body (best-effort, small bodies only)
        body_bytes = b""
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body_bytes += message.get("body", b"")
            if not message.get("more_body"):
                break

        json_payload: Optional[Dict[str, Any]] = None
        if body_bytes:
            try:
                json_payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                json_payload = None

        # Route matching
        for route in self.app.routes:
            if route.method != method:
                continue
            matched, params = route.matches(path)
            if not matched:
                continue
            try:
                result = route.invoke(path_params=params, body=json_payload)
                status_code = 200
                body_obj = responses.serialize(result)
            except HTTPException as exc:
                status_code = exc.status_code
                body_obj = {"detail": exc.detail}

            if isinstance(body_obj, (dict, list)):
                data = json.dumps(body_obj).encode("utf-8")
                content_type = b"application/json; charset=utf-8"
            elif isinstance(body_obj, str):
                data = body_obj.encode("utf-8")
                # Basic content-type detection
                lower_path = path.lower()
                if lower_path.endswith(".js") or lower_path.startswith("/static/"):
                    content_type = b"text/javascript; charset=utf-8"
                elif "<html" in body_obj.lower():
                    content_type = b"text/html; charset=utf-8"
                else:
                    content_type = b"text/plain; charset=utf-8"
            else:
                data = str(body_obj).encode("utf-8")
                content_type = b"text/plain; charset=utf-8"

            headers = [(b"content-type", content_type), (b"content-length", str(len(data)).encode("ascii"))]
            await send({"type": "http.response.start", "status": status_code, "headers": headers})
            await send({"type": "http.response.body", "body": data})
            return

        # No route matched
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"application/json; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": b"{\"detail\": \"Not Found\"}"})
