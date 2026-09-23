"""1D First-Fit placement by garment length on a hang rail."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    start_cm: float
    end_cm: float  # exclusive

    @property
    def length(self) -> float:
        return self.end_cm - self.start_cm


@dataclass(frozen=True)
class Placement:
    start_cm: float
    end_cm: float


@dataclass(frozen=True)
class RailCandidate:
    """A rail offered to first-fit allocation.

    blocked marks a rail under maintenance: it is never selected for new
    hangings, regardless of free space.
    """

    rail_id: int
    length_cm: float
    occupied: list[Segment]
    blocked: bool = False


def free_gaps(rail_length: float, occupied: list[Segment]) -> list[Segment]:
    occ = sorted(occupied, key=lambda s: s.start_cm)
    gaps: list[Segment] = []
    cursor = 0.0
    for seg in occ:
        if seg.start_cm > cursor:
            gaps.append(Segment(cursor, seg.start_cm))
        cursor = max(cursor, seg.end_cm)
    if cursor < rail_length:
        gaps.append(Segment(cursor, rail_length))
    return gaps


def first_fit(rail_length: float, occupied: list[Segment], garment_cm: float) -> Placement | None:
    if garment_cm <= 0 or garment_cm > rail_length:
        return None
    for gap in free_gaps(rail_length, occupied):
        if gap.length + 1e-9 >= garment_cm:
            return Placement(gap.start_cm, gap.start_cm + garment_cm)
    return None


def choose_rail(candidates: list[RailCandidate], garment_cm: float) -> tuple[int, Placement] | None:
    """First-Fit across rails, in the given order, skipping blocked rails."""
    for cand in candidates:
        if cand.blocked:
            continue
        place = first_fit(cand.length_cm, cand.occupied, garment_cm)
        if place is not None:
            return cand.rail_id, place
    return None


def overlaps(a: Segment, b: Segment) -> bool:
    return not (a.end_cm <= b.start_cm or b.end_cm <= a.start_cm)
