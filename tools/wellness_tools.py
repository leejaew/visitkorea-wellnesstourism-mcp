from typing import Optional, Any
from api.wellness_client import WellnessClient, WellnessAPIError

_client: Optional[WellnessClient] = None


def get_client() -> WellnessClient:
    global _client
    if _client is None:
        _client = WellnessClient()
    return _client


async def get_legal_district_codes(
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    l_dong_regn_cd: Optional[str] = None,
    l_dong_list_yn: Optional[str] = None,
) -> dict:
    """
    Retrieve legal administrative district (법정동) codes for filtering wellness tourism queries by region.

    Returns province/city codes (시도) and district codes (시군구). Use these codes as input
    to other tools that accept lDongRegnCd / lDongSignguCd parameters.

    Parameters:
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR" (Korean), "ENG" (English), "JPN" (Japanese),
            "CHS" (Chinese Simplified), "CHT" (Chinese Traditional),
            "GER" (German), "FRE" (French), "SPN" (Spanish), "RUS" (Russian).
        num_of_rows (int, optional): Number of results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.
        l_dong_regn_cd (str, optional): Province/city code to filter results (e.g. "11" for Seoul).
            When omitted, all province/city codes are returned.
        l_dong_list_yn (str, optional): "N" = return 시도/시군구 codes (default);
            "Y" = return full 법정동 list with both province and district fields.

    Returns:
        dict with keys:
            - items (list): Each item has "code", "name", "rnum" fields when lDongListYn=N;
              or "lDongRegnCd", "lDongRegnNm", "lDongSignguCd", "lDongSignguNm", "rnum" when lDongListYn=Y.
            - totalCount (int): Total number of results.
            - pageNo (int): Current page number.
            - numOfRows (int): Results per page.
    """
    try:
        return await get_client().get_legal_district_codes(
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_list_yn=l_dong_list_yn,
        )
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


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
    List wellness tourism spots filtered by administrative region, content type, wellness theme, and sort order.

    Parameters:
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.
        arrange (str, optional): Sort order.
            "A" = title (alphabetical, no image required)
            "C" = modified date, latest first (no image required)
            "D" = created date (no image required)
            "O" = title (image required)
            "Q" = modified date (image required)
            "R" = created date (image required)
        content_type_id (str, optional): Tourism category filter.
            Korean: "12" tourist attraction, "14" cultural facility, "15" event/festival,
            "28" leisure sports, "32" accommodation, "38" shopping, "39" restaurant, "25" travel course.
            Multilingual: "76" tourist attraction, "78" cultural facility, "85" event/festival,
            "75" leisure sports, "80" accommodation, "79" shopping, "82" restaurant, "77" transport.
        mdfcn_dt (str, optional): Modified date filter in YYMMDD format (e.g. "250101").
        l_dong_regn_cd (str, optional): Province/city code (e.g. "11" for Seoul).
        l_dong_signgu_cd (str, optional): District code. Requires l_dong_regn_cd.
        wellness_thema_cd (str, optional): Wellness theme filter.
            "EX050100" = Hot spring/Sauna/Spa (온천/사우나/스파)
            "EX050200" = Jjimjilbang - Korean sauna (찜질방)
            "EX050300" = Korean traditional medicine experience (한방 체험)
            "EX050400" = Healing meditation (힐링 명상)
            "EX050500" = Beauty spa (뷰티 스파)
            "EX050600" = Other wellness (기타 웰니스)
            "EX050700" = Nature healing (자연 치유)

    Returns:
        dict with keys:
            - items (list): Each item includes contentId, contentTypeId, title, baseAddr,
              detailAddr, zipCd, mapX, mapY, mlevel, tel, orgImage, thumbImage,
              cpyrhtDivCd, regDt, mdfcnDt, lDongRegnCd, lDongSignguCd, wellnessThemaCd, langDivCd.
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().search_wellness_by_area(
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

    Parameters:
        map_x (float, required): GPS longitude in WGS84 format (e.g. 126.981611 for Seoul).
        map_y (float, required): GPS latitude in WGS84 format (e.g. 37.568477 for Seoul).
        radius (int, required): Search radius in metres. Maximum allowed value: 20000 (20 km).
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.
        arrange (str, optional): Sort order.
            "A"/"C"/"D"/"O"/"Q"/"R" = same as search_wellness_by_area.
            "E" = distance nearest first (no image required) — only valid on this endpoint.
            "S" = distance nearest first (image required) — only valid on this endpoint.
        content_type_id (str, optional): Tourism category filter — same codes as search_wellness_by_area.
        mdfcn_dt (str, optional): Modified date filter in YYMMDD format.
        l_dong_regn_cd (str, optional): Province/city code filter.
        l_dong_signgu_cd (str, optional): District code filter. Requires l_dong_regn_cd.
        wellness_thema_cd (str, optional): Wellness theme filter.
            "EX050100" Hot spring/Sauna/Spa, "EX050200" Jjimjilbang, "EX050300" Traditional medicine,
            "EX050400" Healing meditation, "EX050500" Beauty spa, "EX050600" Other wellness,
            "EX050700" Nature healing.

    Returns:
        dict with keys:
            - items (list): Same fields as search_wellness_by_area, plus "dist" (distance in metres).
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().search_wellness_by_location(
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
        return {"error": True, "code": "INVALID_RADIUS", "message": str(e)}
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
        keyword (str, required): Search keyword. Can be Korean (e.g. "스파") or English (e.g. "spa").
            Korean keywords are automatically URL-encoded before the API call.
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.
        arrange (str, optional): Sort order "A"/"C"/"D"/"O"/"Q"/"R" — see search_wellness_by_area.
        content_type_id (str, optional): Tourism category filter — same codes as search_wellness_by_area.
        l_dong_regn_cd (str, optional): Province/city code filter.
        l_dong_signgu_cd (str, optional): District code filter. Requires l_dong_regn_cd.
        wellness_thema_cd (str, optional): Wellness theme filter.
            "EX050100" Hot spring/Sauna/Spa, "EX050200" Jjimjilbang, "EX050300" Traditional medicine,
            "EX050400" Healing meditation, "EX050500" Beauty spa, "EX050600" Other wellness,
            "EX050700" Nature healing.

    Returns:
        dict with keys:
            - items (list): Same fields as search_wellness_by_area.
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().search_wellness_by_keyword(
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
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def get_wellness_sync_list(
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
    """
    Retrieve the wellness tourism synchronisation list for applications that maintain a local dataset copy.

    Designed for delta sync use cases. Supports filtering by display status (showflag)
    and by a previous content ID (old_content_id) to retrieve only updated records.

    Parameters:
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.
        arrange (str, optional): Sort order "A"/"C"/"D"/"O"/"Q"/"R" — see search_wellness_by_area.
        content_type_id (str, optional): Tourism category filter — same codes as search_wellness_by_area.
        showflag (str, optional): Display status filter. "1" = publicly visible, "0" = hidden.
        mdfcn_dt (str, optional): Modified date filter in YYMMDD format.
        l_dong_regn_cd (str, optional): Province/city code filter.
        l_dong_signgu_cd (str, optional): District code filter. Requires l_dong_regn_cd.
        old_content_id (str, optional): Previous content ID for delta sync queries.
        wellness_thema_cd (str, optional): Wellness theme filter.
            "EX050100" Hot spring/Sauna/Spa, "EX050200" Jjimjilbang, "EX050300" Traditional medicine,
            "EX050400" Healing meditation, "EX050500" Beauty spa, "EX050600" Other wellness,
            "EX050700" Nature healing.

    Returns:
        dict with keys:
            - items (list): Same fields as search_wellness_by_area, plus "showflag" (display flag)
              and "oldContentId" (previous content ID for DB synchronisation).
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().get_wellness_sync_list(
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            arrange=arrange,
            content_type_id=content_type_id,
            showflag=showflag,
            mdfcn_dt=mdfcn_dt,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            old_content_id=old_content_id,
            wellness_thema_cd=wellness_thema_cd,
        )
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def get_wellness_common_info(
    content_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    """
    Retrieve the full common detail record for a specific wellness tourism content item.

    Returns title, contact info, address, GPS coordinates, overview text, homepage URL,
    copyright type, and wellness theme code.

    Parameters:
        content_id (str, required): The content ID to retrieve (e.g. "702551").
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.

    Returns:
        dict with keys:
            - items (list): Each item includes contentId, contentTypeId, title, homepage,
              baseAddr, detailAddr, zipCd, mapX, mapY, mlevel, tel, telname, overview,
              orgImage, thumbImage, cpyrhtDivCd, regDt, mdfcnDt, lDongRegnCd,
              lDongSignguCd, wellnessThemaCd.
              Note: the "homepage" field may contain raw HTML anchor tags.
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().get_wellness_common_info(
            content_id=content_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def get_wellness_intro_info(
    content_id: str,
    content_type_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    """
    Retrieve type-specific introductory details for a wellness tourism content item.

    IMPORTANT: Response fields vary by content_type_id. The field list below applies
    to contentTypeId 12 or 76 (tourist attraction — the primary wellness category).
    Other content types (accommodation 32/80, restaurant 39/82, etc.) return different fields.

    Parameters:
        content_id (str, required): The content ID (e.g. "322850").
        content_type_id (str, required): Content type ID — required on this endpoint.
            Korean: "12" tourist attraction, "14" cultural facility, "15" event/festival,
            "28" leisure sports, "32" accommodation, "38" shopping, "39" restaurant, "25" travel course.
            Multilingual: "76" tourist attraction, "78" cultural facility, "85" event/festival,
            "75" leisure sports, "80" accommodation, "79" shopping, "82" restaurant, "77" transport.
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.

    Returns (for contentTypeId 12 or 76 — tourist attraction):
        dict with keys:
            - items (list): Each item includes contentId, contentTypeId, accomcount (capacity),
              chkcreditcard, expagerange, expguide, heritage1, heritage2, heritage3,
              infocenter, opendate, parking, restdate, useseason, usetime.
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().get_wellness_intro_info(
            content_id=content_id,
            content_type_id=content_type_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def get_wellness_repeating_info(
    content_id: str,
    content_type_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    """
    Retrieve repeating structured information for a wellness tourism content item.

    Returns lists of facility details, entrance fees, amenities, accessibility features,
    and reservation guidance. Each record is a named info item with a serial number.

    Parameters:
        content_id (str, required): The content ID (e.g. "1000306").
        content_type_id (str, required): Content type ID — required on this endpoint.
            Korean: "12" tourist attraction, "14" cultural facility, "15" event/festival,
            "28" leisure sports, "32" accommodation, "38" shopping, "39" restaurant.
            Multilingual: "76" tourist attraction, "78" cultural facility, "85" event/festival,
            "75" leisure sports, "80" accommodation, "79" shopping, "82" restaurant.
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.

    Returns:
        dict with keys:
            - items (list): Each item includes contentid (all lowercase), contenttypeid (all lowercase),
              serialnum, infoname, infotext, fldgubun.
              Note: field names "contentid" and "contenttypeid" are all lowercase as returned by the API.
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().get_wellness_repeating_info(
            content_id=content_id,
            content_type_id=content_type_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}


async def get_wellness_images(
    content_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    image_yn: Optional[str] = None,
) -> dict:
    """
    Retrieve all image URLs and copyright types for a specific wellness tourism content item.

    For restaurant-type content (contentTypeId 39/82), can retrieve food menu images instead
    of general content images by setting image_yn to "N".

    Parameters:
        content_id (str, required): The content ID (e.g. "1000306").
        lang_div_cd (str, optional): Language code. Default: "KOR".
            Valid values: "KOR", "ENG", "JPN", "CHS", "CHT", "GER", "FRE", "SPN", "RUS".
        num_of_rows (int, optional): Results per page. Default: 10.
        page_no (int, optional): Page number. Default: 1.
        image_yn (str, optional): Image type.
            "Y" = general content images (default).
            "N" = food menu images (only for restaurant contentTypeId 39/82).

    Returns:
        dict with keys:
            - items (list): Each item includes contentId, imgname, orgImage (~500x333px),
              thumbImage (~150x100px), cpyrhtDivCd ("Type1" or "Type3"), serialnum.
            - totalCount (int), pageNo (int), numOfRows (int).
    """
    try:
        return await get_client().get_wellness_images(
            content_id=content_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            image_yn=image_yn,
        )
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}
