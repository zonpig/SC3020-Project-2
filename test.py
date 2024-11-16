import re
from collections import defaultdict


def combine_hints(hints):
    """
    Combines join hints in a PostgreSQL hint comment.

    Args:
        hints (str): The input hint comment, e.g.,
                     "/*+ SeqScan(part) SeqScan(supplier) SeqScan(partsupp) HashJoin(ps p) HashJoin(ps s) */"

    Returns:
        str: The combined hint comment with join hints merged.
    """
    # Remove the comment delimiters
    hints = hints.strip("/*+ ").strip(" */")

    # Split the hints into parts
    hint_parts = hints.split()

    # Separate scan hints and join hints
    scan_hints = []
    join_hints = defaultdict(set)  # Using a set to avoid duplicate operands

    for hint in hint_parts:
        # Match the format of each hint, e.g., SeqScan(part) or HashJoin(ps p)
        match = re.match(r"(\w+)\(([^)]+)\)", hint)
        if match:
            hint_type, hint_content = match.groups()
            if hint_type in {"SeqScan", "IndexScan"}:
                # Collect scan hints as they are
                scan_hints.append(hint)
            else:
                # Split and add join hint operands to the corresponding set
                join_hints[hint_type].update(hint_content.split())

    # Reconstruct the combined hints
    combined_hints = scan_hints
    for hint_type, operands in join_hints.items():
        combined_hints.append(f"{hint_type}({' '.join(sorted(operands))})")

    # Rebuild the comment
    return f"/*+ {' '.join(combined_hints)} */"


# Example usage
hints = "/*+ SeqScan(part) SeqScan(supplier) SeqScan(partsupp) HashJoin(ps p) HashJoin(ps s) */"
combined_hints = combine_hints(hints)
print(combined_hints)
