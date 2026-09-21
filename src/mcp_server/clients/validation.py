import re
from typing import Optional

# ── Allowed value sets ────────────────────────────────────────────────────────
VALID_LANG           = {"KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS"}
VALID_THEME          = {"EX050100", "EX050200", "EX050300", "EX050400",
                        "EX050500", "EX050600", "EX050700"}
VALID_ARRANGE_AREA     = {"A", "C", "D", "O", "Q", "R"}
VALID_ARRANGE_LOCATION = {"A", "C", "D", "O", "Q", "R", "E", "S"}
VALID_SHOWFLAG         = {"0", "1"}
VALID_IMAGE_YN         = {"Y", "N"}
VALID_L_DONG_LIST_YN   = {"Y", "N"}

# ── Compiled regex patterns ───────────────────────────────────────────────────
_RE_CONTENT_ID  = re.compile(r"^\d{1,15}$")
_RE_DATE_YYMMDD = re.compile(r"^\d{6}$")
_RE_REGION_CD   = re.compile(r"^\d{1,8}$")

# ── Scalar limits ─────────────────────────────────────────────────────────────
MAX_ROWS        = 100
MAX_PAGE        = 10_000
MAX_KEYWORD_LEN = 100
MAX_RADIUS_M    = 20_000


# ── Validators ────────────────────────────────────────────────────────────────

def check_lang(v: str) -> str:
    v = v.upper().strip()
    if v not in VALID_LANG:
        raise ValueError(f"Invalid lang_div_cd '{v}'. Must be one of {sorted(VALID_LANG)}.")
    return v


def check_rows(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_ROWS:
        raise ValueError(f"num_of_rows must be an integer between 1 and {MAX_ROWS}.")
    return n


def check_page(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_PAGE:
        raise ValueError(f"page_no must be an integer between 1 and {MAX_PAGE}.")
    return n


def check_arrange(v: Optional[str], *, location: bool = False) -> Optional[str]:
    if not v:
        return None
    v = v.upper().strip()
    valid = VALID_ARRANGE_LOCATION if location else VALID_ARRANGE_AREA
    if v not in valid:
        raise ValueError(f"Invalid arrange '{v}'. Must be one of {sorted(valid)}.")
    return v


def check_theme(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.upper().strip()
    if v not in VALID_THEME:
        raise ValueError(f"Invalid wellness_thema_cd '{v}'. Must be one of {sorted(VALID_THEME)}.")
    return v


def check_content_id(v: str) -> str:
    v = v.strip()
    if not _RE_CONTENT_ID.match(v):
        raise ValueError(f"Invalid content_id '{v}'. Must be 1–15 digits.")
    return v


def check_date(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.strip()
    if not _RE_DATE_YYMMDD.match(v):
        raise ValueError(f"Invalid date '{v}'. Must be YYMMDD (6 digits).")
    return v


def check_region_cd(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.strip()
    if not _RE_REGION_CD.match(v):
        raise ValueError(f"Invalid region code '{v}'. Must be 1–8 digits.")
    return v


def check_keyword(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("keyword must not be empty.")
    if len(v) > MAX_KEYWORD_LEN:
        raise ValueError(f"keyword too long (max {MAX_KEYWORD_LEN} characters).")
    return v


def check_radius(v: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ValueError("radius must be a positive integer (metres).")
    if v > MAX_RADIUS_M:
        raise ValueError(f"radius must not exceed {MAX_RADIUS_M} metres (20 km).")
    return v


def check_content_type_id(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    value = v.strip()
    if not value.isdigit() or not 1 <= len(value) <= 3:
        raise ValueError("content_type_id must contain 1 to 3 digits.")
    return value


def check_coordinates(map_x: float, map_y: float) -> tuple[float, float]:
    import math

    if (
        isinstance(map_x, bool)
        or not isinstance(map_x, (int, float))
        or not math.isfinite(map_x)
        or not -180 <= map_x <= 180
    ):
        raise ValueError("map_x (longitude) must be a finite number between -180 and 180.")
    if (
        isinstance(map_y, bool)
        or not isinstance(map_y, (int, float))
        or not math.isfinite(map_y)
        or not -90 <= map_y <= 90
    ):
        raise ValueError("map_y (latitude) must be a finite number between -90 and 90.")
    return float(map_x), float(map_y)


def check_region_pair(
    region: Optional[str], district: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    checked_region = check_region_cd(region)
    checked_district = check_region_cd(district)
    if checked_district and not checked_region:
        raise ValueError("l_dong_signgu_cd requires l_dong_regn_cd.")
    return checked_region, checked_district
