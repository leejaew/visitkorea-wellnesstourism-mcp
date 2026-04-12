import sys
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import TransportSecuritySettings

from tools import (
    get_legal_district_codes,
    get_wellness_common_info,
    get_wellness_images,
    get_wellness_intro_info,
    get_wellness_repeating_info,
    get_wellness_sync_list,
    search_wellness_by_area,
    search_wellness_by_keyword,
    search_wellness_by_location,
)

if not os.environ.get("WELLNESS_API_KEY_ENCODING"):
    print(
        "ERROR: WELLNESS_API_KEY_ENCODING environment variable is not set.\n"
        "Please configure this Replit Secret before starting the server.\n"
        "Obtain your API key from https://www.data.go.kr/data/15144030/openapi.do",
        file=sys.stderr,
    )
    sys.exit(1)

# DNS-rebinding protection defaults to localhost-only in MCP SDK 1.x.
# This server is a public MCP endpoint behind Replit's TLS proxy, so we
# disable the restriction so external agents (Manus AI, Claude, etc.) can
# connect via the .replit.app domain without receiving HTTP 421.
mcp = FastMCP(
    "visitkorea-wellnesstourism",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.tool(name="get_legal_district_codes")
async def _get_legal_district_codes(
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    l_dong_regn_cd: str = "",
    l_dong_list_yn: str = "",
) -> dict:
    """
    Retrieve legal administrative district (법정동) codes for filtering wellness tourism queries by region.

    Returns province/city codes (시도) and district codes (시군구). Use these codes as input
    to other tools that accept lDongRegnCd / lDongSignguCd parameters.

    Parameters:
        lang_div_cd: Language code. Default "KOR". Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        l_dong_regn_cd: Province/city code filter (e.g. "11" for Seoul). Leave empty for all provinces.
        l_dong_list_yn: "N" = return 시도/시군구 codes (default); "Y" = return full 법정동 list.

    Returns dict with items list, totalCount, pageNo, numOfRows.
    """
    return await get_legal_district_codes(
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
        l_dong_regn_cd=l_dong_regn_cd or None,
        l_dong_list_yn=l_dong_list_yn or None,
    )


@mcp.tool(name="search_wellness_by_area")
async def _search_wellness_by_area(
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    arrange: str = "",
    content_type_id: str = "",
    mdfcn_dt: str = "",
    l_dong_regn_cd: str = "",
    l_dong_signgu_cd: str = "",
    wellness_thema_cd: str = "",
) -> dict:
    """
    List wellness tourism spots filtered by administrative region, content type, wellness theme, and sort order.

    Parameters:
        lang_div_cd: Language code. Default "KOR". Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order. "A"=title, "C"=modified date, "D"=created date (no image needed);
            "O","Q","R" = same but image required.
        content_type_id: Korean: 12=tourist attraction,14=cultural,15=event,28=leisure,32=accommodation,38=shopping,39=restaurant,25=travel course.
            Multilingual: 76=tourist,78=cultural,85=event,75=leisure,80=accommodation,79=shopping,82=restaurant,77=transport.
        mdfcn_dt: Modified date filter in YYMMDD format.
        l_dong_regn_cd: Province/city code (e.g. "11" Seoul).
        l_dong_signgu_cd: District code (requires l_dong_regn_cd).
        wellness_thema_cd: Wellness theme. "EX050100"=Hot spring/Sauna/Spa, "EX050200"=Jjimjilbang,
            "EX050300"=Korean traditional medicine, "EX050400"=Healing meditation,
            "EX050500"=Beauty spa, "EX050600"=Other wellness, "EX050700"=Nature healing.

    Returns dict with items (contentId, title, baseAddr, mapX, mapY, tel, orgImage, wellnessThemaCd, etc.), totalCount, pageNo, numOfRows.
    """
    return await search_wellness_by_area(
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
        arrange=arrange or None,
        content_type_id=content_type_id or None,
        mdfcn_dt=mdfcn_dt or None,
        l_dong_regn_cd=l_dong_regn_cd or None,
        l_dong_signgu_cd=l_dong_signgu_cd or None,
        wellness_thema_cd=wellness_thema_cd or None,
    )


@mcp.tool(name="search_wellness_by_location")
async def _search_wellness_by_location(
    map_x: float,
    map_y: float,
    radius: int,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    arrange: str = "",
    content_type_id: str = "",
    mdfcn_dt: str = "",
    l_dong_regn_cd: str = "",
    l_dong_signgu_cd: str = "",
    wellness_thema_cd: str = "",
) -> dict:
    """
    List wellness tourism spots within a radius of GPS coordinates (WGS84). Maximum radius: 20000 metres (20 km).

    Parameters:
        map_x: GPS longitude in WGS84 (e.g. 126.981611 for central Seoul). REQUIRED.
        map_y: GPS latitude in WGS84 (e.g. 37.568477 for central Seoul). REQUIRED.
        radius: Search radius in metres. Maximum: 20000. REQUIRED.
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order. "E"=distance nearest first (no image), "S"=distance (image required).
            Also accepts "A","C","D","O","Q","R" — same as search_wellness_by_area.
        content_type_id: Tourism category filter (same codes as search_wellness_by_area).
        mdfcn_dt: Modified date filter in YYMMDD format.
        l_dong_regn_cd: Province/city code filter.
        l_dong_signgu_cd: District code filter.
        wellness_thema_cd: Wellness theme — same values as search_wellness_by_area.

    Returns dict with items (same as search_wellness_by_area plus "dist" field in metres), totalCount, pageNo, numOfRows.
    """
    return await search_wellness_by_location(
        map_x=map_x,
        map_y=map_y,
        radius=radius,
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
        arrange=arrange or None,
        content_type_id=content_type_id or None,
        mdfcn_dt=mdfcn_dt or None,
        l_dong_regn_cd=l_dong_regn_cd or None,
        l_dong_signgu_cd=l_dong_signgu_cd or None,
        wellness_thema_cd=wellness_thema_cd or None,
    )


@mcp.tool(name="search_wellness_by_keyword")
async def _search_wellness_by_keyword(
    keyword: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    arrange: str = "",
    content_type_id: str = "",
    l_dong_regn_cd: str = "",
    l_dong_signgu_cd: str = "",
    wellness_thema_cd: str = "",
) -> dict:
    """
    Full-text keyword search across all wellness tourism content.

    Parameters:
        keyword: Search keyword. Can be Korean (e.g. "스파") or English (e.g. "spa"). Auto URL-encoded. REQUIRED.
        lang_div_cd: Language code. Default "KOR". Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order "A","C","D","O","Q","R".
        content_type_id: Tourism category filter (same codes as search_wellness_by_area).
        l_dong_regn_cd: Province/city code filter.
        l_dong_signgu_cd: District code filter (requires l_dong_regn_cd).
        wellness_thema_cd: Wellness theme filter — same values as search_wellness_by_area.

    Returns dict with items (same fields as search_wellness_by_area), totalCount, pageNo, numOfRows.
    """
    return await search_wellness_by_keyword(
        keyword=keyword,
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
        arrange=arrange or None,
        content_type_id=content_type_id or None,
        l_dong_regn_cd=l_dong_regn_cd or None,
        l_dong_signgu_cd=l_dong_signgu_cd or None,
        wellness_thema_cd=wellness_thema_cd or None,
    )


@mcp.tool(name="get_wellness_sync_list")
async def _get_wellness_sync_list(
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    arrange: str = "",
    content_type_id: str = "",
    showflag: str = "",
    mdfcn_dt: str = "",
    l_dong_regn_cd: str = "",
    l_dong_signgu_cd: str = "",
    old_content_id: str = "",
    wellness_thema_cd: str = "",
) -> dict:
    """
    Retrieve the wellness tourism synchronisation list for applications maintaining a local dataset copy.

    Designed for delta sync — filter by showflag or old_content_id to retrieve updated records.

    Parameters:
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order "A","C","D","O","Q","R".
        content_type_id: Tourism category filter.
        showflag: Display status. "1" = publicly visible, "0" = hidden.
        mdfcn_dt: Modified date filter in YYMMDD format.
        l_dong_regn_cd: Province/city code filter.
        l_dong_signgu_cd: District code filter.
        old_content_id: Previous content ID for delta sync.
        wellness_thema_cd: Wellness theme — "EX050100" through "EX050700".

    Returns dict with items (same as search_wellness_by_area plus "showflag" and "oldContentId"),
    totalCount, pageNo, numOfRows.
    """
    return await get_wellness_sync_list(
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
        arrange=arrange or None,
        content_type_id=content_type_id or None,
        showflag=showflag or None,
        mdfcn_dt=mdfcn_dt or None,
        l_dong_regn_cd=l_dong_regn_cd or None,
        l_dong_signgu_cd=l_dong_signgu_cd or None,
        old_content_id=old_content_id or None,
        wellness_thema_cd=wellness_thema_cd or None,
    )


@mcp.tool(name="get_wellness_common_info")
async def _get_wellness_common_info(
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
        content_id: The content ID to retrieve (e.g. "702551"). REQUIRED.
        lang_div_cd: Language code. Default "KOR". Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.

    Returns dict with items containing contentId, contentTypeId, title, homepage (may contain HTML),
    baseAddr, detailAddr, zipCd, mapX, mapY, mlevel, tel, telname, overview, orgImage, thumbImage,
    cpyrhtDivCd, regDt, mdfcnDt, lDongRegnCd, lDongSignguCd, wellnessThemaCd.
    Plus totalCount, pageNo, numOfRows.
    """
    return await get_wellness_common_info(
        content_id=content_id,
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
    )


@mcp.tool(name="get_wellness_intro_info")
async def _get_wellness_intro_info(
    content_id: str,
    content_type_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    """
    Retrieve type-specific introductory details for a wellness tourism content item.

    IMPORTANT: Response fields vary by content_type_id. Fields below apply to
    contentTypeId 12 or 76 (tourist attraction — primary wellness category).
    Other types (accommodation 32/80, restaurant 39/82, etc.) return different fields.

    Parameters:
        content_id: The content ID (e.g. "322850"). REQUIRED.
        content_type_id: Content type ID — REQUIRED on this endpoint.
            Korean: "12"=tourist, "14"=cultural, "15"=event, "28"=leisure,
            "32"=accommodation, "38"=shopping, "39"=restaurant.
            Multilingual: "76"=tourist, "78"=cultural, "85"=event, "75"=leisure,
            "80"=accommodation, "79"=shopping, "82"=restaurant.
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.

    Returns (for contentTypeId 12/76): dict with items containing contentId, contentTypeId,
    accomcount, chkcreditcard, expagerange, expguide, heritage1, heritage2, heritage3,
    infocenter, opendate, parking, restdate, useseason, usetime. Plus totalCount, pageNo, numOfRows.
    """
    return await get_wellness_intro_info(
        content_id=content_id,
        content_type_id=content_type_id,
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
    )


@mcp.tool(name="get_wellness_repeating_info")
async def _get_wellness_repeating_info(
    content_id: str,
    content_type_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    """
    Retrieve repeating structured information for a wellness tourism content item.

    Returns facility details, entrance fees, amenities, accessibility, and reservation guidance.
    Each record is a named info item with a serial number.

    Parameters:
        content_id: The content ID (e.g. "1000306"). REQUIRED.
        content_type_id: Content type ID — REQUIRED on this endpoint.
            Korean: "12"=tourist, "14"=cultural, "15"=event, "28"=leisure, "32"=accommodation, "39"=restaurant.
            Multilingual: "76"=tourist, "78"=cultural, "85"=event, "75"=leisure, "80"=accommodation, "82"=restaurant.
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.

    Returns dict with items. Note: API returns "contentid" and "contenttypeid" (all lowercase).
    Each item also has serialnum, infoname, infotext, fldgubun. Plus totalCount, pageNo, numOfRows.
    """
    return await get_wellness_repeating_info(
        content_id=content_id,
        content_type_id=content_type_id,
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
    )


@mcp.tool(name="get_wellness_images")
async def _get_wellness_images(
    content_id: str,
    lang_div_cd: str = "KOR",
    num_of_rows: int = 10,
    page_no: int = 1,
    image_yn: str = "Y",
) -> dict:
    """
    Retrieve all image URLs and copyright types for a specific wellness tourism content item.

    Parameters:
        content_id: The content ID (e.g. "1000306"). REQUIRED.
        lang_div_cd: Language code. Default "KOR". Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        image_yn: "Y" = general content images (default). "N" = food menu images (restaurant 39/82 only).

    Returns dict with items containing contentId, imgname, orgImage (~500x333px),
    thumbImage (~150x100px), cpyrhtDivCd ("Type1" or "Type3"), serialnum.
    Plus totalCount, pageNo, numOfRows.
    """
    return await get_wellness_images(
        content_id=content_id,
        lang_div_cd=lang_div_cd,
        num_of_rows=num_of_rows,
        page_no=page_no,
        image_yn=image_yn or None,
    )
