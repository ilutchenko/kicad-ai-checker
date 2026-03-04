from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .electrical_model import (
    ElectricalComponent,
    ElectricalNet,
    ElectricalPin,
    ElectricalProject,
    ElectricalSchematic,
    NetMember,
)
from .project import LoadedProject, load_project
from .sch_model import ParsedProject, ParsedSchematic, SExprAtom, SExprList, SExprNode
from .sch_parser import parse_loaded_project


class ElectricalBuildError(RuntimeError):
    """Raised when electrical model extraction fails."""


@dataclass(frozen=True)
class _LibPinDef:
    number: str
    name: str | None
    direction: str | None
    at_x: float | None
    at_y: float | None
    unit: int | None


@dataclass(frozen=True)
class _Point:
    x: float
    y: float


@dataclass
class _PinRuntime:
    pin_number: str
    pin_name: str | None
    direction: str | None
    node: str | None
    is_no_connect: bool


@dataclass
class _ComponentRuntime:
    uuid: str | None
    reference: str | None
    value: str | None
    lib_id: str | None
    unit: int | None
    footprint: str | None
    datasheet: str | None
    description: str | None
    lcsc: str | None
    custom_fields: dict[str, str]
    sheet_path: str
    schematic_path: Path
    pins: list[_PinRuntime]


@dataclass(frozen=True)
class _SheetRef:
    child_path: Path
    sheet_name: str
    pin_points: tuple[tuple[str, _Point], ...]


class _DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.rank: dict[str, int] = {}

    def add(self, node: str) -> None:
        if node not in self.parent:
            self.parent[node] = node
            self.rank[node] = 0

    def find(self, node: str) -> str:
        self.add(node)
        root = node
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[node] != node:
            nxt = self.parent[node]
            self.parent[node] = root
            node = nxt
        return root

    def union(self, a: str, b: str) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        rank_a = self.rank[ra]
        rank_b = self.rank[rb]
        if rank_a < rank_b:
            self.parent[ra] = rb
            return
        if rank_a > rank_b:
            self.parent[rb] = ra
            return
        self.parent[rb] = ra
        self.rank[ra] += 1


def build_electrical_project(project_root: str | Path) -> ElectricalProject:
    loaded = load_project(project_root)
    parsed = parse_loaded_project(loaded)
    return build_electrical_from_parsed(loaded, parsed)


