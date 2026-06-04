from pathlib import Path

text = Path('restored_inventory.html').read_text(errors='replace')
for needle in ['products:$R[', 'stores:$R[', 'stats:$R[', 'matches:$R[', 'newestProducts:$R[']:
    print('\n===', needle, '===')
    i = text.find(needle)
    print('index', i)
    if i >= 0:
        print(text[max(0, i - 300): i + 1200])
