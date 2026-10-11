"""Birth form state choices and city/state queries for the offline geocoder."""

# Values match the bundled GeoNames database; the display label uses the full
# Andaman and Nicobar Islands name. Verified against the National Portal:
# https://www.india.gov.in/directory/web-directory/state-uts
INDIA_STATE_CHOICES = tuple(
    (name, "Andaman and Nicobar Islands" if name == "Andaman and Nicobar" else name)
    for name in (
        "Andaman and Nicobar", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
        "Bihar", "Chandigarh", "Chhattisgarh",
        "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat",
        "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand",
        "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
        "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
        "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
        "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    )
)
OTHER_STATE = "other"
_STATE_VALUES = {value for value, _ in INDIA_STATE_CHOICES}


def _key(value: str) -> str:
    return "".join(c for c in value.casefold() if c.isalnum())


_LEGACY_STATES = {
    _key(label): value for value, label in INDIA_STATE_CHOICES
} | {_key(value): value for value, _ in INDIA_STATE_CHOICES} | {
    "ap": "Andhra Pradesh", "tn": "Tamil Nadu", "up": "Uttar Pradesh",
    "mp": "Madhya Pradesh", "wb": "West Bengal", "orissa": "Odisha",
    "pondicherry": "Puducherry", "uttaranchal": "Uttarakhand",
    "newdelhi": "Delhi", "nctofdelhi": "Delhi",
}


def prepare_birth_place(city: str, state: str) -> tuple[str, str, str]:
    """Return displayed city, selected state and the actual search query.

    A selected Indian state always filters the search. Older City, State
    requests continue to resolve, including older state names. Empty state
    and Other preserve the existing worldwide search and coordinate override.
    """
    city, state = city.strip(), state.strip()
    if state and state not in _STATE_VALUES and state != OTHER_STATE:
        raise ValueError("Choose a state or union territory from the dropdown.")
    if state == OTHER_STATE:
        return city, state, city
    if state:
        city = city.split(",", 1)[0].strip()
        return city, state, f"{city}, {state}" if city else ""
    first, separator, rest = city.partition(",")
    inferred_state = _LEGACY_STATES.get(_key(rest.split(",", 1)[0]))
    if separator and inferred_state:
        return first.strip(), inferred_state, city
    return city, "", city
