import html
from datetime import UTC, datetime

from bs4 import BeautifulSoup


def parse_date(value: str | int | None) -> datetime | None:
    if value is None:
        return
    if isinstance(value, int):
        dt = datetime.fromtimestamp(value / 1000, tz=UTC)
    else:
        dt = datetime.fromisoformat(value)

    return dt.astimezone(UTC)


def html_to_text(raw: str | None, unescape: bool = False) -> str:
    if raw is None:
        return ""
    if unescape:
        raw = html.unescape(raw)
    return (
        BeautifulSoup(raw, "html.parser")
        .get_text("\n", strip=True)
        .replace("\xa0", " ")
    )
