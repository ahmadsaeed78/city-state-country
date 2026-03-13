from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from validators import (
    validate_postal_code, POSTAL_CODE_ERROR,
    validate_phone_number, PHONE_NUMBER_FORMAT_ERROR, PHONE_NUMBER_REQUIRED_ERROR,
    _all_countries, _states_of, _cities_of,
)


class CreateUserDTO(BaseModel):
    first_name:  str = Field(..., min_length=2, max_length=20, pattern=r'^[a-zA-Z\s]+$')
    last_name:   str = Field(..., min_length=2, max_length=20, pattern=r'^[a-zA-Z\s]+$')
    email:       EmailStr
    phone:       str = Field(...)
    country:     str = Field(..., min_length=1)
    state:       str = Field(default="")   # empty string when country has no states
    city:        str = Field(default="")   # empty string when state has no cities
    postal_code: str = Field(..., min_length=1)

    # ── Normalisation ──────────────────────────────────────────────────────────

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if "  " in v:
            raise ValueError("Name cannot have multiple consecutive spaces")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v):
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if not v:
            raise ValueError(PHONE_NUMBER_REQUIRED_ERROR)
        if isinstance(v, str):
            v = v.strip().replace(" ", "")
            if not v:
                raise ValueError(PHONE_NUMBER_REQUIRED_ERROR)
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not validate_phone_number(v):
            raise ValueError(PHONE_NUMBER_FORMAT_ERROR)
        return v

    @field_validator("country", "state", "city", mode="before")
    @classmethod
    def clean_location(cls, v):
        if v is None:
            return ""
        return v.strip() if isinstance(v, str) else v

    @field_validator("postal_code", mode="before")
    @classmethod
    def clean_postal(cls, v):
        if not v:
            raise ValueError("Postal code is required")
        return v.strip().replace(" ", "") if isinstance(v, str) else v

    @field_validator("postal_code")
    @classmethod
    def validate_postal(cls, v: str) -> str:
        if not validate_postal_code(v):
            raise ValueError(POSTAL_CODE_ERROR)
        return v

    # ── Cross-field geo validation ─────────────────────────────────────────────

    @model_validator(mode="after")
    def validate_geo(self) -> "CreateUserDTO":
        """
        Mirrors the frontend cascading logic exactly:

          1. Country must exist in the database.
          2. If country has no states  → PASS (e.g. Åland Islands, territories).
          3. If country has states     → state must be valid.
          4. If state has no cities    → PASS.
          5. If state has cities       → city must be valid.

        This is why Åland Islands always works:
          - _states_of("AX") returns () → we return immediately at step 2.
        """
        country = self.country
        state   = self.state
        city    = self.city

        if not country:
            return self

        # Step 1: resolve country
        c_match = next(
            (c for c in _all_countries()
             if c[0] == country.lower() or c[1] == country.upper()),
            None,
        )
        if not c_match:
            raise ValueError(f"Invalid country: '{country}'")

        c_iso  = c_match[3]
        c_name = c_match[2]

        # Step 2: check if country has states
        states = _states_of(c_iso)
        if not states:
            return self  # No subdivisions — Åland Islands, etc.

        # Step 3: state is required and must be valid
        if not state:
            raise ValueError(f"State/province is required for '{c_name}'")

        s_match = next(
            (s for s in states
             if s[0] == state.lower() or s[1] == state.upper()),
            None,
        )
        if not s_match:
            raise ValueError(f"'{state}' is not a valid state/province of '{c_name}'")

        s_iso  = s_match[3]
        s_name = s_match[2]

        # Step 4: check if state has cities
        cities = _cities_of(c_iso, s_iso)
        if not cities:
            return self  # State has no cities in dataset

        # Step 5: city is required and must be valid
        if not city:
            raise ValueError(f"City is required for '{s_name}', '{c_name}'")

        if city.lower() not in cities:
            raise ValueError(f"'{city}' is not a valid city in '{s_name}', '{c_name}'")

        return self


class UserResponseDTO(BaseModel):
    id:          str
    first_name:  str
    last_name:   str
    email:       str
    phone:       str
    country:     str
    state:       str
    city:        str
    postal_code: str
