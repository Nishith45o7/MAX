"""
actions/public_api_tools.py
Curated collection of high-utility, zero-key public APIs from public-apis/public-apis:
1. Live Weather & Forecast (wttr.in) - auto-location & global cities
2. Live Currency Exchange (Frankfurter API) - EUR, USD, INR, GBP, JPY, CAD, etc.
3. Live Crypto Market Prices (CoinGecko Simple API) - BTC, ETH, SOL, XRP, etc.
4. Encyclopedia Knowledge (Wikipedia REST API) - Fast, accurate summaries
5. Trending Tech News (Hacker News Firebase API) - Live engineering & AI headlines
6. IP Geolocation (ip-api.com) - Current city, country, timezone, and ISP
"""

import requests
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("public_api_tools")
USER_AGENT = "MAX-MARK-I/1.0 (Autonomous Assistant)"
TIMEOUT = 4.0


def get_live_weather(city: str = "") -> str:
    """
    Fetches real-time weather and forecast using wttr.in.
    If city is empty or 'current', automatically uses IP geolocation.
    """
    try:
        clean_city = city.strip() if city and city.lower() not in ("current", "here", "local", "my location") else ""
        url = f"https://wttr.in/{clean_city}?format=j1" if clean_city else "https://wttr.in/?format=j1"
        
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if resp.status_code != 200:
            return f"Weather service returned status code {resp.status_code}."
            
        data = resp.json()
        area_info = data.get("nearest_area", [{}])[0]
        area_name = area_info.get("areaName", [{}])[0].get("value", "Current Location")
        country = area_info.get("country", [{}])[0].get("value", "")
        
        curr = data.get("current_condition", [{}])[0]
        temp_c = curr.get("temp_C", "N/A")
        temp_f = curr.get("temp_F", "N/A")
        feels_c = curr.get("FeelsLikeC", "N/A")
        desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
        humidity = curr.get("humidity", "N/A")
        wind_km = curr.get("windspeedKmph", "N/A")
        
        # 3-day forecast summary
        forecast_lines = []
        for day in data.get("weather", [])[:3]:
            date = day.get("date", "")
            max_c = day.get("maxtempC", "")
            min_c = day.get("mintempC", "")
            day_desc = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")
            forecast_lines.append(f"  • {date}: {day_desc}, High {max_c}°C / Low {min_c}°C")
            
        loc_str = f"{area_name}, {country}".strip(", ")
        forecast_str = "\n".join(forecast_lines)
        
        return (
            f"Weather Report for {loc_str}:\n"
            f"• Condition: {desc}\n"
            f"• Temperature: {temp_c}°C ({temp_f}°F) [Feels like {feels_c}°C]\n"
            f"• Humidity: {humidity}%\n"
            f"• Wind Speed: {wind_km} km/h\n"
            f"\n3-Day Forecast:\n{forecast_str}"
        )
    except Exception as e:
        logger.error(f"Weather query failed: {e}")
        return f"Could not retrieve weather data: {e}"


