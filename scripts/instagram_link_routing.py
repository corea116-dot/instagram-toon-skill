from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

from instagram_link_models import (
    InstagramLinkError,
    InstagramPostType,
    normalize_instagram_post_url,
)


LinkRouteStatus = Literal["not_requested", "ready", "requires_user_input"]
_URL_TOKEN: Final = re.compile(r"https?://[^\s<>()\[\]{}\"']+")


@dataclass(frozen=True, slots=True)
class InstagramLinkRoute:
    status: LinkRouteStatus
    canonical_url: str | None
    post_type: InstagramPostType | None
    message: str


def _urls_in_request(request_text: str) -> tuple[str, ...]:
    return tuple(match.group(0).rstrip(".,!?;:") for match in _URL_TOKEN.finditer(request_text))


def resolve_instagram_link_route(
    request_text: str, *, explicit_skill_invoked: bool
) -> InstagramLinkRoute:
    """Select the link-analysis route only for an explicit one-link invocation."""
    if not explicit_skill_invoked:
        return InstagramLinkRoute("not_requested", None, None, "")
    urls = _urls_in_request(request_text)
    if not urls:
        return InstagramLinkRoute("not_requested", None, None, "")
    if len(urls) != 1:
        return InstagramLinkRoute(
            "requires_user_input",
            None,
            None,
            "Provide exactly one link: a direct Instagram post or reel link.",
        )
    try:
        normalized = normalize_instagram_post_url(urls[0])
    except InstagramLinkError:
        return InstagramLinkRoute(
            "requires_user_input",
            None,
            None,
            "Provide one direct Instagram post or reel link.",
        )
    return InstagramLinkRoute(
        "ready", normalized.canonical_url, normalized.post_type, ""
    )
