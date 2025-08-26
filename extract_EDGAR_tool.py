import requests
import json
import pandas as pd
from bs4 import BeautifulSoup

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

HEADERS = {
    "User-Agent": "Your Name your.email@example.com",
    "Accept-Encoding": "gzip, deflate"
}

def get_income_statement_from_edgar(ticker_or_cik: str) -> dict:
    def fetch_company_submissions(cik: str) -> dict:
        normalized_cik = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{normalized_cik}.json"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()

    def get_latest_10k_url(data):
        filings = data["filings"]["recent"]
        for i, form in enumerate(filings["form"]):
            if form == "10-K":
                accession = filings["accessionNumber"][i].replace("-", "")
                cik = data["cik"].zfill(10)
                return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"
        return None

    def find_main_filing(doc_items):
        preferred_names = ["10-k", "10k", "form10k", "annual", "report"]
        for item in doc_items:
            name = item["name"].lower()
            if any(k in name for k in preferred_names) and name.endswith(".htm") and "exhibit" not in name and "index" not in name:
                return item["name"]
        for item in doc_items:
            name = item["name"].lower()
            if name.endswith(".htm") and "exhibit" not in name and "index" not in name:
                return item["name"]
        return None

    def fetch_and_parse_filing(doc_base_url, filename):
        full_url = f"{doc_base_url}/{filename}"
        res = requests.get(full_url, headers=HEADERS)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")

    def extract_income_statement(soup):
        target_phrases = [
            "Consolidated Statements of Operations",
            "Consolidated Statement of Income",
            "Consolidated Statements of Earnings"
        ]
        for tag in soup.find_all(['h1', 'h2', 'h3', 'b', 'strong', 'p', 'div']):
            text = tag.get_text(strip=True).replace(u'\xa0', ' ')
            for phrase in target_phrases:
                if phrase.lower() in text.lower():
                    if "page" in text.lower() or "index" in text.lower():
                        continue
                    table = tag.find_next("table")
                    if table:
                        return table.get_text(separator="\n", strip=True)
        return None

    try:
        # If user gave ticker, resolve to CIK via lookup
        if not ticker_or_cik.isdigit():
            resp = requests.get(f"https://www.sec.gov/files/company_tickers.json", headers=HEADERS)
            resp.raise_for_status()
            ticker_map = resp.json()
            cik = None
            for entry in ticker_map.values():
                if entry["ticker"].lower() == ticker_or_cik.lower():
                    cik = str(entry["cik_str"])
                    break
            if not cik:
                return {"error": f"Ticker '{ticker_or_cik}' not found in SEC lookup"}
        else:
            cik = ticker_or_cik

        data = fetch_company_submissions(cik)
        index_url = get_latest_10k_url(data)
        if not index_url:
            return {"error": "No recent 10-K filing found"}

        filing_index = requests.get(index_url, headers=HEADERS).json()
        doc_items = filing_index["directory"]["item"]
        filing_doc = find_main_filing(doc_items)

        if not filing_doc:
            return {"error": "Could not find main filing document"}

        base_url = index_url.rsplit("/", 1)[0]
        soup = fetch_and_parse_filing(base_url, filing_doc)
        income_text = extract_income_statement(soup)

        if not income_text:
            return {"error": "Income statement not found"}




        return {
            "source": "EDGAR",
            "ticker_or_cik": ticker_or_cik,
            "document": filing_doc,
            "income_statement": income_text[:3000]  # limit output if large
        }

    except Exception as e:
        return {"error": str(e)}


# raw_data: str, ticker: str
def parse_income_statement(args: dict) -> dict:

    raw_data = args['raw_data']
    ticker = args['ticker']

    prompt = f"""
    Extract the income statement data for the last 3 years from the following text. 
    Return a dictionary like: 
    {{
    "Years": ["2024", "2023", "2022"],
    "Net Sales": [391035, 383285, 394328],
    ...
    }}

    Raw Text:
    {raw_data}
    """
    OPENAI_API_KEY = "your_API_key"

    llm = ChatOpenAI(
        model="gpt-4",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.0,
        max_tokens=2048*2,
        stop_sequences=["Observation:"])
    
    sys_msg = SystemMessage(content="You are a financial data parser.")
    human_msg = HumanMessage(content=prompt)

    # Run the LLM with the prompt
    response = llm.invoke([sys_msg, human_msg])

        
    json_str = response.content
    parsed = json.loads(json_str)

    # df = pd.DataFrame(parsed)
    df = pd.DataFrame.from_dict(parsed, orient="index").T
    df = df.set_index("Years").T  # Transpose so rows are line items, columns are years
    
    df.to_csv("income_statement_"+ticker+".csv")
    print("Saved to income_statement_"+ticker+".csv")

    return response



# Test
# raw_data = get_income_statement_from_edgar("AAPL")
# print(raw_data)

# parse_income_statement(raw_data, "AAPL")
