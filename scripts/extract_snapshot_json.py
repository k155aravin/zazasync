import json
import re
from pathlib import Path

SOURCE = Path('restored_inventory.html')
OUT = Path('restored_snapshot.json')
text = SOURCE.read_text(errors='replace')

def extract_assigned_array(label: str):
    marker = f'{label}:$R['
    start_marker = text.find(marker)
    if start_marker < 0:
        raise RuntimeError(f'Marker not found: {marker}')
    array_start = text.find('=[', start_marker)
    if array_start < 0:
        raise RuntimeError(f'Array assignment not found after {marker}')
    array_start += 1
    depth = 0
    in_string = False
    escape = False
    for idx in range(array_start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                raw = text[array_start:idx+1]
                break
    else:
        raise RuntimeError(f'No balanced end found for {label}')

    cleaned = re.sub(r'\$R\[\d+\]=', '', raw)
    cleaned = cleaned.replace(':!0', ':true').replace(':!1', ':false')
    cleaned = re.sub(r'([\{,])([A-Za-z_$][\w$]*):', r'\1"\2":', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        debug = Path(f'debug_{label}.jsonish')
        debug.write_text(cleaned[:200000])
        raise RuntimeError(f'Failed parsing {label}: {exc}; wrote {debug}') from exc

stores = extract_assigned_array('stores')
products = extract_assigned_array('products')
last_updated = None
for product in products:
    last_updated = max([x for x in [last_updated, product.get('lastSeenAt')] if x]) if last_updated or product.get('lastSeenAt') else None

snapshot = {
    'source': 'https://zazasync.com/inventory restored production route data',
    'extractedAt': __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    'lastUpdatedAt': last_updated,
    'stores': stores,
    'products': products,
}
OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
print(json.dumps({
    'stores': len(stores),
    'products': len(products),
    'availabilityRows': sum(len(p.get('availability') or []) for p in products),
    'lastUpdatedAt': last_updated,
}, indent=2))
