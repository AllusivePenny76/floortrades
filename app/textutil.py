"""Shared text cleanup for feed data."""
import re
import html

_TAG_RE = re.compile(r"<[^>]*>?")


def clean_text(s):
    """Collapse whitespace and strip HTML markup/entities.

    Feed asset descriptions sometimes carry entity-escaped names
    ('JPMorgan Chase &amp; Co', occasionally double-encoded) and the Senate
    archive has raw, often truncated HTML fragments like
    'Revenue Bond &lt;div cla'. Unescape entities first so escaped markup
    becomes visible to the tag regex, which also removes unterminated
    trailing fragments.
    """
    if not s:
        return s
    for _ in range(3):  # some rows are double-encoded ('&amp;amp;')
        prev = s
        s = html.unescape(s)
        if s == prev:
            break
    s = _TAG_RE.sub(" ", s)
    return " ".join(s.split())
