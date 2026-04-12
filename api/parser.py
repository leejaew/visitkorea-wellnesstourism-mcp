import json
import xml.etree.ElementTree as ET


class WellnessAPIError(Exception):
    """Raised when the upstream KTO API returns a non-success response."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def parse_response(raw: str) -> dict:
    """Parse a raw API response string (JSON or XML) into a normalised body dict.

    Raises WellnessAPIError on any non-success result code or parse failure.
    """
    raw = raw.strip()

    # ── Try JSON first ────────────────────────────────────────────────────────
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

    # ── Fall back to XML ──────────────────────────────────────────────────────
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise WellnessAPIError("PARSE_ERROR", f"Failed to parse API response: {e}")

    # data.go.kr portal-level error envelope
    if root.tag == "OpenAPI_ServiceResponse":
        header_el = root.find("cmmMsgHeader")
        if header_el is not None:
            err_msg = header_el.findtext("errMsg", "UNKNOWN")
            auth_msg = header_el.findtext("returnAuthMsg", "UNKNOWN")
            reason = header_el.findtext("returnReasonCode", "99")
            raise WellnessAPIError(reason, f"{err_msg}: {auth_msg}")
        raise WellnessAPIError("99", "Unknown portal error")

    # Standard XML envelope
    header_el = root.find(".//header")
    if header_el is not None:
        result_code = header_el.findtext("resultCode", "")
        result_msg = header_el.findtext("resultMsg", "UNKNOWN")
        if result_code not in ("0000", "00"):
            raise WellnessAPIError(result_code, result_msg)

    body_el = root.find(".//body")
    if body_el is None:
        raise WellnessAPIError("PARSE_ERROR", "No body element in API response")

    items = []
    items_el = body_el.find("items")
    if items_el is not None:
        items = [{child.tag: child.text for child in item_el}
                 for item_el in items_el.findall("item")]

    return {
        "items": {"item": items},
        "numOfRows": int(body_el.findtext("numOfRows", "0") or "0"),
        "pageNo":    int(body_el.findtext("pageNo",    "1") or "1"),
        "totalCount": int(body_el.findtext("totalCount", "0") or "0"),
    }


def extract_items(body: dict) -> list:
    """Normalise the items wrapper from the API body into a plain list."""
    items_wrapper = body.get("items", {})
    if not items_wrapper:
        return []
    items = items_wrapper.get("item", [])
    if isinstance(items, dict):
        return [items]
    return items or []
