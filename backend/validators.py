import re
import logging
from functools import lru_cache

# pip install country-state-city
try:
    from country_state_city import (
        Country as CSCCountry,
        State as CSCState,
        City as CSCCity,
    )
    _csc_available = True
except ImportError:
    _csc_available = False
    logging.warning("country-state-city not installed. Run: pip install country-state-city")


# ── Cached data loaders ────────────────────────────────────────────────────────
#
# Confirmed attribute names from library inspection:
#   Country : c.name, c.iso2
#   State   : s.name, s.iso_code, s.country_code
#   City    : c.name  (no iso code — cities are matched by name only)
#
# We store plain tuples so lru_cache can hash them.

@lru_cache(maxsize=1)
def _all_countries() -> tuple:
    """All countries as tuple of (name_lower, iso2_upper, name, iso2)."""
    if not _csc_available:
        return ()
    raw = CSCCountry.get_countries()
    if not raw:
        return ()
    return tuple(
        (c.name.lower(), c.iso2.upper(), c.name, c.iso2)
        for c in raw
    )


@lru_cache(maxsize=512)
def _states_of(country_iso2: str) -> tuple:
    """States for a country as tuple of (name_lower, iso_code_upper, name, iso_code)."""
    if not _csc_available:
        return ()
    raw = CSCState.get_states_of_country(country_iso2)
    if not raw:
        return ()
    return tuple(
        (s.name.lower(), s.iso_code.upper(), s.name, s.iso_code)
        for s in raw
    )


@lru_cache(maxsize=2048)
def _cities_of(country_iso2: str, state_iso_code: str) -> tuple:
    """City names (lowercase) for a state as a tuple of strings."""
    if not _csc_available:
        return ()
    raw = CSCCity.get_cities_of_state(country_iso2, state_iso_code)
    if not raw:
        return ()
    return tuple(c.name.lower() for c in raw)


# ── Main validator ─────────────────────────────────────────────────────────────

def validate_location_hierarchy(country_val: str, state_val: str, city_val: str) -> bool:
    """
    Validates country → state → city using the country-state-city library.
    Same data source as the frontend npm package — guaranteed consistency.

    Attribute names (confirmed by inspection):
      Country.iso2, Country.name
      State.iso_code, State.name, State.country_code
      City.name

    Rules:
      1. Country must exist (matched by full name or iso2, case-insensitive).
      2. If country has NO states  → skip state + city check entirely (PASS).
         Handles: Åland Islands (AX), territories, small islands, etc.
      3. If country HAS states     → state must exist in that country.
      4. If state has NO cities    → skip city check (PASS).
      5. If state HAS cities       → city must exist in that state.

    Raises ValueError with a descriptive message on failure.
    Returns True on success.
    """
    if not _csc_available:
        logging.warning("validate_location_hierarchy: library missing, skipping")
        return True

    if not country_val or not state_val or not city_val:
        return True

    # ── 1. Resolve country ────────────────────────────────────────────────────
    c_search = country_val.strip()
    country = next(
        (c for c in _all_countries()
         if c[0] == c_search.lower()    # match by full name
         or c[1] == c_search.upper()),   # match by iso2 code
        None,
    )
    if not country:
        raise ValueError(f"Invalid country: '{country_val}'")

    # country tuple: (name_lower, iso2_upper, name, iso2)
    c_iso2  = country[3]
    c_name  = country[2]

    # ── 2. Check if country has states ────────────────────────────────────────
    states = _states_of(c_iso2)
    if not states:
        # No subdivisions — Åland Islands, Cocos Islands, etc. → pass
        return True

    # ── 3. Validate state ─────────────────────────────────────────────────────
    s_search = state_val.strip()
    state = next(
        (s for s in states
         if s[0] == s_search.lower()    # match by full name
         or s[1] == s_search.upper()),   # match by iso_code
        None,
    )
    if not state:
        raise ValueError(f"'{state_val}' is not a valid state/province of '{c_name}'")

    # state tuple: (name_lower, iso_code_upper, name, iso_code)
    s_iso_code = state[3]
    s_name     = state[2]

    # ── 4. Check if state has cities ──────────────────────────────────────────
    cities = _cities_of(c_iso2, s_iso_code)
    if not cities:
        return True

    # ── 5. Validate city ──────────────────────────────────────────────────────
    if city_val.strip().lower() not in cities:
        raise ValueError(f"'{city_val}' is not a valid city in '{s_name}', '{c_name}'")

    return True


# ── Other validators ───────────────────────────────────────────────────────────

def validate_password_complexity(password: str) -> bool:
    if not re.search(r'[a-z]', password): return False
    if not re.search(r'[A-Z]', password): return False
    if not re.search(r'\d', password): return False
    if not re.search(r'[@$!%*?&#]', password): return False
    return True


def validate_postal_code(code: str) -> bool:
    if not code: return False
    if not re.match(r"^[a-zA-Z0-9\s-]{3,10}$", code): return False
    if not re.search(r'[a-zA-Z0-9]', code): return False
    return True


def validate_phone_number(phone: str) -> bool:
    if not phone: return False
    return bool(re.match(r"^\+?\d{7,18}$", phone))


# ── Error constants ────────────────────────────────────────────────────────────

PASSWORD_COMPLEXITY_ERROR  = (
    "Password must contain at least one uppercase letter, one lowercase letter, "
    "one number, and one special character (@$!%*?&#)"
)
POSTAL_CODE_ERROR          = (
    "Postal code must be 3-10 alphanumeric characters. "
    "Spaces and hyphens allowed as separators."
)
PHONE_NUMBER_FORMAT_ERROR  = (
    "Phone number must be 7-18 digits with an optional leading '+'. No spaces."
)
PHONE_NUMBER_REQUIRED_ERROR = "Phone number is required"
LOCATION_HIERARCHY_ERROR    = "The provided city/state/country combination is invalid"