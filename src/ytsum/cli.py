"""Command line interface (re-exported from cli.main)."""

from ytsum.cli.main import _application_factory, _retention_factory, app, main, normalize_cli_args

__all__ = ["_application_factory", "_retention_factory", "app", "main", "normalize_cli_args"]

if __name__ == "__main__":
    main()
