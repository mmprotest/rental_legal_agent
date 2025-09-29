from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, get_type_hints

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

    def include_router(self, router: APIRouter) -> None:
        self.routes.extend(router.routes)

    def get(self, path: str, *, response_model: Optional[type] = None):  # type: ignore[override]
        return super().get(path, response_model=response_model)

    def post(self, path: str, *, response_model: Optional[type] = None):  # type: ignore[override]
        return super().post(path, response_model=response_model)

    async def __call__(self, scope: Dict[str, Any], receive: Callable[[], Awaitable[Dict[str, Any]]], send: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        scope_type = scope.get("type")
        if scope_type == "lifespan":
            await _handle_lifespan(receive, send)
            return
        if scope_type != "http":
            raise RuntimeError(f"Unsupported ASGI scope: {scope_type}")

        method = scope.get("method", "").upper()
        path = scope.get("path", "")
        body = await _receive_json_body(receive)

        for route in self.routes:
            if route.method != method:
                continue
            matched, params = route.matches(path)
            if not matched:
                continue
            try:
                result = route.invoke(path_params=params, body=body)
            except HTTPException as exc:
                await _send_response(send, status_code=exc.status_code, payload={"detail": exc.detail})
                return
            await _send_response(send, status_code=200, payload=responses.serialize(result))
            return

        await _send_response(send, status_code=404, payload={"detail": "Not Found"})


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


async def _handle_lifespan(receive: Callable[[], Awaitable[Dict[str, Any]]], send: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    while True:
        message = await receive()
        message_type = message.get("type")
        if message_type == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message_type == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def _receive_json_body(receive: Callable[[], Awaitable[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    body_bytes = b""
    while True:
        message = await receive()
        body_bytes += message.get("body", b"")
        if not message.get("more_body", False):
            break
    if not body_bytes:
        return None
    try:
        return json.loads(body_bytes.decode())
    except json.JSONDecodeError:
        return None


async def _send_response(send: Callable[[Dict[str, Any]], Awaitable[None]], *, status_code: int, payload: Any) -> None:
    body = json.dumps(payload).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})

__all__ = ["APIRouter", "FastAPI", "HTTPException", "TestClient"]