def build_electrical_from_parsed(
    loaded: LoadedProject,
    parsed: ParsedProject,
) -> ElectricalProject:
    by_path = {sch.path.resolve(): sch for sch in parsed.schematics}
    missing = [p for p in loaded.schematic_files if p.resolve() not in by_path]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise ElectricalBuildError(f"Parsed project is missing schematic files: {names}")

    sheet_refs_by_parent = {
        sch.path.resolve(): _extract_sheet_refs(sch) for sch in parsed.schematics
    }
    sheet_paths = _resolve_sheet_paths(loaded, sheet_refs_by_parent)

    dsu = _DisjointSet()
    net_name_candidates: dict[str, set[tuple[int, str]]] = {}
    components_by_sheet: dict[Path, list[_ComponentRuntime]] = {
        sch.path.resolve(): [] for sch in parsed.schematics
    }
    hierarchical_labels: dict[tuple[str, str], list[str]] = {}
    sheet_pin_nodes: dict[tuple[Path, Path, str], list[str]] = {}

    for schematic in parsed.schematics:
        path = schematic.path.resolve()
        sheet_path = sheet_paths[path]

        primitive = _extract_primitives(schematic, sheet_path, dsu)

        for key, value in primitive.label_candidates.items():
            net_name_candidates.setdefault(key, set()).update(value)

        for label_name, nodes in primitive.hierarchical_labels.items():
            hierarchical_labels.setdefault((sheet_path, label_name), []).extend(nodes)

        for child_path, pin_name, point in primitive.sheet_pin_points:
            node = _point_node(sheet_path, point)
            dsu.add(node)
            sheet_pin_nodes.setdefault((path, child_path, pin_name), []).append(node)

        lib_defs = _extract_lib_pin_defs(schematic)
        runtime_components = _extract_components(
            schematic=schematic,
            sheet_path=sheet_path,
            lib_pin_defs=lib_defs,
            no_connect_points=primitive.no_connect_points,
            dsu=dsu,
            net_name_candidates=net_name_candidates,
        )

        components_by_sheet[path] = runtime_components

    for (parent_path, child_path, pin_name), parent_nodes in sheet_pin_nodes.items():
        child_sheet_path = sheet_paths.get(child_path)
        if child_sheet_path is None:
            continue
        child_nodes = hierarchical_labels.get((child_sheet_path, pin_name), [])
        for parent_node in parent_nodes:
            for child_node in child_nodes:
                dsu.union(parent_node, child_node)

    all_nodes: set[str] = set(dsu.parent)
    for path_components in components_by_sheet.values():
        for comp in path_components:
            for pin in comp.pins:
                if pin.node:
                    all_nodes.add(pin.node)
                    dsu.add(pin.node)

    root_to_nodes: dict[str, list[str]] = {}
    for node in sorted(all_nodes):
        root = dsu.find(node)
        root_to_nodes.setdefault(root, []).append(node)

    net_entries = sorted(root_to_nodes.items(), key=lambda item: item[0])
    root_to_net: dict[str, tuple[str, str | None]] = {}
    nets: list[ElectricalNet] = []

    for idx, (root, _nodes) in enumerate(net_entries, start=1):
        net_id = f"N{idx:04d}"
        candidates = net_name_candidates.get(root, set())
        net_name = _select_net_name(candidates)
        root_to_net[root] = (net_id, net_name)
        labels = tuple(sorted({name for _, name in candidates if name}))
        is_global = any(priority == 0 for priority, _ in candidates)
        nets.append(
            ElectricalNet(
                net_id=net_id,
                net_name=net_name,
                members=(),
                labels=labels,
                is_global=is_global,
            )
        )

    net_members: dict[str, list[NetMember]] = {net.net_id: [] for net in nets}
    finalized_schematics: list[ElectricalSchematic] = []

    for path in loaded.schematic_files:
        resolved = path.resolve()
        runtime_components = components_by_sheet.get(resolved, [])
        finalized_components: list[ElectricalComponent] = []

        for comp in runtime_components:
            finalized_pins: list[ElectricalPin] = []
            for pin in comp.pins:
                net_id: str | None = None
                net_name: str | None = None
                if pin.node:
                    root = dsu.find(pin.node)
                    net_id, net_name = root_to_net[root]

                finalized_pins.append(
                    ElectricalPin(
                        pin_number=pin.pin_number,
                        pin_name=pin.pin_name,
                        direction=pin.direction,
                        is_no_connect=pin.is_no_connect,
                        net_id=net_id,
                        net_name=net_name,
                    )
                )

                if net_id and comp.uuid and comp.reference:
                    net_members[net_id].append(
                        NetMember(
                            component_uuid=comp.uuid,
                            reference=comp.reference,
                            pin_number=pin.pin_number,
                        )
                    )

            finalized_components.append(
                ElectricalComponent(
                    uuid=comp.uuid,
                    reference=comp.reference,
                    value=comp.value,
                    lib_id=comp.lib_id,
                    unit=comp.unit,
                    footprint=comp.footprint,
                    datasheet=comp.datasheet,
                    description=comp.description,
                    lcsc=comp.lcsc,
                    custom_fields=comp.custom_fields,
                    sheet_path=comp.sheet_path,
                    schematic_path=comp.schematic_path,
                    pins=tuple(finalized_pins),
                )
            )

        finalized_schematics.append(
            ElectricalSchematic(
                path=resolved,
                sheet_path=sheet_paths[resolved],
                components=tuple(finalized_components),
            )
        )

    finalized_nets = tuple(
        ElectricalNet(
            net_id=net.net_id,
            net_name=net.net_name,
            labels=net.labels,
            is_global=net.is_global,
            members=tuple(net_members[net.net_id]),
        )
        for net in nets
    )

    return ElectricalProject(
        schematics=tuple(finalized_schematics),
        nets=finalized_nets,
    )


@dataclass(frozen=True)
class _PrimitiveExtraction:
    no_connect_points: set[str]
    hierarchical_labels: dict[str, list[str]]
    sheet_pin_points: list[tuple[Path, str, _Point]]
    label_candidates: dict[str, set[tuple[int, str]]]


