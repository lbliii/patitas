"""Free-threading safe — parse 1000 docs in parallel."""

from concurrent.futures import ThreadPoolExecutor

from patitas import parse

docs = ["# Doc " + str(i) + "\n\nContent for document " + str(i) for i in range(1000)]

with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(parse, docs))

print(f"Parsed {len(results)} documents in parallel")
print("First doc children:", len(results[0].children))
print("Last doc children:", len(results[-1].children))
