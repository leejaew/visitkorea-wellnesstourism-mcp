import os
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urlencode

import httpx

# ── Upstream API ──────────────────────────────────────────────────────────────
# HTTPS enforced: the serviceKey travels as a query param; plain HTTP would
# expose it to any observer on the network path.
BASE_URL = "https://apis.data.go.kr/B551011/WellnessTursmService"

TIMEOUT = httpx.Timeout(
    connect=10.0,   # TCP + TLS handshake
    read=25.0,      # waiting for the first byte
    write=5.0,
    pool=5.0,       # time to acquire a connection from the pool
)

# ── Shared connection pool ────────────────────────────────────────────────────
# One persistent AsyncClient reused across all tool calls.
# Eliminates the per-call TCP + TLS handshake overhead (~100-300 ms each).
_LIMITS = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=30,
)
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=TIMEOUT, limits=_LIMITS)
    return _http_client


# ── Simple TTL response cache ─────────────────────────────────────────────────
# Avoids hitting the 1,000 req/day quota for identical repeated calls.
# District codes cached for 1 h (change at most daily).
# All other endpoints cached for 5 min.
_CACHE: dict[str, tuple[dict, float]] = {}
_TTL_SHORT = 300.0    # 5 minutes — search / detail results
_TTL_LONG  = 3600.0   # 1 hour    — district code lookups


def _cache_key(endpoint: str, params: dict) -> str:
    safe = {k: v for k, v in params.items() if k != "serviceKey"}
    return endpoint + "|" + "&".join(f"{k}={v}" for k, v in sorted(safe.items()))


def _cache_get(key: str) -> Optional[dict]:
    entry = _CACHE.get(key)
    if entry:
        value, ts = entry
        if time.monotonic() - ts < (_TTL_LONG if "ldongCode" in key else _TTL_SHORT):
            return value
    return None


def _cache_set(key: str, value: dict) -> None:
    _CACHE[key] = (value, time.monotonic())


# ── Input validation ──────────────────────────────────────────────────────────
VALID_LANG   = {"KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS"}
VALID_THEME  = {"EX050100", "EX050200", "EX050300", "EX050400",
                "EX050500", "EX050600", "EX050700"}
VALID_ARRANGE_AREA     = {"A", "C", "D", "O", "Q", "R"}
VALID_ARRANGE_LOCATION = {"A", "C", "D", "O", "Q", "R", "E", "S"}
VALID_SHOWFLAG   = {"0", "1"}
VALID_IMAGE_YN   = {"Y", "N"}
VALID_L_DONG_LIST_YN = {"Y", "N"}
_RE_CONTENT_ID   = re.compile(r"^\d{1,15}$")
_RE_DATE_YYMMDD  = re.compile(r"^\d{6}$")
_RE_REGION_CD    = re.compile(r"^\d{1,8}$")
MAX_ROWS         = 100
MAX_KEYWORD_LEN  = 100


def _check_lang(v: str) -> str:
    v = v.upper().strip()
    if v not in VALID_LANG:
        raise ValueError(f"Invalid lang_div_cd '{v}'. Must be one of {sorted(VALID_LANG)}.")
    return v


def _check_rows(n: int) -> int:
    if not isinstance(n, int) or n < 1:
        n = 1
    return min(n, MAX_ROWS)


def _check_page(n: int) -> int:
    if not isinstance(n, int) or n < 1:
        n = 1
    return n


def _check_arrange(v: Optional[str], location: bool = False) -> Optional[str]:
    if not v:
        return None
    v = v.upper().strip()
    valid = VALID_ARRANGE_LOCATION if location else VALID_ARRANGE_AREA
    if v not in valid:
        raise ValueError(f"Invalid arrange '{v}'. Must be one of {sorted(valid)}.")
    return v


