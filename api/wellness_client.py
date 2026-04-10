import os
import json
import xml.etree.ElementTree as ET
from typing import Any, Optional
import httpx

BASE_URL = "http://apis.data.go.kr/B551011/WellnessTursmService"
TIMEOUT = 30.0


class WellnessAPIError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


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

        body = response.get("body", {})
        return body

    except (json.JSONDecodeError, ValueError):
        pass

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise WellnessAPIError("PARSE_ERROR", f"Failed to parse response: {e}")

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
        raise WellnessAPIError("PARSE_ERROR", "No body in XML response")

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


class WellnessClient:
    def __init__(self):
        self.api_key = os.environ.get("WELLNESS_API_KEY_ENCODING")
        if not self.api_key:
            raise RuntimeError(
                "WELLNESS_API_KEY_ENCODING environment variable is not set. "
                "Please configure this Replit Secret before starting the server."
            )

    def _base_params(self, lang_div_cd: str = "KOR", num_of_rows: int = 10, page_no: int = 1) -> dict:
        return {
            "serviceKey": self.api_key,
            "MobileOS": "ETC",
            "MobileApp": "WellnessTourismMCP",
            "_type": "json",
            "langDivCd": lang_div_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
        }

    async def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{BASE_URL}/{endpoint}"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return _parse_response(response.text)

    async def get_legal_district_codes(
        self,
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
        l_dong_regn_cd: Optional[str] = None,
        l_dong_list_yn: Optional[str] = None,
    ) -> dict:
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
        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id
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
        if radius > 20000:
            raise ValueError("radius must not exceed 20000 metres (20 km)")
        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["mapX"] = map_x
        params["mapY"] = map_y
        params["radius"] = radius
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id
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
        from urllib.parse import quote
        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        params["keyword"] = keyword
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id
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
        params = self._base_params(lang_div_cd, num_of_rows, page_no)
        if arrange:
            params["arrange"] = arrange
        if content_type_id:
            params["contentTypeId"] = content_type_id
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
