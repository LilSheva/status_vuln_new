"""Template for preprocessing plugin scripts.

Each plugin must implement a `process()` function with the following signature:

    def process(entries: list[dict]) -> list[dict]

Each entry dict has the following keys:
    - vendor: str    — vendor name (e.g. "Microsoft")
    - product: str   — product name (e.g. "Windows 10 Pro")
    - version: str   — version string (e.g. "10.0.19045")
    - raw_text: str  — original concatenated text from TSU

The function may:
    - Modify entries in place (e.g. clean product names)
    - Return fewer entries (filtering)
    - Return more entries (splitting multi-product rows)

IMPORTANT:
    - Always return a list of dicts with the same keys.
    - Never raise exceptions — handle errors gracefully.
    - Use logging instead of print().
"""


def process(entries: list[dict]) -> list[dict]:
    """Process vulnerability entries.

    Args:
        entries: List of entry dicts to process.

    Returns:
        Processed list of entry dicts.
    """
    # Your processing logic here
    return entries
