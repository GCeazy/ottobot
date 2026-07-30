"""!weather — check the current conditions for Ottawa (YOW)."""

import urllib.request
import asyncio
import re
from ottobot import Context, command

# URL for Environment Canada's location page for Ottawa
URL = "https://weather.gc.ca/en/location/index.html?coords=45.403,-75.687"


def fetch_current_weather() -> str:
    """Fetches current weather by reliably parsing the Current Conditions section."""
    req = urllib.request.Request(
        URL, headers={"User-Agent": "Mozilla/5.0 (Ottobot Mesh Node)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")

        # Clean up the HTML tags and extra whitespace
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        text = text.replace("&deg;", "°")

        # Isolate the Current Conditions section
        if "Current Conditions" in text and "Forecast" in text:
            target_text = text.split("Current Conditions")[1].split("Forecast")[0]
        else:
            return "Could not locate Current Conditions data."

        # Helper to find a value following a specific label
        def extract_value(label: str) -> str:
            # Look for the label followed by an optional colon
            label_pattern = f"{label}:"
            alt_label_pattern = f"{label}"

            # Find where the label starts
            start_idx = target_text.find(label_pattern)
            if start_idx == -1:
                start_idx = target_text.find(alt_label_pattern)
                if start_idx == -1:
                    return ""
                # Adjust start index past the label itself
                start_idx += len(alt_label_pattern)
            else:
                start_idx += len(label_pattern)

            # Extract the text after the label
            remaining_text = target_text[start_idx:].strip()

            # The value usually ends before the next known label or a common delimiter
            # We'll split by common labels to find the end of our value
            next_labels = [
                "Condition",
                "Pressure",
                "Tendency",
                "Temperature",
                "Dew point",
                "Humidity",
                "Wind",
                "Humidex",
                "Visibility",
                "Date",
                "Observed at",
            ]

            end_idx = len(remaining_text)
            for next_label in next_labels:
                # Don't look for the label we are currently extracting
                if next_label != label:
                    idx = remaining_text.find(next_label)
                    if idx != -1 and idx < end_idx:
                        end_idx = idx

            # Return the extracted value, cleaning up any trailing colons or spaces
            val = remaining_text[:end_idx].strip()
            # Remove a leading colon if it was caught
            if val.startswith(":"):
                val = val[1:].strip()
            return val

        # Extract the specific data points
        temp = extract_value("Temperature")
        humidex = extract_value("Humidex")
        cond = extract_value("Condition")
        wind = extract_value("Wind")

        # Build the final output string exactly as requested
        msg_parts = []
        if temp:
            msg_parts.append(temp)
        if humidex:
            # Ensure only numbers are kept for the Humidex value
            clean_humidex = re.sub(r"[^0-9]", "", humidex)
            if clean_humidex:
                msg_parts.append(f"Humidex: {clean_humidex}")
        if cond:
            # Abbreviate conditions if necessary to save space (optional, based on your previous preferences)
            cond = (
                cond.replace("Mainly cloudy", "Mnly Cldy")
                .replace("Mostly Cloudy", "Mstly Cldy")
                .replace("Partly cloudy", "Ptly Cldy")
            )
            msg_parts.append(cond)
        if wind:
            msg_parts.append(f"Wind {wind}")

        return " | ".join(msg_parts) if msg_parts else "No weather data available."

    except Exception as e:
        return f"Fetch failed: {e}"


@command("weather", help="Get current Ottawa (YOW) weather conditions")
async def weather(ctx: Context) -> str:
    """The async command handler triggered by !weather."""
    who = ctx.sender_name or "you"

    try:
        weather_text = await asyncio.to_thread(fetch_current_weather)
        msg = f"@[{who}] Current YOW WX: {weather_text}"

    except Exception:
        msg = f"@[{who}] Error fetching YOW weather."

    # Enforce the strict 141-character limit for mesh radios
    if len(msg) > 141:
        msg = msg[:138] + "..."

    return msg
