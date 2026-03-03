from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .project import LoadedProject, load_project
from .sch_model import ParsedProject, ParsedSchematic, SExprAtom, SExprList, SExprNode


class SchematicParseError(RuntimeError):
    """Raised when a KiCad schematic S-expression cannot be parsed."""


@dataclass
class _Cursor:
    text: str
    index: int = 0

    def eof(self) -> bool:
        return self.index >= len(self.text)

    def peek(self) -> str:
        if self.eof():
            return ""
        return self.text[self.index]

    def take(self) -> str:
        if self.eof():
            return ""
        ch = self.text[self.index]
        self.index += 1
        return ch


def parse_schematic_file(path: str | Path) -> ParsedSchematic:
    file_path = Path(path).expanduser().resolve()
    text = file_path.read_text(encoding="utf-8")
    root = parse_sexpr(text, source=file_path)

    if not root.items:
        raise SchematicParseError(f"{file_path}: empty top-level expression")

    head = root.items[0]
    if not isinstance(head, SExprAtom) or head.value != "kicad_sch":
        raise SchematicParseError(
            f"{file_path}: expected root list to start with 'kicad_sch'"
        )

    return ParsedSchematic(path=file_path, root=root)


def parse_project(project_root: str | Path) -> ParsedProject:
    loaded = load_project(project_root)
    return parse_loaded_project(loaded)


def parse_loaded_project(loaded: LoadedProject) -> ParsedProject:
    schematics = tuple(parse_schematic_file(path) for path in loaded.schematic_files)
    return ParsedProject(schematics=schematics)


def parse_sexpr(text: str, source: Path | None = None) -> SExprList:
    cursor = _Cursor(text=text)
    _skip_ws_and_comments(cursor)

    if cursor.peek() != "(":
        raise _error(cursor, source, "expected '(' at top-level")

    root = _parse_list(cursor, source)
    _skip_ws_and_comments(cursor)

    if not cursor.eof():
        raise _error(cursor, source, "unexpected trailing content")

    return root


def _parse_list(cursor: _Cursor, source: Path | None) -> SExprList:
    if cursor.take() != "(":
        raise _error(cursor, source, "expected '('")

    items: List[SExprNode] = []
    while True:
        _skip_ws_and_comments(cursor)
        ch = cursor.peek()

        if ch == "":
            raise _error(cursor, source, "unexpected end of input; missing ')'")
        if ch == ")":
            cursor.take()
            return SExprList(items=tuple(items))
        if ch == "(":
            items.append(_parse_list(cursor, source))
            continue
        if ch == '"':
            items.append(_parse_string(cursor, source))
            continue

        items.append(_parse_symbol(cursor))


def _parse_string(cursor: _Cursor, source: Path | None) -> SExprAtom:
    if cursor.take() != '"':
        raise _error(cursor, source, "expected string")

    chars: List[str] = []
    while True:
        ch = cursor.take()
        if ch == "":
            raise _error(cursor, source, "unterminated string")
        if ch == "\\":
            escaped = cursor.take()
            if escaped == "":
                raise _error(cursor, source, "unterminated escape sequence")
            if escaped == "n":
                chars.append("\n")
            elif escaped == "t":
                chars.append("\t")
            else:
                chars.append(escaped)
            continue
        if ch == '"':
            break
        chars.append(ch)

    return SExprAtom(value="".join(chars), quoted=True)


def _parse_symbol(cursor: _Cursor) -> SExprAtom:
    chars: List[str] = []
    while True:
        ch = cursor.peek()
        if ch == "" or ch.isspace() or ch in "();":
            break
        chars.append(cursor.take())

    return SExprAtom(value="".join(chars), quoted=False)


def _skip_ws_and_comments(cursor: _Cursor) -> None:
    while True:
        while cursor.peek().isspace():
            cursor.take()

        if cursor.peek() != ";":
            return

        while True:
            ch = cursor.take()
            if ch in {"", "\n"}:
                break


def _line_col(text: str, index: int) -> tuple[int, int]:
    line = 1
    col = 1
    for ch in text[:index]:
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1
    return line, col


def _error(cursor: _Cursor, source: Path | None, message: str) -> SchematicParseError:
    line, col = _line_col(cursor.text, cursor.index)
    location = f"{source}:{line}:{col}" if source is not None else f"{line}:{col}"
    return SchematicParseError(f"{location}: {message}")
