"""
actions/finance_engine.py
Stock analysis, portfolio tracking, market data, technical indicators.
Inspired by AutoHedge, Vibe-Trading, FinceptTerminal.
"""

import json
import logging
import math
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("finance_engine")
USER_AGENT = "MAX-MARK-I/1.0 (Autonomous Assistant)"
TIMEOUT = 6.0


def _memory_dir() -> Path:
    d = Path(__file__).resolve().parent.parent / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_json(name: str) -> dict:
    p = _memory_dir() / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_json(name: str, data: dict):
    (_memory_dir() / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _yahoo_quote(symbol: str) -> dict:
    """Fetch quote from Yahoo Finance unofficial API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            return {
                "symbol": meta.get("symbol", symbol),
                "price": meta.get("regularMarketPrice", 0),
                "previous_close": meta.get("previousClose", 0),
                "currency": meta.get("currency", "USD"),
                "exchange": meta.get("exchangeName", ""),
                "name": meta.get("shortName", symbol),
                "market_time": meta.get("regularMarketTime", 0),
            }
    except Exception:
        pass
    # Fallback to Alpha Vantage demo
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=demo"
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.status_code == 200:
            gq = resp.json().get("Global Quote", {})
            return {
                "symbol": gq.get("01. symbol", symbol),
                "price": float(gq.get("05. price", 0)),
                "previous_close": float(gq.get("08. previous close", 0)),
                "change": gq.get("09. change", "0"),
                "change_pct": gq.get("10. change percent", "0%"),
            }
    except Exception:
        pass
    return {}


def finance_engine(parameters: dict, player=None) -> str:
    """Financial analysis engine."""
    action = (parameters.get("action") or "stock_quote").strip().lower()
    aliases = {
        "quote": "stock_quote", "stock": "stock_quote", "portfolio": "portfolio_summary",
        "portfolio_view": "portfolio_summary", "portfolio_add": "portfolio_track",
        "crypto": "crypto_analysis", "market": "market_overview", "market_summary": "market_overview",
        "news": "stock_news", "analysis": "technical_analysis", "forex": "forex_rates"
    }
    action = aliases.get(action, action)

    if action == "stock_quote":
        symbol = (parameters.get("symbol") or parameters.get("ticker", "AAPL")).strip().upper()
        q = _yahoo_quote(symbol)
        if not q or not q.get("price"):
            return f"Could not fetch quote for '{symbol}'. Check the ticker symbol."
        price = q["price"]
        prev = q.get("previous_close", price)
        change = price - prev if prev else 0
        change_pct = (change / prev * 100) if prev else 0
        arrow = "📈" if change >= 0 else "📉"
        return (
            f"{arrow} {q.get('name', symbol)} ({symbol})\n"
            f"  • Price: ${price:.2f} {q.get('currency', 'USD')}\n"
            f"  • Change: {'+' if change >= 0 else ''}{change:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%)\n"
            f"  • Previous Close: ${prev:.2f}\n"
            f"  • Exchange: {q.get('exchange', 'N/A')}"
        )

    elif action == "market_overview":
        indices = ["^GSPC", "^IXIC", "^DJI", "^NSEI", "^FTSE"]
        names = {"^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^DJI": "Dow Jones", "^NSEI": "NIFTY 50", "^FTSE": "FTSE 100"}
        lines = ["📊 Market Overview:\n"]
        for idx in indices:
            q = _yahoo_quote(idx)
            if q and q.get("price"):
                price = q["price"]
                prev = q.get("previous_close", price)
                chg = price - prev if prev else 0
                pct = (chg / prev * 100) if prev else 0
                arrow = "🟢" if chg >= 0 else "🔴"
                lines.append(f"  {arrow} {names.get(idx, idx)}: {price:,.2f} ({'+' if chg >= 0 else ''}{pct:.2f}%)")
            else:
                lines.append(f"  ⚪ {names.get(idx, idx)}: unavailable")
        return "\n".join(lines)

    elif action == "portfolio_track":
        symbol = (parameters.get("symbol") or "").strip().upper()
        shares = float(parameters.get("shares", 0))
        buy_price = float(parameters.get("buy_price", 0))
        if not symbol or not shares:
            return "Symbol and shares are required."
        portfolio = _load_json("portfolio.json")
        if "holdings" not in portfolio:
            portfolio["holdings"] = []
        portfolio["holdings"].append({
            "symbol": symbol,
            "shares": shares,
            "buy_price": buy_price,
            "buy_date": time.strftime("%Y-%m-%d"),
        })
        _save_json("portfolio.json", portfolio)
        return f"✅ Added {shares} shares of {symbol} @ ${buy_price:.2f} to portfolio."

    elif action == "portfolio_summary":
        portfolio = _load_json("portfolio.json")
        holdings = portfolio.get("holdings", [])
        if not holdings:
            return "Portfolio is empty. Use 'portfolio_track' to add holdings."
        lines = ["💼 Portfolio Summary:\n"]
        total_value = 0
        total_cost = 0
        for h in holdings:
            q = _yahoo_quote(h["symbol"])
            curr_price = q.get("price", h["buy_price"]) if q else h["buy_price"]
            value = curr_price * h["shares"]
            cost = h["buy_price"] * h["shares"]
            pnl = value - cost
            pnl_pct = (pnl / cost * 100) if cost else 0
            total_value += value
            total_cost += cost
            arrow = "🟢" if pnl >= 0 else "🔴"
            lines.append(
                f"  {arrow} {h['symbol']}: {h['shares']} shares @ ${curr_price:.2f} = ${value:,.2f} "
                f"(P&L: {'+' if pnl >= 0 else ''}{pnl:,.2f} / {pnl_pct:+.1f}%)"
            )
        total_pnl = total_value - total_cost
        lines.append(f"\n  💰 Total Value: ${total_value:,.2f}")
        lines.append(f"  📊 Total P&L: {'+' if total_pnl >= 0 else ''}${total_pnl:,.2f}")
        return "\n".join(lines)

    elif action == "watchlist":
        symbol = (parameters.get("symbol") or "").strip().upper()
        sub_action = (parameters.get("sub_action") or "list").strip().lower()
        wl = _load_json("watchlist.json")
        if "symbols" not in wl:
            wl["symbols"] = []
        if sub_action == "add" and symbol:
            if symbol not in wl["symbols"]:
                wl["symbols"].append(symbol)
                _save_json("watchlist.json", wl)
            return f"✅ Added {symbol} to watchlist."
        elif sub_action == "remove" and symbol:
            wl["symbols"] = [s for s in wl["symbols"] if s != symbol]
            _save_json("watchlist.json", wl)
            return f"✅ Removed {symbol} from watchlist."
        else:
            if not wl["symbols"]:
                return "Watchlist is empty. Use sub_action 'add' with a symbol."
            lines = ["👁️ Watchlist:\n"]
            for s in wl["symbols"]:
                q = _yahoo_quote(s)
                if q and q.get("price"):
                    price = q["price"]
                    prev = q.get("previous_close", price)
                    pct = ((price - prev) / prev * 100) if prev else 0
                    arrow = "🟢" if pct >= 0 else "🔴"
                    lines.append(f"  {arrow} {s}: ${price:.2f} ({pct:+.2f}%)")
                else:
                    lines.append(f"  ⚪ {s}: unavailable")
            return "\n".join(lines)

    elif action == "crypto_analysis":
        coin = (parameters.get("coin") or parameters.get("symbol", "bitcoin")).strip().lower()
        try:
            resp = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{coin}?localization=false&tickers=false&community_data=false&developer_data=false",
                timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
            )
            if resp.status_code == 200:
                d = resp.json()
                md = d.get("market_data", {})
                price = md.get("current_price", {}).get("usd", 0)
                mc = md.get("market_cap", {}).get("usd", 0)
                vol = md.get("total_volume", {}).get("usd", 0)
                ath = md.get("ath", {}).get("usd", 0)
                chg24 = md.get("price_change_percentage_24h", 0)
                chg7 = md.get("price_change_percentage_7d", 0)
                chg30 = md.get("price_change_percentage_30d", 0)
                return (
                    f"🪙 {d.get('name', coin)} ({d.get('symbol', '').upper()}):\n"
                    f"  • Price: ${price:,.2f}\n"
                    f"  • 24h Change: {chg24:+.2f}%\n"
                    f"  • 7d Change: {chg7:+.2f}%\n"
                    f"  • 30d Change: {chg30:+.2f}%\n"
                    f"  • Market Cap: ${mc:,.0f}\n"
                    f"  • 24h Volume: ${vol:,.0f}\n"
                    f"  • All-Time High: ${ath:,.2f}"
                )
            return f"CoinGecko returned status {resp.status_code}."
        except Exception as e:
            return f"Crypto analysis failed: {e}"

    elif action == "forex_rates":
        base = (parameters.get("base") or "USD").strip().upper()
        try:
            resp = requests.get(f"https://api.frankfurter.app/latest?from={base}",
                                timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                lines = [f"💱 Forex Rates (Base: {base}, {data.get('date', '')}):\n"]
                for curr in ["EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY"]:
                    if curr in rates:
                        lines.append(f"  • {curr}: {rates[curr]:.4f}")
                return "\n".join(lines)
            return f"Forex API returned status {resp.status_code}."
        except Exception as e:
            return f"Forex query failed: {e}"

    elif action == "technical_analysis":
        symbol = (parameters.get("symbol") or "AAPL").strip().upper()
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"
            resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                closes = [c for c in closes if c is not None]
                if len(closes) < 5:
                    return f"Not enough price data for {symbol}."
                sma5 = sum(closes[-5:]) / 5
                sma20 = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 5 else sma5
                curr = closes[-1]
                prev = closes[-2] if len(closes) > 1 else curr
                chg = ((curr - prev) / prev * 100) if prev else 0
                # RSI calculation
                gains, losses = [], []
                for i in range(1, min(15, len(closes))):
                    diff = closes[i] - closes[i - 1]
                    if diff > 0:
                        gains.append(diff)
                    else:
                        losses.append(abs(diff))
                avg_gain = sum(gains) / 14 if gains else 0
                avg_loss = sum(losses) / 14 if losses else 0.001
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
                return (
                    f"📊 Technical Analysis: {symbol}\n"
                    f"  • Current Price: ${curr:.2f}\n"
                    f"  • Daily Change: {chg:+.2f}%\n"
                    f"  • SMA(5): ${sma5:.2f}\n"
                    f"  • SMA(20): ${sma20:.2f}\n"
                    f"  • RSI(14): {rsi:.1f} ({signal})\n"
                    f"  • Trend: {'Bullish' if curr > sma20 else 'Bearish'} (price {'above' if curr > sma20 else 'below'} SMA20)"
                )
        except Exception as e:
            return f"Technical analysis failed: {e}"
        return f"Could not fetch data for {symbol}."

    elif action == "stock_news":
        query = (parameters.get("query") or parameters.get("symbol", "market")).strip()
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.news(f"{query} stock market", max_results=5))
            if results:
                lines = [f"📰 Financial News for '{query}':\n"]
                for r in results[:5]:
                    lines.append(f"  • {r.get('title', 'N/A')}\n    {r.get('url', '')}")
                return "\n".join(lines)
            return f"No news found for '{query}'."
        except ImportError:
            return "duckduckgo_search not installed."
        except Exception as e:
            return f"News search failed: {e}"

    else:
        return (
            f"Unknown action '{action}'. Available: stock_quote, market_overview, portfolio_track, "
            "portfolio_summary, watchlist, crypto_analysis, forex_rates, technical_analysis, stock_news"
        )


if __name__ == "__main__":
    print(finance_engine({"action": "stock_quote", "symbol": "AAPL"}))
    print("\n" + finance_engine({"action": "forex_rates"}))

