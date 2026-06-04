import re
from pathlib import Path

path = Path('/home/ubuntu/zazasync_repo/restored_home.html')
raw = path.read_bytes()
text = raw.decode('utf-8', errors='replace')
markers = ['productsTracked','snapshot','inventory','dehydrated','__TANSTACK','__ROUTER','__TSR','loaderData','sqdc','stock','brand','categorySummaries','radarPicks']
for marker in markers:
    print(f'=== {marker} count={text.lower().count(marker.lower())} ===')
    locs = [m.start() for m in re.finditer(re.escape(marker), text, flags=re.I)][:12]
    for idx in locs:
        snippet = text[max(0, idx-320):idx+720].replace('\n',' ')
        print(snippet[:1200])
        print('---')

print('=== script tags summary ===')
for i, m in enumerate(re.finditer(r'<script[^>]*>(.*?)</script>', text, flags=re.I|re.S), 1):
    body = m.group(1)
    print(i, len(body), body[:300].replace('\n',' '))
