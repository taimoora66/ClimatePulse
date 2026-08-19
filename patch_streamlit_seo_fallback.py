from pathlib import Path
import re
import streamlit

TITLE = "ORBIDENSE | Climate Risk, Earth Intelligence & Environmental Data"

NOSCRIPT = """<noscript>
  <main style="max-width:900px;margin:48px auto;padding:24px;font-family:Arial,sans-serif;line-height:1.6">
    <h1>ORBIDENSE - Climate Risk, Earth Intelligence & Environmental Data</h1>

    <p>
      ORBIDENSE is an independent climate and Earth intelligence platform
      for exploring environmental conditions, climate trends, emissions,
      population exposure and climate-risk insights using scientific and
      public environmental datasets.
    </p>

    <p>
      Explore environmental research, scientific methodology, climate data,
      Earth observation and evidence-based climate-risk analysis.
    </p>

    <nav aria-label="ORBIDENSE information pages">
      <a href="/about">About ORBIDENSE</a> |
      <a href="/research">Research</a> |
      <a href="/methodology">Methodology</a> |
      <a href="/data">Data &amp; Sources</a>
    </nav>

    <p>
      JavaScript is required to use the full interactive Earth Intelligence platform.
    </p>
  </main>
</noscript>"""


def main():
    streamlit_dir = Path(streamlit.__file__).resolve().parent
    index_path = streamlit_dir / "static" / "index.html"

    if not index_path.exists():
        raise FileNotFoundError(f"Streamlit index.html not found: {index_path}")

    html = index_path.read_text(encoding="utf-8")

    html, title_count = re.subn(
        r"<title>.*?</title>",
        f"<title>{TITLE}</title>",
        html,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    html, noscript_count = re.subn(
        r"<noscript>.*?</noscript>",
        NOSCRIPT,
        html,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if title_count != 1:
        raise RuntimeError(f"Expected one title replacement; got {title_count}")

    if noscript_count != 1:
        raise RuntimeError(f"Expected one noscript replacement; got {noscript_count}")

    index_path.write_text(html, encoding="utf-8")

    print(f"SEO fallback patched: {index_path}")
    print(f"Title: {TITLE}")
    print("Noscript fallback: ORBIDENSE semantic content installed")


if __name__ == "__main__":
    main()