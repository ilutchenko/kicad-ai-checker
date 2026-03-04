from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NetMember:
    component_uuid: str
    reference: str
    pin_number: str


@dataclass(frozen=True)
class ElectricalNet:
    net_id: str
    net_name: str | None
    members: tuple[NetMember, ...]
    labels: tuple[str, ...]
    is_global: bool


@dataclass(frozen=True)
class ElectricalPin:
    pin_number: str
    pin_name: str | None
    direction: str | None
    is_no_connect: bool
    net_id: str | None
    net_name: str | None


@dataclass(frozen=True)
class ElectricalComponent:
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
    pins: tuple[ElectricalPin, ...]


@dataclass(frozen=True)
class ElectricalSchematic:
    path: Path
    sheet_path: str
    components: tuple[ElectricalComponent, ...]


@dataclass(frozen=True)
class ElectricalProject:
    schematics: tuple[ElectricalSchematic, ...]
    nets: tuple[ElectricalNet, ...]