def get_crypto_currency_rates(
    action: str = "crypto",
    crypto_symbols: str = "bitcoin,ethereum,solana",
    amount: float = 1.0,
    from_curr: str = "USD",
    to_curr: str = "EUR,INR,GBP"
) -> str:
    """
    Fetches real-time crypto prices (CoinGecko) or converts fiat currencies (Frankfurter API).
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        if action == "fiat" or "convert" in action:
            # Frankfurter Currency Exchange API
            from_c = from_curr.strip().upper()
            to_c = to_curr.strip().upper().replace(" ", "")
            url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_c}&to={to_c}"
            
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                date = data.get("date", "Recent")
                rates = data.get("rates", {})
                conversions = [f"  • {amt:.2f} {curr}" for curr, amt in rates.items()]
                return f"Exchange Rate ({date}) for {amount} {from_c}:\n" + "\n".join(conversions)
            return f"Currency exchange lookup failed (status: {resp.status_code})."
        else:
            # CoinGecko Simple Price API
            ids = crypto_symbols.lower().replace(" ", "")
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd,inr,eur"
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            
            if resp.status_code == 200:
                data = resp.json()
                lines = []
                for coin, prices in data.items():
                    usd = prices.get("usd", "N/A")
                    inr = prices.get("inr", "N/A")
                    lines.append(f"  • {coin.capitalize()}: ${usd:,} USD | {inr:,} INR")
                if lines:
                    return "Live Crypto Market Prices:\n" + "\n".join(lines)
                return f"No crypto prices found for symbols: {crypto_symbols}"
            return f"CoinGecko lookup failed (status: {resp.status_code})."
    except Exception as e:
        logger.error(f"Crypto/Currency query failed: {e}")
        return f"Error fetching exchange/crypto rates: {e}"


def get_wikipedia_summary(query: str) -> str:
    """
    Fetches authoritative, fast encyclopedic summary from Wikipedia REST API.
    """
    try:
        title = query.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        headers = {"User-Agent": USER_AGENT}
        
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            extract = data.get("extract", "")
            page_title = data.get("title", query)
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            
            return (
                f"Wikipedia: {page_title}\n\n"
                f"{extract}\n\n"
                f"Source: {page_url}"
            )
        elif resp.status_code == 404:
            return f"No direct Wikipedia article found for '{query}'. Try searching web instead."
        return f"Wikipedia API returned code {resp.status_code}."
    except Exception as e:
        logger.error(f"Wikipedia query failed: {e}")
        return f"Error retrieving Wikipedia summary: {e}"


def get_top_tech_news(limit: int = 5) -> str:
    """
    Fetches trending technology and AI headlines from Hacker News.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        resp = requests.get(top_url, headers=headers, timeout=TIMEOUT)
        
        if resp.status_code != 200:
            return "Could not retrieve Hacker News stories."
            
        story_ids = resp.json()[:max(1, min(limit, 10))]
        stories = []
        
        for sid in story_ids:
            try:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                item_resp = requests.get(item_url, headers=headers, timeout=2.0)
                if item_resp.status_code == 200:
                    item = item_resp.json()
                    title = item.get("title", "Untitled")
                    url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                    score = item.get("score", 0)
                    stories.append(f"  • {title} ({score} pts)\n    Link: {url}")
            except Exception:
                continue
                
        if stories:
            return "Top Trending Tech & AI Headlines:\n" + "\n\n".join(stories)
        return "No tech stories available."
    except Exception as e:
        logger.error(f"Tech news query failed: {e}")
        return f"Error fetching tech news: {e}"


def get_ip_geolocation() -> str:
    """
    Fetches network & location details (city, region, country, timezone, ISP) via ip-api.com.
    """
    try:
        url = "http://ip-api.com/json/"
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                city = data.get("city", "Unknown")
                region = data.get("regionName", "")
                country = data.get("country", "")
                ip = data.get("query", "")
                isp = data.get("isp", "")
                tz = data.get("timezone", "")
                
                return (
                    f"Host Network & Location Information:\n"
                    f"• Location: {city}, {region}, {country}\n"
                    f"• Timezone: {tz}\n"
                    f"• Public IP: {ip}\n"
                    f"• ISP: {isp}"
                )
        return "Could not retrieve IP geolocation details."
    except Exception as e:
        logger.error(f"Geolocation query failed: {e}")
        return f"Error retrieving geolocation: {e}"


if __name__ == "__main__":
    print("=== Testing Public API Tools ===")
    print(get_live_weather("London"))
    print("\n" + get_crypto_currency_rates(action="crypto", crypto_symbols="bitcoin,ethereum"))
    print("\n" + get_crypto_currency_rates(action="fiat", amount=100, from_curr="USD", to_curr="EUR,INR"))
    print("\n" + get_wikipedia_summary("Alan Turing")[:200])
    print("\n" + get_ip_geolocation())
