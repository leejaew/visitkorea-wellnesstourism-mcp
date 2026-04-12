import os
from typing import Optional
from urllib.parse import urlencode

import httpx

from .cache import cache_get, cache_key, cache_set, get_fetch_lock
from .config import BASE_URL, get_http_client
from .parser import WellnessAPIError, extract_items, parse_response
from .validation import (
    VALID_IMAGE_YN,
    VALID_L_DONG_LIST_YN,
    VALID_SHOWFLAG,
    check_arrange,
    check_content_id,
    check_date,
    check_keyword,
    check_lang,
    check_page,
    check_radius,
    check_region_cd,
    check_rows,
    check_theme,
)


class WellnessClient:
    """Async HTTP client for the KTO WellnessTursmService Open API.

    One shared instance is created at startup and reused across all tool calls.
    All upstream requests are validated, cached, and protected against stampede.
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("WELLNESS_API_KEY_ENCODING")
        if not self.api_key:
            raise RuntimeError(
                "WELLNESS_API_KEY_ENCODING environment variable is not set. "
                "Please configure this Replit Secret before starting the server."
            )

    def _base_params(self, lang_div_cd: str, num_of_rows: int, page_no: int) -> dict:
        # serviceKey is NOT included here — the encoding key must be embedded
        # directly in the URL string; passing it via httpx params= would
        # cause double-encoding and a 401 from the upstream API.
        return {
            "MobileOS":  "ETC",
            "MobileApp": "WellnessTourismMCP",
            "_type":     "json",
            "langDivCd": lang_div_cd,
            "numOfRows": num_of_rows,
            "pageNo":    page_no,
        }

    async def _get(self, endpoint: str, params: dict) -> dict:
        key = cache_key(endpoint, params)

        # Fast path: return from cache without acquiring any lock.
        cached = cache_get(key)
        if cached is not None:
            return cached

        # Acquire a per-key lock: only one coroutine fires the upstream request
        # at a time; all other waiters recheck the cache after the lock releases.
        async with get_fetch_lock(key):
            cached = cache_get(key)
            if cached is not None:
                return cached

            # Build the full URL in one string so httpx cannot discard the
            # pre-encoded serviceKey (httpx drops the URL's query string when
            # params={} is also passed).
            full_url = (
                f"{BASE_URL}/{endpoint}"
                f"?serviceKey={self.api_key}&{urlencode(params)}"
            )
            client = get_http_client()
            try:
                response = await client.get(full_url)
                response.raise_for_status()
            except httpx.TimeoutException:
                raise WellnessAPIError("TIMEOUT", "Upstream API request timed out.")
            except httpx.HTTPStatusError as e:
                raise WellnessAPIError(
                    "HTTP_ERROR",
                    f"Upstream API returned HTTP {e.response.status_code}.",
                )
            except httpx.RequestError:
                raise WellnessAPIError("NETWORK_ERROR", "Could not reach the upstream API.")

            result = parse_response(response.text)
            cache_set(key, result)
            return result

    # ── Catalog ───────────────────────────────────────────────────────────────

    async def get_legal_district_codes(
        self,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_list_yn: Optional[str] = None,
    ) -> dict:
        lang_div_cd    = check_lang(lang_div_cd)
        num_of_rows    = check_rows(num_of_rows)
        page_no        = check_page(page_no)
        l_dong_regn_cd = check_region_cd(l_dong_regn_cd)
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
        return self._page(body, extract_items(body), num_of_rows, page_no)

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
        lang_div_cd      = check_lang(lang_div_cd)
        num_of_rows      = check_rows(num_of_rows)
        page_no          = check_page(page_no)
        arrange          = check_arrange(arrange, location=False)
        wellness_thema_cd = check_theme(wellness_thema_cd)
        mdfcn_dt         = check_date(mdfcn_dt)
        l_dong_regn_cd   = check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = check_region_cd(l_dong_signgu_cd)
        if showflag is not None:
            showflag = showflag.strip()
            if showflag not in VALID_SHOWFLAG:
                raise ValueError("showflag must be '0' or '1'.")
        if old_content_id:
            old_content_id = check_content_id(old_content_id)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if arrange:           params["arrange"]          = arrange
        if content_type_id:   params["contentTypeId"]    = content_type_id.strip()
        if showflag is not None: params["showflag"]       = showflag
        if mdfcn_dt:          params["mdfcnDt"]          = mdfcn_dt
        if l_dong_regn_cd:    params["lDongRegnCd"]      = l_dong_regn_cd
        if l_dong_signgu_cd:  params["lDongSignguCd"]    = l_dong_signgu_cd
        if old_content_id:    params["oldContentId"]     = old_content_id
        if wellness_thema_cd: params["wellnessThemaCd"]  = wellness_thema_cd

        body = await self._get("wellnessTursmSyncList", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

    # ── Search ────────────────────────────────────────────────────────────────

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
        lang_div_cd      = check_lang(lang_div_cd)
        num_of_rows      = check_rows(num_of_rows)
        page_no          = check_page(page_no)
        arrange          = check_arrange(arrange, location=False)
        wellness_thema_cd = check_theme(wellness_thema_cd)
        mdfcn_dt         = check_date(mdfcn_dt)
        l_dong_regn_cd   = check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = check_region_cd(l_dong_signgu_cd)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if arrange:           params["arrange"]         = arrange
        if content_type_id:   params["contentTypeId"]   = content_type_id.strip()
        if mdfcn_dt:          params["mdfcnDt"]         = mdfcn_dt
        if l_dong_regn_cd:    params["lDongRegnCd"]     = l_dong_regn_cd
        if l_dong_signgu_cd:  params["lDongSignguCd"]   = l_dong_signgu_cd
        if wellness_thema_cd: params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("areaBasedList", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

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
        lang_div_cd      = check_lang(lang_div_cd)
        num_of_rows      = check_rows(num_of_rows)
        page_no          = check_page(page_no)
        radius           = check_radius(int(radius))
        arrange          = check_arrange(arrange, location=True)
        wellness_thema_cd = check_theme(wellness_thema_cd)
        mdfcn_dt         = check_date(mdfcn_dt)
        l_dong_regn_cd   = check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = check_region_cd(l_dong_signgu_cd)
        if not isinstance(map_x, (int, float)) or not (-180 <= map_x <= 180):
            raise ValueError("map_x (longitude) must be a number between -180 and 180.")
        if not isinstance(map_y, (int, float)) or not (-90 <= map_y <= 90):
            raise ValueError("map_y (latitude) must be a number between -90 and 90.")

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["mapX"]   = map_x
        params["mapY"]   = map_y
        params["radius"] = radius
        if arrange:           params["arrange"]         = arrange
        if content_type_id:   params["contentTypeId"]   = content_type_id.strip()
        if mdfcn_dt:          params["mdfcnDt"]         = mdfcn_dt
        if l_dong_regn_cd:    params["lDongRegnCd"]     = l_dong_regn_cd
        if l_dong_signgu_cd:  params["lDongSignguCd"]   = l_dong_signgu_cd
        if wellness_thema_cd: params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("locationBasedList", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

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
        keyword          = check_keyword(keyword)
        lang_div_cd      = check_lang(lang_div_cd)
        num_of_rows      = check_rows(num_of_rows)
        page_no          = check_page(page_no)
        arrange          = check_arrange(arrange, location=False)
        wellness_thema_cd = check_theme(wellness_thema_cd)
        l_dong_regn_cd   = check_region_cd(l_dong_regn_cd)
        l_dong_signgu_cd = check_region_cd(l_dong_signgu_cd)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["keyword"] = keyword
        if arrange:           params["arrange"]         = arrange
        if content_type_id:   params["contentTypeId"]   = content_type_id.strip()
        if l_dong_regn_cd:    params["lDongRegnCd"]     = l_dong_regn_cd
        if l_dong_signgu_cd:  params["lDongSignguCd"]   = l_dong_signgu_cd
        if wellness_thema_cd: params["wellnessThemaCd"] = wellness_thema_cd

        body = await self._get("searchKeyword", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

    # ── Detail ────────────────────────────────────────────────────────────────

    async def get_wellness_common_info(
        self,
        content_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> dict:
        content_id  = check_content_id(content_id)
        lang_div_cd = check_lang(lang_div_cd)
        num_of_rows = check_rows(num_of_rows)
        page_no     = check_page(page_no)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"] = content_id
        body = await self._get("detailCommon", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

    async def get_wellness_intro_info(
        self,
        content_id: str,
        content_type_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> dict:
        content_id      = check_content_id(content_id)
        lang_div_cd     = check_lang(lang_div_cd)
        num_of_rows     = check_rows(num_of_rows)
        page_no         = check_page(page_no)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"]     = content_id
        params["contentTypeId"] = content_type_id.strip()
        body = await self._get("detailIntro", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

    async def get_wellness_repeating_info(
        self,
        content_id: str,
        content_type_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> dict:
        content_id      = check_content_id(content_id)
        lang_div_cd     = check_lang(lang_div_cd)
        num_of_rows     = check_rows(num_of_rows)
        page_no         = check_page(page_no)

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"]     = content_id
        params["contentTypeId"] = content_type_id.strip()
        body = await self._get("detailInfo", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

    async def get_wellness_images(
        self,
        content_id: str,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        image_yn: Optional[str] = None,
    ) -> dict:
        content_id  = check_content_id(content_id)
        lang_div_cd = check_lang(lang_div_cd)
        num_of_rows = check_rows(num_of_rows)
        page_no     = check_page(page_no)
        if image_yn:
            image_yn = image_yn.upper().strip()
            if image_yn not in VALID_IMAGE_YN:
                raise ValueError("image_yn must be 'Y' or 'N'.")

        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["contentId"] = content_id
        if image_yn:
            params["imageYN"] = image_yn
        body = await self._get("detailImage", params)
        return self._page(body, extract_items(body), num_of_rows, page_no)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _page(body: dict, items: list, num_of_rows: int, page_no: int) -> dict:
        return {
            "items":      items,
            "numOfRows":  body.get("numOfRows",  num_of_rows),
            "pageNo":     body.get("pageNo",     page_no),
            "totalCount": body.get("totalCount", 0),
        }