def _check_theme(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.upper().strip()
    if v not in VALID_THEME:
        raise ValueError(f"Invalid wellness_thema_cd '{v}'. Must be one of {sorted(VALID_THEME)}.")
    return v


def _check_content_id(v: str) -> str:
    v = v.strip()
    if not _RE_CONTENT_ID.match(v):
        raise ValueError(f"Invalid content_id '{v}'. Must be 1–15 digits.")
    return v


def _check_date(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.strip()
    if not _RE_DATE_YYMMDD.match(v):
        raise ValueError(f"Invalid date '{v}'. Must be YYMMDD (6 digits).")
    return v


def _check_region_cd(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.strip()
    if not _RE_REGION_CD.match(v):
        raise ValueError(f"Invalid region code '{v}'. Must be 1–8 digits.")
    return v


def _check_keyword(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("keyword must not be empty.")
    if len(v) > MAX_KEYWORD_LEN:
        raise ValueError(f"keyword too long (max {MAX_KEYWORD_LEN} characters).")
    return v


def _check_radius(v: int) -> int:
    if not isinstance(v, int) or v < 1:
        raise ValueError("radius must be a positive integer (metres).")
    if v > 20000:
        raise ValueError("radius must not exceed 20000 metres (20 km).")
    return v


# ── Error type ────────────────────────────────────────────────────────────────
class WellnessAPIError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ── Response parsing ──────────────────────────────────────────────────────────
def _parse_response(raw: str) -> dict:
    raw = raw.strip()

    try:
        data = json.loads(raw)
        response = data.get("response", {})
        header = response.get("header", {})
        result_code = str(header.get("resultCode", ""))
        result_msg = header.get("resultMsg", "UNKNOWN")
        if result_code not in ("0000", "00"):
            raise WellnessAPIError(result_code, result_msg)
        return response.get("body", {})
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise WellnessAPIError("PARSE_ERROR", f"Failed to parse API response: {e}")

    if root.tag == "OpenAPI_ServiceResponse":
        header_el = root.find("cmmMsgHeader")
        if header_el is not None:
            err_msg = header_el.findtext("errMsg", "UNKNOWN")
            return_auth_msg = header_el.findtext("returnAuthMsg", "UNKNOWN")
            reason_code = header_el.findtext("returnReasonCode", "99")
            raise WellnessAPIError(reason_code, f"{err_msg}: {return_auth_msg}")
        raise WellnessAPIError("99", "Unknown portal error")

    header_el = root.find(".//header")
    if header_el is not None:
        result_code = header_el.findtext("resultCode", "")
        result_msg = header_el.findtext("resultMsg", "UNKNOWN")
        if result_code not in ("0000", "00"):
            raise WellnessAPIError(result_code, result_msg)

    body_el = root.find(".//body")
    if body_el is None:
        raise WellnessAPIError("PARSE_ERROR", "No body element in API response")

    items_el = body_el.find("items")
    items = []
    if items_el is not None:
        for item_el in items_el.findall("item"):
            item = {child.tag: child.text for child in item_el}
            items.append(item)

    return {
        "items": {"item": items},
        "numOfRows": int(body_el.findtext("numOfRows", "0") or "0"),
        "pageNo": int(body_el.findtext("pageNo", "1") or "1"),
        "totalCount": int(body_el.findtext("totalCount", "0") or "0"),
    }


def _extract_items(body: dict) -> list:
    items_wrapper = body.get("items", {})
    if not items_wrapper:
        return []
    items = items_wrapper.get("item", [])
    if isinstance(items, dict):
        return [items]
    if items is None:
        return []
    return items


# ── Client ────────────────────────────────────────────────────────────────────
class WellnessClient:
    def __init__(self):
        self.api_key = os.environ.get("WELLNESS_API_KEY_ENCODING")
        if not self.api_key:
            raise RuntimeError(
                "WELLNESS_API_KEY_ENCODING environment variable is not set. "
                "Please configure this Replit Secret before starting the server."
            )

    def _base_params(self, lang_div_cd: str, num_of_rows: int, page_no: int) -> dict:
        # serviceKey is intentionally NOT included here.
        # The data.go.kr "encoding key" is already URL-encoded; if placed in
        # httpx's params={} dict it would be encoded a second time, mangling
        # the key and causing HTTP 401.  It is embedded raw into the URL in
        # _get() instead.
        return {
            "MobileOS": "ETC",
            "MobileApp": "WellnessTourismMCP",
            "_type": "json",
            "langDivCd": lang_div_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
        }

    async def _get(self, endpoint: str, params: dict) -> dict:
        key = _cache_key(endpoint, params)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        # Build the full URL manually.
        # Root cause of HTTP 401: when httpx receives both a URL with an existing
        # query string (?serviceKey=...) AND a params={} dict, it silently drops
        # the URL's query string and only uses params={}.  serviceKey is never
        # sent → upstream returns 401.
        # Fix: urlencode the other params and concatenate everything into one URL
        # string, then call client.get() with NO params= argument so httpx cannot
        # interfere with the query string.
        full_url = f"{BASE_URL}/{endpoint}?serviceKey={self.api_key}&{urlencode(params)}"
        client = _get_http_client()
        try:
            response = await client.get(full_url)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise WellnessAPIError("TIMEOUT", "Upstream API request timed out.")
        except httpx.HTTPStatusError as e:
            raise WellnessAPIError("HTTP_ERROR", f"Upstream API returned HTTP {e.response.status_code}.")
        except httpx.RequestError:
            raise WellnessAPIError("NETWORK_ERROR", "Could not reach the upstream API.")

        result = _parse_response(response.text)
        _cache_set(key, result)
        return result

    # ── Tools ─────────────────────────────────────────────────────────────────

    async def get_legal_district_codes(
        self,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_list_yn: Optional[str] = None,
    ) -> dict:
        lang_div_cd   = _check_lang(lang_div_cd)
        num_of_rows   = _check_rows(num_of_rows)
        page_no       = _check_page(page_no)
        l_dong_regn_cd = _check_region_cd(l_dong_regn_cd)
        if l_dong_list_yn:
            l_dong_list_yn = l_dong_list_yn.upper().strip()
            if l_dong_list_yn not in VALID_L_DONG_LIST_YN:
                raise ValueError("l_dong_list_yn must be 'Y' or 'N'.")

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if l_dong_regn_cd:
            params["lDongRegnCd"] = l_dong_regn_cd
        if l_dong_list_yn:
            params["lDongListYn"] = l_dong_list_yn

        body = await self._get("ldongCode", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def search_wellness_by_area(
        self,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        arrange: Optional[str] = None,
        content_type_id: Optional[str] = None,
        mdfcn_dt: Optional[str] = None,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_signgu_cd: Optional[str] = None,
        wellness_thema_cd: Optional[str] = None,
    ) -> dict:
        lang_div_cd    = _check_lang(lang_div_cd)
        num_of_rows    = _check_rows(num_of_rows)
        page_no        = _check_page(page_no)
        arrange        = _check_arrange(arrange, location=False)
        wellness_thema_cd = _check_theme(wellness_thema_cd)
        mdfcn_dt       = _check_date(mdfcn_dt)
        l_dong_regn_cd = _check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = _check_region_cd(l_dong_signgu_cd)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id.strip()
        if mdfcn_dt:
            params["mdfcnDt"] = mdfcn_dt
        if l_dong_regn_cd:
            params["lDongRegnCd"] = l_dong_regn_cd
        if l_dong_signgu_cd:
            params["lDongSignguCd"] = l_dong_signgu_cd
        if wellness_thema_cd:
            params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("areaBasedList", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def search_wellness_by_location(
        self,
        map_x: float,
        map_y: float,
        radius: int,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        arrange: Optional[str] = None,
        content_type_id: Optional[str] = None,
        mdfcn_dt: Optional[str] = None,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_signgu_cd: Optional[str] = None,
        wellness_thema_cd: Optional[str] = None,
    ) -> dict:
        lang_div_cd    = _check_lang(lang_div_cd)
        num_of_rows    = _check_rows(num_of_rows)
        page_no        = _check_page(page_no)
        radius         = _check_radius(int(radius))
        arrange        = _check_arrange(arrange, location=True)
        wellness_thema_cd = _check_theme(wellness_thema_cd)
        mdfcn_dt       = _check_date(mdfcn_dt)
        l_dong_regn_cd = _check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = _check_region_cd(l_dong_signgu_cd)

        if not isinstance(map_x, (int, float)) or not (-180 <= map_x <= 180):
            raise ValueError("map_x (longitude) must be a number between -180 and 180.")
        if not isinstance(map_y, (int, float)) or not (-90 <= map_y <= 90):
            raise ValueError("map_y (latitude) must be a number between -90 and 90.")

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["mapX"] = map_x
        params["mapY"] = map_y
        params["radius"] = radius
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id.strip()
        if mdfcn_dt:
            params["mdfcnDt"] = mdfcn_dt
        if l_dong_regn_cd:
            params["lDongRegnCd"] = l_dong_regn_cd
        if l_dong_signgu_cd:
            params["lDongSignguCd"] = l_dong_signgu_cd
        if wellness_thema_cd:
            params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("locationBasedList", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def search_wellness_by_keyword(
        self,
        keyword: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        arrange: Optional[str] = None,
        content_type_id: Optional[str] = None,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_signgu_cd: Optional[str] = None,
        wellness_thema_cd: Optional[str] = None,
    ) -> dict:
        keyword        = _check_keyword(keyword)
        lang_div_cd    = _check_lang(lang_div_cd)
        num_of_rows    = _check_rows(num_of_rows)
        page_no        = _check_page(page_no)
        arrange        = _check_arrange(arrange, location=False)
        wellness_thema_cd = _check_theme(wellness_thema_cd)
        l_dong_regn_cd = _check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = _check_region_cd(l_dong_signgu_cd)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["keyword"] = keyword
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id.strip()
        if l_dong_regn_cd:
            params["lDongRegnCd"] = l_dong_regn_cd
        if l_dong_signgu_cd:
            params["lDongSignguCd"] = l_dong_signgu_cd
        if wellness_thema_cd:
            params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("searchKeyword", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def get_wellness_sync_list(
        self,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        arrange: Optional[str] = None,
        content_type_id: Optional[str] = None,
        showflag: Optional[str] = None,
        mdfcn_dt: Optional[str] = None,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_signgu_cd: Optional[str] = None,
        old_content_id: Optional[str] = None,
        wellness_thema_cd: Optional[str] = None,
    ) -> dict:
        lang_div_cd    = _check_lang(lang_div_cd)
        num_of_rows    = _check_rows(num_of_rows)
        page_no        = _check_page(page_no)
        arrange        = _check_arrange(arrange, location=False)
        wellness_thema_cd = _check_theme(wellness_thema_cd)
        mdfcn_dt       = _check_date(mdfcn_dt)
        l_dong_regn_cd = _check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = _check_region_cd(l_dong_signgu_cd)
        if showflag is not None:
            showflag = showflag.strip()
            if showflag not in VALID_SHOWFLAG:
                raise ValueError("showflag must be '0' or '1'.")
        if old_content_id:
            old_content_id = _check_content_id(old_content_id)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id.strip()
        if showflag is not None:
            params["showflag"] = showflag
        if mdfcn_dt:
            params["mdfcnDt"] = mdfcn_dt
        if l_dong_regn_cd:
            params["lDongRegnCd"] = l_dong_regn_cd
        if l_dong_signgu_cd:
            params["lDongSignguCd"] = l_dong_signgu_cd
        if old_content_id:
            params["oldContentId"] = old_content_id
        if wellness_thema_cd:
            params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("wellnessTursmSyncList", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def get_wellness_common_info(
        self,
        content_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> dict:
        content_id  = _check_content_id(content_id)
        lang_div_cd = _check_lang(lang_div_cd)
        num_of_rows = _check_rows(num_of_rows)
        page_no     = _check_page(page_no)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"] = content_id
        body = await self._get("detailCommon", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def get_wellness_intro_info(
        self,
        content_id: str,
        content_type_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> dict:
        content_id      = _check_content_id(content_id)
        lang_div_cd     = _check_lang(lang_div_cd)
        num_of_rows     = _check_rows(num_of_rows)
        page_no         = _check_page(page_no)
        content_type_id = content_type_id.strip()

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"] = content_id
        params["contentTypeId"] = content_type_id
        body = await self._get("detailIntro", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def get_wellness_repeating_info(
        self,
        content_id: str,
        content_type_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> dict:
        content_id      = _check_content_id(content_id)
        lang_div_cd     = _check_lang(lang_div_cd)
        num_of_rows     = _check_rows(num_of_rows)
        page_no         = _check_page(page_no)
        content_type_id = content_type_id.strip()

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"] = content_id
        params["contentTypeId"] = content_type_id
        body = await self._get("detailInfo", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }

    async def get_wellness_images(
        self,
        content_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        image_yn: Optional[str] = None,
    ) -> dict:
        content_id  = _check_content_id(content_id)
        lang_div_cd = _check_lang(lang_div_cd)
        num_of_rows = _check_rows(num_of_rows)
        page_no     = _check_page(page_no)
        if image_yn:
            image_yn = image_yn.upper().strip()
            if image_yn not in VALID_IMAGE_YN:
                raise ValueError("image_yn must be 'Y' or 'N'.")

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"] = content_id
        if image_yn:
            params["imageYN"] = image_yn
        body = await self._get("detailImage", params)
        items = _extract_items(body)
        return {
            "items": items,
            "numOfRows": body.get("numOfRows", num_of_rows),
            "pageNo": body.get("pageNo", page_no),
            "totalCount": body.get("totalCount", 0),
        }
