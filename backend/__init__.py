from .runtime import BackendRuntime, bind_runtime, build_runtime, create_api_app


def create_app(config: object | None = None):
    return create_api_app(config=config)


__all__ = [
    "BackendRuntime",
    "bind_runtime",
    "build_runtime",
    "create_api_app",
    "create_app",
]
