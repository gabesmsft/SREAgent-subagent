def main(status_code: int, url: str = "", latency_ms: float = 0.0) -> dict:
    """Parse an HTTP status code into structured facts.

    Takes the status_code returned by a health check (e.g. the MCP
    http_health_check tool) and returns its class, canonical reason phrase,
    which side owns the failure, and whether a retry is likely to help.
    Purely mechanical - no judgement, no network calls.
    """
    REASONS = {
        200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
        301: "Moved Permanently", 302: "Found", 304: "Not Modified",
        307: "Temporary Redirect", 308: "Permanent Redirect",
        400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
        404: "Not Found", 405: "Method Not Allowed", 408: "Request Timeout",
        409: "Conflict", 410: "Gone", 418: "I'm a teapot",
        429: "Too Many Requests", 431: "Request Header Fields Too Large",
        500: "Internal Server Error", 501: "Not Implemented",
        502: "Bad Gateway", 503: "Service Unavailable",
        504: "Gateway Timeout", 507: "Insufficient Storage",
    }

    CLASSES = {
        1: ("1xx", "Informational", "Request received, processing continues."),
        2: ("2xx", "Success", "Request was received, understood, and accepted."),
        3: ("3xx", "Redirection", "Further action is needed to complete the request."),
        4: ("4xx", "Client Error", "The request itself is faulty or not permitted."),
        5: ("5xx", "Server Error", "The server failed to fulfil a valid request."),
    }

    # Retry is only meaningful for transient conditions.
    RETRYABLE = {408, 425, 429, 500, 502, 503, 504, 507, 509, 598, 599}

    if not isinstance(status_code, int) or not 100 <= status_code <= 599:
        return {
            "status_code": status_code,
            "valid": False,
            "error": "status_code must be an integer between 100 and 599.",
        }

    family = status_code // 100
    class_label, class_name, class_meaning = CLASSES[family]
    healthy = family in (2, 3)

    if family in (1, 2, 3):
        owner = "none"
    elif family == 4:
        owner = "client"
    else:
        owner = "server"

    result = {
        "status_code": status_code,
        "valid": True,
        "reason_phrase": REASONS.get(status_code, "Unassigned or non-standard"),
        "well_known": status_code in REASONS,
        "status_class": class_label,
        "class_name": class_name,
        "class_meaning": class_meaning,
        "healthy": healthy,
        "failure_owner": owner,
        "retryable": status_code in RETRYABLE,
        "summary": f"{status_code} {REASONS.get(status_code, 'Unassigned')} "
                   f"({class_name}) - {'healthy' if healthy else 'not healthy'}",
    }

    if url:
        result["url"] = url
    if latency_ms:
        result["latency_ms"] = round(float(latency_ms), 1)
        result["latency_band"] = (
            "fast" if latency_ms < 300
            else "acceptable" if latency_ms < 1000
            else "slow" if latency_ms < 3000
            else "very slow"
        )

    return result
