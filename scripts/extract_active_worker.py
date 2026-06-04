from email.parser import BytesParser
from email.policy import default
from pathlib import Path

raw = Path('active_worker_download.bin').read_bytes()
first = raw.split(b'\r\n', 1)[0].decode('utf-8')
boundary = first[2:] if first.startswith('--') else first
message = b'Content-Type: multipart/form-data; boundary=' + boundary.encode() + b'\r\n\r\n' + raw
msg = BytesParser(policy=default).parsebytes(message)
for part in msg.iter_parts():
    name = part.get_param('name', header='content-disposition')
    filename = part.get_filename()
    payload = part.get_payload(decode=True) or b''
    safe = filename or f'{name}.txt'
    out = Path('active_worker_parts') / safe
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(payload)
    print(name, filename, len(payload), out)
