"""!channels — list Ottawa's public MeshCore channels."""

from ottobot import Context, command

# Public channels from https://ottawamesh.ca/meshcore/general-public-channels/
# plus the #ott-alerts channel. This is a user-facing directory of channels to
# join, not the set the bot itself tunes to (see ottobot.channels.CHANNELS).
CHANNELS = (
    "#aircraft",
    "#aylmer",
    "#barrhaven",
    "#bike",
    "#bots",
    "#caf",
    "#cars",
    "#constancebay",
    "#games",
    "#hamradio",
    "#hike",
    "#music",
    "#ott-alerts",
    "#ottawa",
    "#queer",
    "#radio",
    "#testing",
    "#wardriving",
    "#watersports",
)


@command("channels", help="List Ottawa's public MeshCore channels")
async def channels(ctx: Context) -> list[str]:
    # Find the midpoint of the tuple to split the list evenly
    half_index = len(CHANNELS) // 2
    
    # Join each half into its own space-separated string
    page_1 = " ".join(CHANNELS[:half_index])
    page_2 = " ".join(CHANNELS[half_index:])
    
    # Return a list of strings; the framework will send them sequentially
    return [
        f"Channels (1/2): {page_1}",
        f"Channels (2/2): {page_2}"
    ]