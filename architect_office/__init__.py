"""Architect Office procedural governance scaffold."""

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    from .cli import main as cli_main

    return cli_main(argv)
