from typing import Optional

from api import WellnessAPIError, WellnessClient

_client: Optional[WellnessClient] = None


def _get_client() -> WellnessClient:
    global _client
    if _client is None:
        _client = WellnessClient()
    return _client


async def search_wellness_by_area(
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
    """
    List wellness tourism spots filtered by administrative region, content type,
    wellness theme, and sort order.

    Parameters:
        lang_div_cd: Language code. Default "KOR".
            Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order. "A"=title, "C"=modified, "D"=created (no image);
            "O"/"Q"/"R" = same but image required.
        content_type_id: Tourism category.
            Korean: 12=tourist,14=cultural,15=event,28=leisure,32=accommodation,
                    38=shopping,39=restaurant,25=travel course.
            Multilingual: 76=tourist,78=cultural,85=event,75=leisure,80=accommodation,
                          79=shopping,82=restaurant,77=transport.
        mdfcn_dt: Modified date filter in YYMMDD format.
        l_dong_regn_cd: Province/city code (e.g. "11" for Seoul).
        l_dong_signgu_cd: District code. Requires l_dong_regn_cd.
        wellness_thema_cd: "EX050100"=Hot spring/Spa, "EX050200"=Jjimjilbang,
            "EX050300"=Traditional medicine, "EX050400"=Healing meditation,
            "EX050500"=Beauty spa, "EX050600"=Other wellness, "EX050700"=Nature healing.

    Returns dict with items (contentId, title, baseAddr, mapX, mapY, tel,
    orgImage, wellnessThemaCd, etc.), totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().search_wellness_by_area(
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            arrange=arrange,
            content_type_id=content_type_id,
            mdfcn_dt=mdfcn_dt,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            wellness_thema_cd=wellness_thema_cd,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def search_wellness_by_location(
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
    """
    List wellness tourism spots within a radius of GPS coordinates (WGS84).
    Maximum radius: 20000 metres (20 km).

    Parameters:
        map_x: GPS longitude in WGS84 (e.g. 126.9780 for central Seoul). REQUIRED.
        map_y: GPS latitude in WGS84 (e.g. 37.5665 for central Seoul). REQUIRED.
        radius: Search radius in metres. Max 20000. REQUIRED.
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: "E"=distance nearest first (no image); "S"=distance (image required).
            Also accepts "A","C","D","O","Q","R".
        content_type_id: Tourism category filter (same codes as search_wellness_by_area).
        mdfcn_dt: Modified date filter in YYMMDD format.
        l_dong_regn_cd: Province/city code filter.
        l_dong_signgu_cd: District code filter.
        wellness_thema_cd: Wellness theme — same values as search_wellness_by_area.

    Returns dict with items (same as search_wellness_by_area plus "dist" in metres),
    totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().search_wellness_by_location(
            map_x=map_x,
            map_y=map_y,
            radius=radius,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            arrange=arrange,
            content_type_id=content_type_id,
            mdfcn_dt=mdfcn_dt,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            wellness_thema_cd=wellness_thema_cd,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def search_wellness_by_keyword(
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
    """
    Full-text keyword search across all wellness tourism content.

    Parameters:
        keyword: Search term — Korean (e.g. "스파") or English (e.g. "spa"). REQUIRED.
        lang_div_cd: Language code. Default "KOR".
            Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order "A"/"C"/"D"/"O"/"Q"/"R".
        content_type_id: Tourism category filter (same codes as search_wellness_by_area).
        l_dong_regn_cd: Province/city code filter.
        l_dong_signgu_cd: District code filter. Requires l_dong_regn_cd.
        wellness_thema_cd: Wellness theme — same values as search_wellness_by_area.

    Returns dict with items (same fields as search_wellness_by_area),
    totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().search_wellness_by_keyword(
            keyword=keyword,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            arrange=arrange,
            content_type_id=content_type_id,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            wellness_thema_cd=wellness_thema_cd,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}
