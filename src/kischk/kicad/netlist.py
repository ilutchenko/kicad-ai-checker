from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile

from .project import LoadedProject, load_project
from .sch_model import SExprAtom, SExprList
from .sch_parser import parse_sexpr


class NetlistError(RuntimeError):
    """Raised when netlist export or parsing fails."""


@dataclass(frozen=True)
class NetlistNode:
    ref: str
    pin: str
    pintype: str | None
    pinfunction: str | None


@dataclass(frozen=True)
class NetlistNet:
    code: str
    name: str
    net_class: str | None
    nodes: tuple[NetlistNode, ...]


@dataclass(frozen=True)
class NetlistData:
    source: Path
    nets: tuple[NetlistNet, ...]


def export_netlist(
    schematic_file: str | Path,
    output_file: str | Path,
    fmt: str = "kicadsexpr",
) -> Path:
    schematic = Path(schematic_file).expanduser().resolve()
    output = Path(output_file).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "kicad-cli",
        "sch",
        "export",
        "netlist",
        "--format",
        fmt,
        "-o",
        str(output),
        str(schematic),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
        raise NetlistError(f"Failed to export netlist with kicad-cli: {msg}")

    if not output.exists():
        raise NetlistError(f"kicad-cli did not produce netlist file: {output}")

    return output


def export_project_netlist(loaded: LoadedProject) -> Path:
    prefix = loaded.root_schematic.stem.replace(" ", "_")
    with tempfile.NamedTemporaryFile(
        prefix=f"kischk_{prefix}_",
        suffix=".net",
        delete=False,
    ) as tmp:
        temp_path = Path(tmp.name)

    return export_netlist(loaded.root_schematic, temp_path)


def load_or_export_project_netlist(project_root: str | Path) -> NetlistData:
    loaded = load_project(project_root)

    candidate = loaded.root_schematic.with_suffix(".net")
    if candidate.exists():
        return parse_netlist_file(candidate)

    exported = export_project_netlist(loaded)
    return parse_netlist_file(exported)


def parse_netlist_file(path: str | Path) -> NetlistData:
    netlist_path = Path(path).expanduser().resolve()
    text = netlist_path.read_text(encoding="utf-8")
    root = parse_sexpr(text, source=netlist_path)
    return parse_netlist_ast(root, source=netlist_path)


def parse_netlist_ast(root: SExprList, source: Path | None = None) -> NetlistData:
    head = _head(root)
    if head != "export":
        location = str(source) if source else "<netlist>"
        raise NetlistError(f"{location}: expected root 'export' node")

    nets_node = _find_child(root, "nets")
    if nets_node is None:
        location = str(source) if source else "<netlist>"
        raise NetlistError(f"{location}: missing '(nets ...) section")

    nets: list[NetlistNet] = []
    for net in _child_lists(nets_node, "net"):
        code = _first_kv_value(net, "code")
        name = _first_kv_value(net, "name")
        net_class = _first_kv_value(net, "class")
        if code is None or name is None:
            continue

        nodes: list[NetlistNode] = []
        for node in _child_lists(net, "node"):
            ref = _first_kv_value(node, "ref")
            pin = _first_kv_value(node, "pin")
            if ref is None or pin is None:
                continue

            nodes.append(
                NetlistNode(
                    ref=ref,
                    pin=pin,
                    pintype=_first_kv_value(node, "pintype"),
                    pinfunction=_first_kv_value(node, "pinfunction"),
                )
            )

        nets.append(
            NetlistNet(
                code=code,
                name=name,
                net_class=net_class,
                nodes=tuple(nodes),
            )
        )

    return NetlistData(source=source or Path("<memory>"), nets=tuple(nets))


def _head(node: SExprList | None) -> str | None:
    if node is None or not node.items:
        return None
    first = node.items[0]
    return first.value if isinstance(first, SExprAtom) else None


def _find_child(node: SExprList, head: str) -> SExprList | None:
    for child in node.items[1:]:
        if isinstance(child, SExprList) and _head(child) == head:
            return child
    return None


def _child_lists(node: SExprList, head: str) -> list[SExprList]:
    out: list[SExprList] = []
    for child in node.items[1:]:
        if isinstance(child, SExprList) and _head(child) == head:
            out.append(child)
    return out


def _first_kv_value(node: SExprList, key: str) -> str | None:
    for child in node.items[1:]:
        if not isinstance(child, SExprList):
            continue
        if _head(child) != key:
            continue
        if len(child.items) < 2:
            continue
        value = child.items[1]
        if isinstance(value, SExprAtom):
            return value.value
    return None
