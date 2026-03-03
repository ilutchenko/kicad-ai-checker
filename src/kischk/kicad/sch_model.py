from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias


@dataclass(frozen=True)
class SExprAtom:
    value: str
    quoted: bool = False


@dataclass(frozen=True)
class SExprList:
    items: tuple["SExprNode", ...]


SExprNode: TypeAlias = SExprAtom | SExprList


@dataclass(frozen=True)
class ParsedSchematic:
    path: Path
    root: SExprList


@dataclass(frozen=True)
class ParsedProject:
    schematics: tuple[ParsedSchematic, ...]
