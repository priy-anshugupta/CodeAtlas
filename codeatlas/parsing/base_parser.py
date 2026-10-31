"""Parser interface and registry. One parser per language."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress

from codeatlas.core.models import ParsedFile


class BaseParser(ABC):
    language: str

    @abstractmethod
    def parse(self, path: str, source: bytes, module: str, is_package: bool) -> ParsedFile:
        """Parse one file. Must never raise on bad input; set `parse_error` instead."""


_REGISTRY: dict[str, BaseParser] = {}


def register_parser(parser: BaseParser) -> None:
    _REGISTRY[parser.language] = parser


def get_parser(language: str) -> BaseParser | None:
    if not _REGISTRY:
        from codeatlas.parsing.python_ast import PythonAstParser

        register_parser(PythonAstParser())
        # Optional extra: `pip install codeatlas-ctx[treesitter]` adds JS/TS/Go/Java.
        from codeatlas.parsing import treesitter

        if treesitter.available():
            for parser in treesitter.parsers():
                register_parser(parser)
        # Dart, Kotlin and Swift need no grammar package.
        from codeatlas.parsing import braces

        for parser in braces.parsers():
            register_parser(parser)
        if treesitter.available():
            from codeatlas.parsing.dart_treesitter import DartTreeSitterParser

            with suppress(ImportError):
                register_parser(DartTreeSitterParser())
            from codeatlas.parsing.kotlin_treesitter import KotlinTreeSitterParser

            with suppress(ImportError):
                register_parser(KotlinTreeSitterParser())
            from codeatlas.parsing.swift_treesitter import SwiftTreeSitterParser

            with suppress(ImportError):
                register_parser(SwiftTreeSitterParser())
    return _REGISTRY.get(language)
