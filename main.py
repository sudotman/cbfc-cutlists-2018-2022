import argparse
import uvicorn
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CBFC Cutlists web service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Port (default: 8000 or PORT env var)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "api:app",  # import string so reload works
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
    )


if __name__ == "__main__":
    main() 