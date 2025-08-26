import yfinance as yf
import requests

def get_order_book(tool_args: dict):
    symbol = tool_args.get("symbol", "BTCUSDT").upper()
    depth = tool_args.get("depth", 5    )

    url = f"https://api.binance.us/api/v3/depth?symbol=BTCUSDT&limit=10"
    params = {"symbol": symbol, "limit": depth}

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        return {
            "symbol": symbol,
            "bids": data["bids"],  # list of [price, quantity]
            "asks": data["asks"]
        }

    except Exception as e:
        return {"error": f"Failed to retrieve order book for {symbol}: {str(e)}"}



def get_technical_indicators(tool_args: dict):
    
    ticker = tool_args.get("ticker")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo")

        df["SMA_20"] = df["Close"].rolling(window=20).mean()
        df["RSI_14"] = 100 - (100 / (1 + df["Close"].pct_change().add(1).rolling(14).mean()))
        latest = df.iloc[-1]

        return {
            "ticker": ticker,
            "SMA_20": round(latest["SMA_20"], 2),
            "RSI_14": round(latest["RSI_14"], 2),
            "latest_price": round(latest["Close"], 2)
        }
    except Exception as e:
        return {"error": str(e)}
    


    
def get_stock_price(tool_args: dict):
    ticker = tool_args.get("ticker")
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        latest = data.iloc[-1]
        return {
            "ticker": ticker,
            "price": round(latest["Close"], 2),
            "open": round(latest["Open"], 2),
            "volume": int(latest["Volume"]),
            "change_pct": round(((latest["Close"] - latest["Open"]) / latest["Open"]) * 100, 2)
        }
    except Exception as e:
        return {"error": str(e)}
    



def get_earnings_data(tool_args: dict):

    tickers = tool_args.get("tickers")
    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.split(",")]

    earnings_data = {}

    for ticker in tickers:
        try:
            print(f"📡 Fetching: {ticker}")
            stock = yf.Ticker(ticker)
            income_stmt = stock.income_stmt

            print(f"📄 income_stmt for {ticker}:\n{income_stmt}")

            if income_stmt is not None and not income_stmt.empty:
                latest_col = income_stmt.columns[0]

                revenue = income_stmt.loc["Total Revenue"][latest_col] if "Total Revenue" in income_stmt.index else None
                net_income = income_stmt.loc["Net Income"][latest_col] if "Net Income" in income_stmt.index else None

                data = {
                    "Total Revenue": int(revenue) if revenue else "N/A",
                    "Net Income": int(net_income) if net_income else "N/A",
                    "Period Ending": str(latest_col.date()) if hasattr(latest_col, 'date') else str(latest_col)
                }

                earnings_data[ticker] = data
            else:
                earnings_data[ticker] = "No earnings data found (empty income_stmt)"

        except Exception as e:
            earnings_data[ticker] = f"Error: {str(e)}"

    return earnings_data






def get_finance_news(tool_args: dict):
    query = tool_args.get("query", "")
    max_results = tool_args.get("max_results", 5)
    api_key = "pub_65f81972c70a4d05a2f040f68c14089b"  # ← Replace this with your actual key

    try:
        url = f"https://newsdata.io/api/1/news?apikey={api_key}&q={query}&language=en"
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])[:max_results]

        return [
            {
                "title": item.get("title"),
                "pubDate": item.get("pubDate"),
                "link": item.get("link"),
                "description": item.get("description")
            }
            for item in results
        ]

    except Exception as e:
        return {"error": str(e)}


    

# def analyze_news_sentiment(tool_args: dict):
#     news_items = tool_args.get("news", [])
#     results = []
#     for item in news_items:
#         text = item.get("title", "") + " " + item.get("description", "")
#         sentiment = TextBlob(text).sentiment
#         results.append({
#             "title": item.get("title"),
#             "polarity": round(sentiment.polarity, 3),
#             "subjectivity": round(sentiment.subjectivity, 3)
#         })
#     return results