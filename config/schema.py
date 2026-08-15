"""
drf-spectacular preprocessing hook.
Maps URL path prefixes -> our predefined tag names so Swagger
shows only one clean tag group per section.
"""


# URL prefix  ->  Swagger tag name
URL_TAG_MAP = [
    ("/api/auth/",           "Auth"),
    ("/api/clients/",        "Clients"),
    ("/api/quotes/",         "Quotes"),
    ("/api/invoices/",       "Invoices"),
    ("/api/payments/",       "Payments"),
    ("/api/receipts/",       "Receipts"),
    ("/api/settings/",       "Settings"),
    ("/api/reports/",        "Reports"),
    ("/api/profile/",        "Profile"),
    ("/api/health/",         "Health"),
    ("/api/",                "API"),
]


def assign_tags(endpoints, **kwargs):
    """
    Preprocessing hook: replaces auto-generated tags on every endpoint
    with our canonical capitalized tag name based on the URL path.
    """
    result = []

    for (path, path_regex, method, callback) in endpoints:
        tag = "API"
        for prefix, tag_name in URL_TAG_MAP:
            if path.startswith(prefix):
                tag = tag_name
                break

        if hasattr(callback, "cls"):
            callback.cls.swagger_tags = [tag]
        elif hasattr(callback, "initkwargs"):
            callback.initkwargs["swagger_tags"] = [tag]

        if hasattr(callback, "kwargs"):
            callback.kwargs["tags"] = [tag]

        result.append((path, path_regex, method, callback))

    return result
