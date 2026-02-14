"""Cache parsed AST to disk — JSON round-trip."""

from patitas import parse
from patitas.serialization import from_json, to_json

doc = parse("# Cached document\n\nThis AST can be serialized and restored.")

json_str = to_json(doc)
restored = from_json(json_str)

print("Original == restored:", doc == restored)
print("JSON length:", len(json_str), "chars")
