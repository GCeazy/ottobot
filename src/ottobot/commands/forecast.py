"""!forecast — check the short-term weather forecast for Ottawa (YOW)."""

import urllib.request
import asyncio
import re
from ottobot import Context, command

# URL for Environment Canada's forecast for Ottawa
URL = "https://weather.gc.ca/en/location/index.html?coords=45.403,-75.687"


def summarize_forecast_text(text: str) -> str:
    """Compresses a detailed forecast block using heavy abbreviation for mesh limits."""
    # Strip leading temperature prefixes and trailing UV index sentences
    clean = re.sub(r"^-?\d+°?\s*C\.?\s*", "", text).strip()
    clean = re.sub(r"UV index.*?(\.|$)", "", clean, flags=re.IGNORECASE)

    # Bond temperatures tightly (e.g. "High 25" -> "H:25")
    clean = re.sub(r"\bHigh\s+(-?\d+)", r"H:\1", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bLow\s+(-?\d+)", r"L:\1", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bHumidex\s+(\d+)", r"Hx:\1", clean, flags=re.IGNORECASE)

    # Condense probability swings (e.g., 30->70% shwrs)
    clean = re.sub(
        r"(\d+)\s*percent chance of showers changing to (\d+)\s*percent chance of showers",
        r"\1->\2% shwrs",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"(\d+)\s*percent chance of showers", r"\1% shwrs", clean, flags=re.IGNORECASE
    )
    clean = re.sub(r"(\d+)\s*percent chance", r"\1%", clean, flags=re.IGNORECASE)

    # General word compression mapping - updated with new abbreviations
    abbr_map = {
        r"\bchanging to\b": "->",
        r"\bbecoming\b": "->",
        r"\bRisk of a thunderstorm\b": "Risk TStorm",
        r"\bMainly cloudy\b": "Mnly Cldy",
        r"\bPartly cloudy\b": "Ptly Cldy",
        r"\bMostly cloudy\b": "Mstly Cldy",
        r"\bA mix of sun and cloud\b": "Sun/Cld Mix",
        r"\bkm/h\b": "kph",
        r"\bgusting to\b": "gust",
        r"\bLocal amount\b": "Amt",
        r"\bwith\b": "w/",
        r"\band\b": "&",
        # Drop redundant time-of-day phrases to save space
        r"\bthis afternoon\b": "",
        r"\bearly this evening\b": "",
        r"\bthis evening\b": "",
        r"\bnear noon\b": "",
        r"\bthis morning\b": "",
    }

    for k, v in abbr_map.items():
        clean = re.sub(k, v, clean, flags=re.IGNORECASE)

    # Replace periods separating sentences with commas to condense text
    clean = re.sub(r"\.\s*", ", ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    clean = re.sub(r"\s+,", ",", clean)

    # --- TEMPERATURE PRIORITY LOGIC ---
    # Extract the temperatures so we can move them to the front of the string
    temps = []
    for prefix in [r"H:", r"L:", r"Hx:"]:
        match = re.search(rf"{prefix}-?\d+", clean)
        if match:
            temps.append(match.group(0))
            # Remove the temp from its original location
            clean = re.sub(rf"{prefix}-?\d+", "", clean)

    # Clean up orphan commas left behind by removing the temperatures
    clean = re.sub(r",\s*,", ",", clean)
    clean = re.sub(r"[, ]+$", "", clean)
    clean = clean.strip(", ")

    # Re-attach temperatures at the very front of the summary
    if temps:
        temp_str = ", ".join(temps)
        if clean:
            clean = f"{temp_str}, {clean}"
        else:
            clean = temp_str

    return clean


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

            return f"{p1_name} > {p1_summary} | {p2_name} > {p2_summary}"

        return "Could not extract forecast text."

    except Exception as e:
        return f"Fetch failed: {e}"


@command("forecast", help="Get the short multi-day Ottawa (YOW) forecast")
async def forecast(ctx: Context) -> str:
    """The async command handler triggered by !forecast."""
    who = ctx.sender_name or "you"

    try:
        forecast_text = await asyncio.to_thread(fetch_forecast_datamart)
        msg = f"@[{who}] YOW FCST: {forecast_text}"

    except Exception:
        msg = f"@[{who}] Error fetching YOW forecast."

    # Enforce the strict 141-character limit for mesh radios
    if len(msg) > 141:
        msg = msg[:138] + "..."

    return msg
