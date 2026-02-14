"""Re-parse only what changed — O(change) not O(document)."""

from patitas import parse, parse_incremental

original = "# Title\n\nFirst para.\n\nSecond para."
doc = parse(original)

# User edits "First para." → "First paragraph."
edit_start = len("# Title\n\n")
edit_end = len("# Title\n\nFirst para.")
new_source = "# Title\n\nFirst paragraph.\n\nSecond para."
new_length = len("First paragraph.")

new_doc = parse_incremental(new_source, doc, edit_start, edit_end, new_length)

print("Original document blocks:", len(doc.children))
print("New document blocks:", len(new_doc.children))
print()
print("Second paragraph unchanged (same object?):", doc.children[2] is new_doc.children[2])
print("First paragraph changed:", doc.children[1] is not new_doc.children[1])