def _extract_primitives(
    schematic: ParsedSchematic,
    sheet_path: str,
    dsu: _DisjointSet,
) -> _PrimitiveExtraction:
    no_connect_points: set[str] = set()
    hierarchical_labels: dict[str, list[str]] = {}
    sheet_pin_points: list[tuple[Path, str, _Point]] = []
    label_candidates: dict[str, set[tuple[int, str]]] = {}

    for node in schematic.root.items[1:]:
        if not isinstance(node, SExprList):
            continue

        head = _head(node)
        if head == "wire":
            points = _wire_points(node)
            for point in points:
                dsu.add(_point_node(sheet_path, point))
            for left, right in zip(points, points[1:]):
                dsu.union(_point_node(sheet_path, left), _point_node(sheet_path, right))
            continue

        if head == "junction":
            point = _at_point(node)
            if point:
                dsu.add(_point_node(sheet_path, point))
            continue

        if head == "no_connect":
            point = _at_point(node)
            if point:
                no_connect_points.add(_point_key(point))
                dsu.add(_point_node(sheet_path, point))
            continue

        if head in {"label", "global_label", "hierarchical_label"}:
            label = _first_atom(node, start=1)
            point = _at_point(node)
            if not label or point is None:
                continue

            point_node = _point_node(sheet_path, point)
            dsu.add(point_node)

            if head == "global_label":
                label_node = _global_label_node(label)
                candidate_priority = 0
            elif head == "hierarchical_label":
                label_node = _local_label_node(sheet_path, label)
                candidate_priority = 2
                hierarchical_labels.setdefault(label, []).append(point_node)
            else:
                label_node = _local_label_node(sheet_path, label)
                candidate_priority = 1

            dsu.union(point_node, label_node)
            label_candidates.setdefault(label_node, set()).add((candidate_priority, label))
            continue

        if head == "sheet":
            child_rel = _sheet_property(node, "Sheetfile")
            if not child_rel:
                continue
            child_path = (schematic.path.parent / child_rel).resolve()
            for pin in _child_lists(node, "pin"):
                pin_name = _first_atom(pin, start=1)
                point = _at_point(pin)
                if pin_name and point:
                    sheet_pin_points.append((child_path, pin_name, point))
            continue

    return _PrimitiveExtraction(
        no_connect_points=no_connect_points,
        hierarchical_labels=hierarchical_labels,
        sheet_pin_points=sheet_pin_points,
        label_candidates=label_candidates,
    )


def _extract_components(
    schematic: ParsedSchematic,
    sheet_path: str,
    lib_pin_defs: dict[str, dict[tuple[int | None, str], _LibPinDef]],
    no_connect_points: set[str],
    dsu: _DisjointSet,
    net_name_candidates: dict[str, set[tuple[int, str]]],
) -> list[_ComponentRuntime]:
    components: list[_ComponentRuntime] = []

    for node in schematic.root.items[1:]:
        if not isinstance(node, SExprList) or _head(node) != "symbol":
            continue

        if _find_child(node, "lib_id") is None:
            continue

        fields = _symbol_properties(node)
        standard = {"Reference", "Value", "Footprint", "Datasheet", "Description", "LCSC"}
        lib_id = _first_atom(_find_child(node, "lib_id"), start=1)
        at = _at_point(node)
        rotation = _rotation(node)
        mirror = _mirror(node)
        unit = _int_value(_find_child(node, "unit"), default=None)
        symbol_uuid = _first_atom(_find_child(node, "uuid"), start=1)

        pins: list[_PinRuntime] = []
        for pin_node in _child_lists(node, "pin"):
            pin_number = _first_atom(pin_node, start=1)
            if pin_number is None:
                continue

            pin_def = _lookup_lib_pin_def(lib_pin_defs, lib_id, unit, pin_number)

            point_node: str | None = None
            is_nc = False
            if at and pin_def and pin_def.at_x is not None and pin_def.at_y is not None:
                point = _transform_point(pin_def.at_x, pin_def.at_y, at, rotation, mirror)
                point_node = _point_node(sheet_path, point)
                dsu.add(point_node)
                is_nc = _point_key(point) in no_connect_points

            pins.append(
                _PinRuntime(
                    pin_number=pin_number,
                    pin_name=pin_def.name if pin_def else None,
                    direction=pin_def.direction if pin_def else None,
                    node=point_node,
                    is_no_connect=is_nc,
                )
            )

        component = _ComponentRuntime(
            uuid=symbol_uuid,
            reference=fields.get("Reference"),
            value=fields.get("Value"),
            lib_id=lib_id,
            unit=unit,
            footprint=fields.get("Footprint"),
            datasheet=fields.get("Datasheet"),
            description=fields.get("Description"),
            lcsc=fields.get("LCSC"),
            custom_fields={k: v for k, v in fields.items() if k not in standard},
            sheet_path=sheet_path,
            schematic_path=schematic.path.resolve(),
            pins=pins,
        )

        # KiCad power symbols define global nets through their value text.
        if component.lib_id and component.lib_id.startswith("power:") and component.value:
            global_node = _global_label_node(component.value)
            for pin in component.pins:
                if pin.node:
                    dsu.union(pin.node, global_node)
            net_name_candidates.setdefault(global_node, set()).add((0, component.value))

        components.append(component)

    return components


