from pathlib import Path
from html import escape

import streamlit


TITLE = "ORBIDENSE | Earth Intelligence"

DESCRIPTION = (
    "Explore climate outlooks, population exposure, emissions and "
    "environmental intelligence for evidence-based decisions."
)

SITE_URL = "https://orbidense.com/"

IMAGE_URL = (
    "https://orbidense.com/app/static/"
    "orbidense_social_preview.png"
)


streamlit_root = Path(streamlit.__file__).resolve().parent
index_path = streamlit_root / "static" / "index.html"

html = index_path.read_text(encoding="utf-8")

title = escape(TITLE, quote=True)
description = escape(DESCRIPTION, quote=True)
site_url = escape(SITE_URL, quote=True)
image_url = escape(IMAGE_URL, quote=True)

marker = "<!-- ORBIDENSE SOCIAL META -->"

metadata = f"""
{marker}
<meta name="description" content="{description}" />
<link rel="canonical" href="{site_url}" />

<meta property="og:title" content="{title}" />
<meta property="og:description" content="{description}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{site_url}" />
<meta property="og:image" content="{image_url}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{description}" />
<meta name="twitter:image" content="{image_url}" />
"""

if marker not in html:
    html = html.replace("</head>", f"{metadata}\n</head>")

html = html.replace(
    "<title>Streamlit</title>",
    f"<title>{title}</title>",
)

index_path.write_text(html, encoding="utf-8")

print(f"Patched Streamlit HTML: {index_path}")
