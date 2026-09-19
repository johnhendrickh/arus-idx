"""alert.py — format pesan + kirim Telegram. Tidak ada aksi trading apa pun."""
import pandas as pd, requests, os
BOT = os.getenv('ARUS_BOT_TOKEN', '')
CHAT = os.getenv('ARUS_CHAT_ID', '')

def format_alert(rows, regime_up):
    lines = [f"ARUS — {pd.Timestamp.now():%d %b %H:%M} WIB",
             f"IHSG regime: {'▲ UP' if regime_up else '▼ DOWN — mode tunggu, jangan entry'}", '']
    for t, v, st in rows[:5]:
        if st.startswith('SKIP'): continue
        lines.append(f'{t.replace(".JK","")}  {v:.2f}  {st}')
    lines += ['', 'Skor = momentum 55% + fundamental 45% (kolom flow = informasi). Bukan rekomendasi beli/jual.']
    return '\n'.join(lines)

def send(msg):
    if not BOT or not CHAT: return False
    r = requests.post(f'https://api.telegram.org/bot{BOT}/sendMessage',
                      json={'chat_id': CHAT, 'text': msg}, timeout=15)
    return r.status_code == 200

import pandas as pd  # noqa: E402 (dipakai format_alert)