def _resolve_sheet_paths(
    loaded: LoadedProject,
    sheet_refs: dict[Path, tuple[_SheetRef, ...]],
) -> dict[Path, str]:
    root = loaded.root_schematic.resolve()
    result: dict[Path, str] = {root: "/Root"}

    stack: list[Path] = [root]
    while stack:
        parent = stack.pop()
        parent_path = result[parent]
        refs = {ref.child_path: ref.sheet_name for ref in sheet_refs.get(parent, ())}

        for child in loaded.hierarchy.get(parent, ()):  # parent/child mapping from loader
            child = child.resolve()
            if child in result:
                continue
            name = refs.get(child, child.stem)
            result[child] = f"{parent_path}/{name}"
            stack.append(child)

    return result


def _extract_sheet_refs(schematic: ParsedSchematic) -> tuple[_SheetRef, ...]:
    refs: list[_SheetRef] = []
    for node in schematic.root.items[1:]:
        if not isinstance(node, SExprList) or _head(node) != "sheet":
            continue

        child_rel = _sheet_property(node, "Sheetfile")
        if not child_rel:
            continue

        child_path = (schematic.path.parent / child_rel).resolve()
        sheet_name = _sheet_property(node, "Sheetname") or child_path.stem
        pin_points: list[tuple[str, _Point]] = []

        for pin in _child_lists(node, "pin"):
            name = _first_atom(pin, start=1)
            point = _at_point(pin)
            if name and point:
                pin_points.append((name, point))

        refs.append(
            _SheetRef(
                child_path=child_path,
                sheet_name=sheet_name,
                pin_points=tuple(pin_points),
            )
        )

    return tuple(refs)


def _extract_lib_pin_defs(
    schematic: ParsedSchematic,
) -> dict[str, dict[tuple[int | None, str], _LibPinDef]]:
    lib_symbols = _find_child(schematic.root, "lib_symbols")
    if lib_symbols is None:
        return {}

    symbol_defs: dict[str, dict[tuple[int | None, str], _LibPinDef]] = {}

    for symbol in _child_lists(lib_symbols, "symbol"):
        lib_id = _first_atom(symbol, start=1)
        if not lib_id:
            continue

        entry: dict[tuple[int | None, str], _LibPinDef] = {}
        for sub_symbol in _child_lists(symbol, "symbol"):
            unit = _symbol_unit_from_name(_first_atom(sub_symbol, start=1))
            for pin in _child_lists(sub_symbol, "pin"):
                pin_def = _lib_pin_from_node(pin, unit)
                if pin_def is None:
                    continue
                key = (pin_def.unit, pin_def.number)
                if key not in entry:
                    entry[key] = pin_def

        symbol_defs[lib_id] = entry

    return symbol_defs


def _lib_pin_from_node(pin: SExprList, unit: int | None) -> _LibPinDef | None:
    direction = _atom(pin.items[1]) if len(pin.items) > 1 else None
    at = _at_point(pin)

    pin_name = None
    pin_number = None
    name_node = _find_child(pin, "name")
    if name_node is not None:
        pin_name = _first_atom(name_node, start=1)

    number_node = _find_child(pin, "number")
    if number_node is not None:
        pin_number = _first_atom(number_node, start=1)

    if not pin_number:
        return None

    return _LibPinDef(
        number=pin_number,
        name=pin_name,
        direction=direction,
        at_x=at.x if at else None,
        at_y=at.y if at else None,
        unit=unit,
    )


def _lookup_lib_pin_def(
    lib_pin_defs: dict[str, dict[tuple[int | None, str], _LibPinDef]],
    lib_id: str | None,
    unit: int | None,
    pin_number: str,
) -> _LibPinDef | None:
    if not lib_id:
        return None

    defs = lib_pin_defs.get(lib_id)
    if not defs:
        return None

    if (unit, pin_number) in defs:
        return defs[(unit, pin_number)]
    if (None, pin_number) in defs:
        return defs[(None, pin_number)]

    for (candidate_unit, number), pin in defs.items():
        if number == pin_number and candidate_unit is not None:
            return pin

    return None


