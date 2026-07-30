"""!weather — check the current weather in Ottawa (YOW)."""

import re
import urllib.request
import asyncio
from ottobot import Context, command

URL = "https://weather.gc.ca/en/location/index.html?coords=45.403,-75.687"


def fetch_weather() -> dict:
    """Synchronous function to fetch and parse weather data."""
    req = urllib.request.Request(
        URL, headers={"User-Agent": "Mozilla/5.0 (Ottobot Mesh Node)"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read().decode("utf-8")

    # Strip HTML tags to create a clean text block for regex searching
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    # Extract weather data points using regular expressions
    condition = re.search(r"Condition:\s*(.+?)\s*Pressure:", text)
    temp = re.search(r"Temperature\W+([-\d\.]+)", text)
    wind = re.search(r"Wind\W+([A-Z]{1,3})\s*(\d+)\s*km/h", text)

    # Bulletproof regex for Humidex and Wind chill to bypass HTML formatting quirks
    humidex = re.search(r"Humidex\W+(\d+)", text, re.IGNORECASE)
    windchill = re.search(r"Wind chill\W+(-?\d+)", text, re.IGNORECASE)

    return {
        "condition": condition.group(1).strip() if condition else "Unknown",
        "temp": temp.group(1) if temp else None,
        "wind_dir": wind.group(1) if wind else "Unknown",
        "wind_speed": wind.group(2) if wind else "Unknown",
        "humidex": humidex.group(1) if humidex else None,
        "windchill": windchill.group(1) if windchill else None,
    }


@command("weather", help="Get the current Ottawa (YOW) weather")
async def weather(ctx: Context) -> str:
    """The async command handler triggered by !weather."""
    who = ctx.sender_name or "you"

    try:
        data = await asyncio.to_thread(fetch_weather)

        try:
            temp_str = str(round(float(data["temp"]))) if data["temp"] else "??"
        except (ValueError, TypeError):
            temp_str = "??"

        feels_like = ""
        if data["humidex"]:
            feels_like = f", Humidex {data['humidex']}"
        elif data["windchill"]:
            feels_like = f", Windchill {data['windchill']}"

        wind_str = f"{data['wind_dir']} {data['wind_speed']} km/h"

        msg = f"@[{who}] Current YOW WX: {data['condition']}, {temp_str} C{feels_like}, Wind {wind_str}"

    except Exception as e:
        msg = f"@[{who}] Error fetching YOW weather."

    if len(msg) > 141:
        msg = msg[:138] + "..."

    return msg
