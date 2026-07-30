"""!forecast — check the short-term weather forecast for Ottawa (YOW)."""

import urllib.request
import asyncio
import re
from ottobot import Context, command

# URL for Environment Canada's forecast for Ottawa
URL = "https://weather.gc.ca/en/location/index.html?coords=45.403,-75.687"


def summarize_forecast_text(text: str) -> str:
    """Compresses a detailed forecast block into a concise sentence + High/Low."""
    # Strip leading temperature prefixes if present (e.g. "18° C.")
    clean = re.sub(r"^-?\d+°?\sC\.?\s", "", text).strip()

    # Abbreviate common long phrases to save space on mesh
    clean = clean.replace("percent chance", "% chance")

    # Extract just the first core sentence
    sentences = [s.strip() for s in clean.split(".") if s.strip()]
    if not sentences:
        return clean

    first_sentence = sentences[0]

    # Grab the High or Low temperature from anywhere in the text block
    temp_match = re.search(r"\b(High|Low)\s+(-?\d+)", clean, re.IGNORECASE)
    if temp_match and temp_match.group(0).lower() not in first_sentence.lower():
        return f"{first_sentence}. {temp_match.group(1)} {temp_match.group(2)}"

    return first_sentence


def fetch_forecast_datamart() -> str:
    """Fetches and summarizes a 2-period forecast from the EC location page."""
    req = urllib.request.Request(
        URL, headers={"User-Agent": "Mozilla/5.0 (Ottobot Mesh Node)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")

        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        text = text.replace("&deg;", "°")

        # Focus strictly on the "Detailed Forecast" block at the bottom of the page
        if "Detailed Forecast" in text:
            target_text = text.split("Detailed Forecast")[-1]
        else:
            target_text = text

        header_pattern = re.compile(
            r"\b(Today|Tonight|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:\s*,\s*\d+\s*[A-Za-z]+)?)\b"
        )
        night_pattern = re.compile(r"\bNight:\b")

        matches = list(header_pattern.finditer(target_text))

        if len(matches) >= 2:
            # --- Period 1 (Tonight/Today) ---
            p1_name = matches[0].group(1).strip()
            p1_text_raw = target_text[matches[0].end() : matches[1].start()].strip()
            p1_summary = summarize_forecast_text(p1_text_raw)

            # --- Period 2 (Tomorrow Daytime) ---
            p2_raw = matches[1].group(1).strip()
            p2_name = p2_raw.split()[0]  # Shortens "Thu , 30 Jul" down to "Thu"

            p2_end_match = matches[2].start() if len(matches) > 2 else len(target_text)
            night_match = night_pattern.search(target_text, matches[1].end())
            if night_match and night_match.start() < p2_end_match:
                p2_end_match = night_match.start()

            p2_text_raw = target_text[matches[1].end() : p2_end_match].strip()
            p2_summary = summarize_forecast_text(p2_text_raw)

            return f"{p1_name}: {p1_summary} | {p2_name}: {p2_summary}"

        return "Could not extract forecast text."

    except Exception as e:
        return f"Fetch failed: {e}"


@command("forecast", help="Get the short multi-day Ottawa (YOW) forecast")
async def forecast(ctx: Context) -> str:
    """The async command handler triggered by !forecast."""
    who = ctx.sender_name or "you"

    try:
        forecast_text = await asyncio.to_thread(fetch_forecast_datamart)
        msg = f"@[{who}] YOW: {forecast_text}"

    except Exception:
        msg = f"@[{who}] Error fetching YOW forecast."

    # Enforce the strict 141-character limit for mesh radios
    if len(msg) > 141:
        msg = msg[:138] + "..."

    return msg
