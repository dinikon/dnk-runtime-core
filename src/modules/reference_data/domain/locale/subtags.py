import re


def parse_locale_subtags(code: str) -> tuple[str, str | None, str | None]:
    """Extract language, script and region from a normalized CLDR locale code."""
    if not re.fullmatch(r"[a-z]{2,8}(?:-[A-Za-z0-9]{2,8})*", code):
        raise ValueError(f"Invalid locale code: {code}")
    language, *subtags = code.split("-")
    script = next(
        (part for part in subtags if re.fullmatch(r"[A-Z][a-z]{3}", part)),
        None,
    )
    region = next(
        (part for part in subtags if re.fullmatch(r"[A-Z]{2}|[0-9]{3}", part)),
        None,
    )
    return language, script, region
