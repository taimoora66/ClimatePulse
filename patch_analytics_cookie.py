from __future__ import annotations
from pathlib import Path
import streamlit

MARKER = "<!-- ORBIDENSE ANALYTICS VISITOR COOKIE V4 -->"
COOKIE_SCRIPT = r"""
<!-- ORBIDENSE ANALYTICS VISITOR COOKIE V4 -->
<script>
(function () {
  try {
    const name = "orbidense_vid";
    const hasCookie = document.cookie.split("; ").some(v => v.startsWith(name + "="));
    if (hasCookie) return;
    const a = new Uint8Array(16);
    crypto.getRandomValues(a);
    a[6] = (a[6] & 0x0f) | 0x40;
    a[8] = (a[8] & 0x3f) | 0x80;
    const hex = [...a].map(b => b.toString(16).padStart(2,"0"));
    const uuid = `${hex.slice(0,4).join("")}-${hex.slice(4,6).join("")}-${hex.slice(6,8).join("")}-${hex.slice(8,10).join("")}-${hex.slice(10).join("")}`;
    const value = "visitor_" + uuid.replaceAll("-", "");
    document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=31536000; Path=/; SameSite=Lax; Secure`;
  } catch (_) {}
})();
</script>
"""

index_path = Path(streamlit.__file__).resolve().parent / "static" / "index.html"
html = index_path.read_text(encoding="utf-8")
if MARKER not in html:
    html = html.replace("</head>", COOKIE_SCRIPT + "\n</head>")
    index_path.write_text(html, encoding="utf-8")
    print(f"Patched ORBIDENSE analytics visitor cookie: {index_path}")
else:
    print("ORBIDENSE analytics visitor cookie already installed.")