def _transform_point(
    rel_x: float,
    rel_y: float,
    at: _Point,
    rotation: int,
    mirror: str | None,
) -> _Point:
    x = rel_x
    y = rel_y

    if mirror == "x":
        y = -y
    elif mirror == "y":
        x = -x

    rot = rotation % 360
    if rot == 0:
        xr, yr = x, y
    elif rot == 90:
        xr, yr = -y, x
    elif rot == 180:
        xr, yr = -x, -y
    elif rot == 270:
        xr, yr = y, -x
    else:
        raise ElectricalBuildError(f"Unsupported symbol rotation: {rotation}")

    return _Point(x=at.x + xr, y=at.y + yr)


def _wire_points(node: SExprList) -> list[_Point]:
    pts = _find_child(node, "pts")
    if pts is None:
        return []

    result: list[_Point] = []
    for xy in _child_lists(pts, "xy"):
        point = _xy_point(xy)
        if point:
            result.append(point)
    return result


def _xy_point(node: SExprList) -> _Point | None:
    if _head(node) != "xy" or len(node.items) < 3:
        return None
    x = _float_atom(node.items[1])
    y = _float_atom(node.items[2])
    if x is None or y is None:
        return None
    return _Point(x=x, y=y)


def _at_point(node: SExprList) -> _Point | None:
    at = _find_child(node, "at")
    if at is None or len(at.items) < 3:
        return None
    x = _float_atom(at.items[1])
    y = _float_atom(at.items[2])
    if x is None or y is None:
        return None
    return _Point(x=x, y=y)


def _rotation(node: SExprList) -> int:
    at = _find_child(node, "at")
    if at is None or len(at.items) < 4:
        return 0
    value = _int_atom(at.items[3])
    return value if value is not None else 0


def _mirror(node: SExprList) -> str | None:
    mirror = _find_child(node, "mirror")
    return _first_atom(mirror, start=1)


def _symbol_properties(node: SExprList) -> dict[str, str]:
    fields: dict[str, str] = {}
    for child in _child_lists(node, "property"):
        if len(child.items) < 3:
            continue
        key = _atom(child.items[1])
        value = _atom(child.items[2])
        if key is None or value is None:
            continue
        fields[key] = value
    return fields


def _sheet_property(node: SExprList, key: str) -> str | None:
    for child in _child_lists(node, "property"):
        if len(child.items) < 3:
            continue
        name = _atom(child.items[1])
        value = _atom(child.items[2])
        if name == key and value is not None:
            return value
    return None


def _select_net_name(candidates: Iterable[tuple[int, str]]) -> str | None:
    ranked = sorted(candidates, key=lambda item: (item[0], item[1]))
    if not ranked:
        return None
    return ranked[0][1]


def _point_key(point: _Point) -> str:
    return f"{point.x:.6f},{point.y:.6f}"


def _point_node(sheet_path: str, point: _Point) -> str:
    return f"point:{sheet_path}:{_point_key(point)}"


def _local_label_node(sheet_path: str, label: str) -> str:
    return f"local_label:{sheet_path}:{label}"


def _global_label_node(label: str) -> str:
    return f"global_label:{label}"


def _head(node: SExprNode | None) -> str | None:
    if not isinstance(node, SExprList) or not node.items:
        return None
    return _atom(node.items[0])


def _atom(node: SExprNode | None) -> str | None:
    if isinstance(node, SExprAtom):
        return node.value
    return None


def _first_atom(node: SExprList | None, start: int = 0) -> str | None:
    if node is None:
        return None
    for child in node.items[start:]:
        value = _atom(child)
        if value is not None:
            return value
    return None


def _find_child(node: SExprList, key: str) -> SExprList | None:
    for child in node.items:
        if isinstance(child, SExprList) and _head(child) == key:
            return child
    return None


def _child_lists(node: SExprList, key: str) -> list[SExprList]:
    result: list[SExprList] = []
    for child in node.items:
        if isinstance(child, SExprList) and _head(child) == key:
            result.append(child)
    return result


def _float_atom(node: SExprNode | None) -> float | None:
    value = _atom(node)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int_atom(node: SExprNode | None) -> int | None:
    value = _atom(node)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _int_value(node: SExprList | None, default: int | None = 0) -> int | None:
    if node is None:
        return default
    value = _first_atom(node, start=1)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _symbol_unit_from_name(name: str | None) -> int | None:
    if not name:
        return None
    match = re.search(r"_(\d+)_\d+$", name)
    if not match:
        return None
    return int(match.group(1))
