"""Official 18.2 changes applied only after validating the reviewed export."""

from copy import deepcopy

from tft.abilities.models import AbilityCorrection, AbilityForm
from tft.config import RIOT_ABILITY_PATCH_NOTES_URL

# Star-specific changes preserve unlisted source points and their PBE provenance.
# Brambleback's flat term is a constant: applying its change at all stars is an
# inference from the patch wording, disclosed in the champion's source notes.
_PATCH_ROWS: dict[str, dict[str, dict[int, int | float]]] = {
    "TFT18_Camille": {"AbilityDamage": {1: 150, 2: 225, 3: 375, 4: 640}},
    "TFT18_LeBlanc": {"PercentChanceToPrint": {3: 0.30}},
    "TFT18_Teemo": {"APDamage": {1: 55, 2: 82, 3: 130}},
    "TFT18_Ashe": {
        "RiftDuration": {1: 3, 2: 3},
        "RiftDamagePerSecond": {1: 9, 2: 14},
    },
    "TFT18_Brambleback": {
        "FrenzyArmorIgnoreFlat": {1: 0.20, 2: 0.20, 3: 0.20, 4: 0.20},
        "FrenzyArmorIgnorePercent": {1: 0.25, 2: 0.25},
    },
}


def apply_corrections(unit_name: str, forms: list[AbilityForm]) -> list[AbilityCorrection]:
    """Correct reviewed curves and discard stale derived calculation results.

    The loader must validate the exact source fingerprint and target patch
    before calling this function. Dependent calculations lose cached values as
    well; their symbolic terms remain available for the frontend to display.
    """
    overrides = _PATCH_ROWS.get(unit_name, {})
    corrections: list[AbilityCorrection] = []
    for row, values in overrides.items():
        for form in forms:
            _correct_form(form, row, values)
        corrections.append(
            {
                "field": row,
                "values": [[star, value] for star, value in values.items()],
                "source_url": RIOT_ABILITY_PATCH_NOTES_URL,
            }
        )
    return corrections


def _correct_form(form: AbilityForm, row: str, values: dict[int, int | float]) -> None:
    """Update every retained representation of a corrected curve row."""
    if row not in form["curve_values"]:
        raise ValueError(f"Reviewed ability source is missing correction row {row}")
    points = {int(star): value for star, value in form["curve_values"][row]}
    points.update(values)
    corrected = [[star, value] for star, value in sorted(points.items())]
    form["curve_values"][row] = corrected
    for footer in form["footer"]:
        if footer.get("row") == row:
            footer["values"] = deepcopy(corrected)
        if row in footer.get("curveValues", {}):
            footer["curveValues"][row] = deepcopy(corrected)

    changed: set[str] = set()
    for attribute, calculation in form["attribute_calcs"].items():
        for term in calculation.get("terms", []):
            if term.get("row") != row:
                continue
            field = "values" if term.get("type") == "flat" else "coefficient"
            series = term.get(field)
            if not isinstance(series, list):
                raise ValueError(f"Reviewed calculation for {row} has no {field}")
            for star, value in values.items():
                if star > len(series):
                    raise ValueError(f"Reviewed calculation for {row} has no star {star}")
                series[star - 1] = value
            changed.add(attribute)
    _discard_cached_values(form, changed)


def _discard_cached_values(form: AbilityForm, changed: set[str]) -> None:
    """Invalidate direct and transitive derived values after formula changes."""
    while True:
        dependencies = changed | {name.rsplit(".", 1)[-1] for name in changed}
        downstream = {
            attribute
            for attribute, calculation in form["attribute_calcs"].items()
            if any(term.get("scaling") in dependencies for term in calculation.get("terms", []))
        }
        newly_changed = downstream - changed
        if not newly_changed:
            break
        changed.update(newly_changed)
    for attribute in changed:
        form["attribute_values"].pop(attribute, None)
        calculation = form["attribute_calcs"][attribute]
        calculation.pop("values", None)
        calculation["resolved"] = False
