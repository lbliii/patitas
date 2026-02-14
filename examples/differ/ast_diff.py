"""Structural diff — know exactly what changed between two parses."""

from patitas import diff_documents, parse

old_source = "# Hello\n\nWorld"
new_source = "# Hello\n\nUpdated world"

old_doc = parse(old_source)
new_doc = parse(new_source)

changes = diff_documents(old_doc, new_doc)

print("Changes:")
for change in changes:
    print(f"  {change.kind} at {change.path}")
    if change.old_node is not None:
        print(f"    old: {change.old_node}")  # type: ignore[union-attr]
    if change.new_node is not None:
        print(f"    new: {change.new_node}")  # type: ignore[union-attr]
