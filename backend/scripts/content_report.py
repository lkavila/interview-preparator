"""Print a per-course summary of lessons, test questions, and exercise types."""
import glob
import json

for f in sorted(glob.glob("seeds/courses/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    types: dict[str, int] = {}
    for lesson in d["lessons"]:
        for ex in lesson["exercises"]:
            types[ex["type"]] = types.get(ex["type"], 0) + 1
    print(f"{d['slug']:28} lessons={len(d['lessons']):3} test={len(d['test']):3} {types}")
