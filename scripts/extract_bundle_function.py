from pathlib import Path
import sys

if len(sys.argv) < 3:
    raise SystemExit('usage: extract_bundle_function.py <bundle> <needle>')

bundle = Path(sys.argv[1])
needle = sys.argv[2]
text = bundle.read_text('utf-8', 'replace')
idx = text.find(needle)
print(f'needle={needle!r} index={idx}')
if idx < 0:
    raise SystemExit(1)
start = max(0, idx - 1200)
end = min(len(text), idx + 5000)
snippet = text[start:end]
# Add light line breaks around punctuation to make minified code readable.
for old, new in [(';', ';\n'), ('=>', '=>'), ('},', '},\n'), (',{', ',\n{')]:
    snippet = snippet.replace(old, new)
print(snippet)
