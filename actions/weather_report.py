# actions/weather_report.py
# MARK I-OR Weather Action (Powered by public-apis zero-key wttr.in)

from actions.public_api_tools import get_live_weather


def weather_action(
    parameters: dict = None,
    player=None,
    session_memory=None
) -> str:
    """
    Retrieves real-time weather reports and forecasts for any city or current location.
    """
    params = parameters or {}
    city = params.get("city", "")
    
    if isinstance(city, str):
        city = city.strip()
    else:
        city = ""

    report = get_live_weather(city)
    
    if player:
        try:
            player.write_log(f"[weather] {report[:80]}...")
        except Exception:
            pass

    if session_memory:
        try:
            session_memory.set_last_search(
                query=f"weather {city}".strip(),
                response=report[:120]
            )
        except Exception:
            pass

    return report