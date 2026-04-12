from typing import Optional

from api import WellnessAPIError, WellnessClient

_client: Optional[WellnessClient] = None


def _get_client() -> WellnessClient:
    global _client
    if _client is None:
        _client = WellnessClient()
    return _client


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
        content_id: The content ID to retrieve (e.g. "702551"). REQUIRED.
        lang_div_cd: Language code. Default "KOR".
            Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.

    Returns dict with items (contentId, contentTypeId, title, homepage, baseAddr,
    detailAddr, zipCd, mapX, mapY, mlevel, tel, telname, overview, orgImage,
    thumbImage, cpyrhtDivCd, regDt, mdfcnDt, lDongRegnCd, lDongSignguCd,
    wellnessThemaCd). Note: "homepage" may contain raw HTML anchor tags.
    Plus totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().get_wellness_common_info(
            content_id=content_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
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

    Parameters:
        content_id: The content ID (e.g. "322850"). REQUIRED.
        content_type_id: Content type ID — REQUIRED.
            Korean: "12"=tourist,"14"=cultural,"15"=event,"28"=leisure,
                    "32"=accommodation,"38"=shopping,"39"=restaurant,"25"=travel course.
            Multilingual: "76"=tourist,"78"=cultural,"85"=event,"75"=leisure,
                          "80"=accommodation,"79"=shopping,"82"=restaurant,"77"=transport.
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.

    Returns (for contentTypeId 12/76) dict with items (contentId, contentTypeId,
    accomcount, chkcreditcard, expagerange, expguide, heritage1/2/3, infocenter,
    opendate, parking, restdate, useseason, usetime). Plus totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().get_wellness_intro_info(
            content_id=content_id,
            content_type_id=content_type_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
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

    Returns facility details, entrance fees, amenities, accessibility features,
    and reservation guidance. Each record is a named info item with a serial number.

    Parameters:
        content_id: The content ID (e.g. "1000306"). REQUIRED.
        content_type_id: Content type ID — REQUIRED (same codes as get_wellness_intro_info).
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.

    Returns dict with items (contentid, contenttypeid — both lowercase as returned
    by the API — serialnum, infoname, infotext, fldgubun). Plus totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().get_wellness_repeating_info(
            content_id=content_id,
            content_type_id=content_type_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
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

    Parameters:
        content_id: The content ID (e.g. "1000306"). REQUIRED.
        lang_div_cd: Language code. Default "KOR".
            Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        image_yn: "Y" = general content images (default).
            "N" = food menu images (restaurant contentTypeId 39/82 only).

    Returns dict with items (contentId, imgname, orgImage ~500x333px,
    thumbImage ~150x100px, cpyrhtDivCd "Type1"/"Type3", serialnum).
    Plus totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().get_wellness_images(
            content_id=content_id,
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            image_yn=image_yn,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}
