"""BindingOps API server — ``bind-api`` CLI entry point."""


def main() -> None:
    import uvicorn

    uvicorn.run(
        "bind_tools.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
