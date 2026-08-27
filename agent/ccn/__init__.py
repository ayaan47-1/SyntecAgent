"""CCN naming validator — vocabulary/data parsing (Step 1).

Only the parser and its parse report live here. Validation *rules* are a
separate, later task and must not be added to this subpackage yet.
"""

from agent.ccn.parse import (
    Entry,
    ParseResult,
    Vocabulary,
    format_report,
    parse_workbook,
)

__all__ = [
    "Entry",
    "ParseResult",
    "Vocabulary",
    "format_report",
    "parse_workbook",
]
