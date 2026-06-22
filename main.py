import os
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI
import json
import requests


load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

WATCHLIST = ["NVDA", "AMD", "MSFT", "MU"]

def search_topic(query):
    response = tavily.search(
        query=query,
        search_depth="basic",
        max_results=5,
        include_answer=False,
    )

    results = response.get("results", [])

    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
        })

    return formatted
    # save formatted as a file for testing

def send_to_discord(message): #investing new stocks we might want
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("No Discord webhook URL set.")
        return

    requests.post(webhook_url, json={
        "content": message[:1900]
    })
def find_bullish_stocks():
    discovery_results = search_topic(
        "stocks with bullish momentum today AI earnings upgrades breakout analyst upgrade site:finance.yahoo.com OR site:marketwatch.com OR site:cnbc.com"
    )

    context = f"""
Current watchlist to exclude: {WATCHLIST}

Discovery search results:
{discovery_results}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are a stock research assistant.

Find 1-2 stocks that look bullish or worth watching based only on the provided search results.

Rules:
- Do not include anything already in the current watchlist.
- Do not give financial advice.
- Do not claim certainty.
- Prefer stocks with a clear catalyst: earnings beat, analyst upgrade, AI demand, breakout, guidance raise, unusual momentum, or major deal.
- If the evidence is weak, say "No strong discovery candidates today."

Format:

## New Bullish Stocks To Watch

### TICKER - Company Name
- Why it showed up:
- Bullish catalyst:
- Risk / uncertainty:
- Confidence: Low / Medium / High

{context}
"""
    )

    return response.output_text

def build_report_for_ticker(ticker): #main code for looking at existing stocks in our list
    news = search_topic(f"{ticker} stock latest news today")
    reddit = search_topic(f"{ticker} stock site:reddit.com/r/stocks OR site:reddit.com/r/investing recent")

    with open(f"{ticker}_raw_data.json", "w") as file:
        json.dump(
        {
            "news": news,
            "reddit": reddit
        },
        file,
        indent=4
    )

    context = f"""
Ticker: {ticker}

NEWS RESULTS:
{news}

REDDIT RESULTS:
{reddit}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
You are a stock research assistant.

Using only the provided search results, summarize:
1. What changed within 48 hours
2. Possible catalysts
3. Reddit/investor sentiment
4. Risks or uncertainty
5. Whether this seems meaningful or just noise

Summarize the news and sentiment.

Do not state specific stock prices unless explicitly provided in the context.
If price information is inconsistent or unavailable, say so.

Do not give financial advice. Be clear when evidence is weak.

{context}
"""
    )

    return response.output_text

from datetime import datetime

def main():
    today = datetime.now().strftime("%Y-%m-%d")

    with open(f"stock_report_{today}.md", "w") as file:

        file.write(f"# Stock Report - {today}\n\n")

        for ticker in WATCHLIST:

            print(f"Building report for {ticker}...")

            report = build_report_for_ticker(ticker)
            send_to_discord(f"📈 **{ticker} Report**\n\n{report}")

            file.write(f"## {ticker}\n\n")
            file.write(report)
            file.write("\n\n---\n\n")

        
        print("Looking for new bullish stocks...")

        discovery_report = find_bullish_stocks()
        send_to_discord(f"🚀 **New Bullish Stocks To Watch**\n\n{discovery_report}")

        file.write("# New Bullish Stocks To Watch\n\n")
        file.write(discovery_report)
        file.write("\n\n---\n\n")

    print("Report complete!")
if __name__ == "__main__":
    main()