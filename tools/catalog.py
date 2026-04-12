from typing import Optional

from api import WellnessAPIError, WellnessClient

_client: Optional[WellnessClient] = None


def _get_client() -> WellnessClient:
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
    Retrieve legal administrative district (법정동) codes for filtering wellness
    tourism queries by region.

    Returns province/city codes (시도) and district codes (시군구). Use these codes
    as input to other tools that accept lDongRegnCd / lDongSignguCd parameters.

    Parameters:
        lang_div_cd: Language code. Default "KOR".
            Values: "KOR","ENG","JPN","CHS","CHT","GER","FRE","SPN","RUS".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        l_dong_regn_cd: Province/city code filter (e.g. "11" for Seoul).
            When omitted, all province/city codes are returned.
        l_dong_list_yn: "N" = return 시도/시군구 codes (default);
            "Y" = return full 법정동 list with both province and district fields.

    Returns dict with items list, totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().get_legal_district_codes(
            lang_div_cd=lang_div_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_list_yn=l_dong_list_yn,
        )
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
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
    Retrieve the wellness tourism synchronisation list for applications that
    maintain a local dataset copy.

    Designed for delta sync use cases. Filter by showflag or old_content_id
    to retrieve only updated records.

    Parameters:
        lang_div_cd: Language code. Default "KOR".
        num_of_rows: Results per page. Default 10.
        page_no: Page number. Default 1.
        arrange: Sort order "A"/"C"/"D"/"O"/"Q"/"R".
        content_type_id: Tourism category filter (same codes as search_wellness_by_area).
        showflag: Display status. "1" = publicly visible, "0" = hidden.
        mdfcn_dt: Modified date filter in YYMMDD format.
        l_dong_regn_cd: Province/city code filter.
        l_dong_signgu_cd: District code filter. Requires l_dong_regn_cd.
        old_content_id: Previous content ID for delta sync queries.
        wellness_thema_cd: Wellness theme — "EX050100" through "EX050700".

    Returns dict with items (same as search_wellness_by_area plus "showflag"
    and "oldContentId"), totalCount, pageNo, numOfRows.
    """
    try:
        return await _get_client().get_wellness_sync_list(
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
    except ValueError as e:
        return {"error": True, "code": "INVALID_PARAM", "message": str(e)}
    except WellnessAPIError as e:
        return {"error": True, "code": e.code, "message": e.message}
