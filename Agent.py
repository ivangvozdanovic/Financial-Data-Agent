from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langchain_core.messages import HumanMessage
from langgraph.graph import START, StateGraph, END
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from IPython.display import Image, display


from print_messages import pretty_print_messages
from financials_tool import get_technical_indicators, get_order_book, get_stock_price, get_finance_news, get_earnings_data
from image_description_tool import capture_screenshot, describe_image
from extract_EDGAR_tool import get_income_statement_from_edgar, parse_income_statement

import os
import sys
OPENAI_API_KEY = "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"
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


llm = ChatOpenAI(
    model="gpt-4",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.0,
    max_tokens=2048*2,
    stop_sequences=["Observation:"])



SYSTEM_PROMPT = """Answer the following questions as best you can. You have access to the following tools:
{tool_descriptions}

The way you use the tools is by specifying a json blob.
Specifically, this json should have an `action` key (with the name of the tool to use) and an `action_input` key (with the input to the tool going here).

The only values that should be in the "action" field are:
{tool_descriptions_action}
example use :
{example_use}

ALWAYS use the following format:

Thought: you should always think about one action to take. Only one action at a time in this format:
Action:

$JSON_BLOB (inside markdown cell)

Observation: the result of the action. This Observation is unique, complete, and the source of truth.
... (this Thought/Action/Observation can repeat N times, you should take several steps when needed. The $JSON_BLOB must be formatted as markdown and only use a SINGLE action at a time.)

You must always end your output with the following format:

Thought: I now know the final answer
Final Answer: the final answer to the original input question

Now begin! Reminder to ALWAYS use the exact characters `Final Answer:` when you provide a definitive answer. """


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def tool_node(state: AgentState):
    tools = {
        "get_earnings_data": get_earnings_data,
        "get_finance_news": get_finance_news,
        "get_stock_price": get_stock_price,
        "get_technical_indicators": get_technical_indicators,
        "get_order_book": get_order_book,
        "capture_screenshot": capture_screenshot,
        "describe_image": describe_image,
        "get_financials": get_income_statement_from_edgar,
        "parse_income_statement": parse_income_statement
    }

    last_message = state["messages"][-1].content
    filtered_messages = [msg for msg in state["messages"] if isinstance(msg, (HumanMessage, SystemMessage))]

    try:
        
        tool_result = extract_action(last_message)
        tool_name = tool_result["action"]
        tool_args = tool_result["action_input"]

        print(f"Executing tool: {tool_name} with args: {tool_args}")

        if tool_name not in tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # result = tools[tool_name](tool_args)
        if tool_name == "get_financials":
            ticker = tool_args["tickers"][0]
            result = tools[tool_name](ticker)
        else:
            result = tools[tool_name](tool_args)
        ai_answer = f"Observation: {result}"
        filtered_messages = [AIMessage(content=ai_answer)]

    except Exception as e:
        print(f"Error executing tool: {e}")
        filtered_messages = [AIMessage(content=f"Observation: Error - {str(e)}")]

    return {"messages": filtered_messages}


def is_final_asnwer_node(state: AgentState) -> bool:
    """
    Check if the last message in the conversation contains a final answer.
    
    Returns:
        bool: True if the last message contains 'Final Answer:', False otherwise
    """
    last_message = state["messages"][-1]
    
    if "Final Answer:" in last_message.content:
        return "end"
    return 'tools'


def extract_action(content: str) -> dict:
    import re, json

    # Try to extract JSON from markdown or raw content
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        json_blob = match.group(1)
    else:
        # Remove any trailing comments, whitespace, or text
        json_blob = content.strip().split("\n")[0] if content.strip().startswith("{") else content.strip()

    try:
        return json.loads(json_blob)
    except json.JSONDecodeError as e:
        raise ValueError("Could not parse action JSON: " + str(e))



def assistant(state: AgentState):
    # System message
    tool_descriptions = """
    get_earnings_data(input: dict) -> dict:
        Fetches the most recent annual earnings for a list of S&P 500 companies.
        Input should be: {"tickers": ["AAPL", "MSFT", "GOOGL", ...]}

    get_finance_news(input: dict) -> list:
        Searches recent financial news using NewsData.io.
        Input: {"query": "Nvidia earnings", "max_results": 5}

    get_stock_price(input: dict) -> dict:
        Fetches the latest stock price, open price, volume, and change for a given ticker symbol.
        Input: {"ticker": "NVDA"}

    get_technical_indicators(input: dict) -> dict:
        Fetches the technical indicators for a given ticker symbol.
        Input: {"ticker": "NVDA"}

    get_order_book(input: dict) -> dict:
        Retrieves top N bid/ask levels from Binance for a crypto symbol.
        Input: {"symbol": "BTCUSDT", "depth": 5}

    capture_screenshot(input: dict) -> dict:
        Takes a screenshot of the current screen and returns the image encoded in base64.
        Input: {}

    describe_image(input: dict) -> dict:
        Sends an image to GPT-4 Vision and returns its description.
        Input should include either:
        - 'image_path': str (path to image file)
        - or 'image_bytes': raw bytes
        - optionally: 'prompt': str

    get_financials(tickers: List[str]) -> Dict:
        Retrieves financial data for the given list of ticker symbols.
        Attempts to pull the latest EDGAR filing (10-K), extract an income statement from it,
        and fallbacks to Yahoo Finance if EDGAR is unavailable or incomplete.

    parse_income_statement(raw_data: str, ticker: str) -> dict:
        Parses the raw EDGAR financials financial statements into a dictionary for the given ticker.
    """

    # Tool format for LLM
    tool_descriptions_action = """
    get_earnings_data: Get earnings summaries for companies, args: {
      "tickers": ["AAPL", "MSFT", "GOOGL"]
    }
    
    get_finance_news: {
    "query": "Nvidia earnings",
    "max_results": 5
    }

    get_stock_price: {
    "ticker": "NVDA"
    }

    get_technical_indicators: {
    "ticker": "NVDA"
    }

    get_order_book: Get order book for a crypto asset, args: {
    "symbol": "BTCUSDT",
    "depth": 5
    }

    capture_screenshot: Capture current screen and return base64-encoded image, args: {}

    describe_image: Describe an image using GPT-4 Vision, args: {
    "image_path": "screenshot.png",
    "prompt": "Explain what's in this screenshot"
    }

    get_financials: Fetch financial data for one or more companies. 
    args: {
        "tickers": [str]  # List of ticker symbols, e.g. ["AAPL", "TSLA", "ZTNO"]
    }

    parse_income_statement: Parse the raw financials data.
    args: {
        "raw_data": "...the raw EDGAR text..."
        "ticker": AAPL
    }
    """

    example_use = """Examples:

    1. Get earnings data:
    {
    "action": "get_earnings_data",
    "action_input": {
        "tickers": ["AAPL", "MSFT", "GOOGL"]
    }
    }

    2. Scrape for finance news:
    {
    "action": "get_finance_news",
    "action_input": {
        "query": "Nvidia earnings",
        "max_results": 3
    }
    }

    3. Get the stock prices:
    {
    "action": "get_stock_price",
    "action_input": {
        "ticker": "NVDA"
    }
    }

    4. Get the technical indicators:
    {
    "action": "get_technical_indicators",
    "action_input": {
        "ticker": "NVDA"
    }
    }

    5.
    {
    "action": "get_order_book",
    "action_input": {
        "symbol": "ETHUSDT",
        "depth": 10
    }
    }
    

    {
    "action": "capture_screenshot",
    "action_input": {}
    }

    {
    "action": "describe_image",
    "action_input": {
        "image_path": "screenshot.png",
        "prompt": "What do you see?"
    }
    }

    {
    "action": "get_financials",
    "action_input": {
        "ticker_or_cik": "AAPL"
    }
    }

    {
    "action": "parse_income_statement",
    "action_input": {
        "raw_text": "...the raw EDGAR text...",
        "ticker": Company Ticker
    }
    }
    """

    
    sys_msg = SystemMessage(content=SYSTEM_PROMPT.format(
    tool_descriptions=tool_descriptions,
    tool_descriptions_action=tool_descriptions_action,
    example_use=example_use
))
    
    response = llm.invoke([sys_msg] + state["messages"])
    return {"messages": [response]} 




# Build the math graph
graph = StateGraph(AgentState)

# Define nodes
graph.add_node("assistant", assistant)
graph.add_node("tools", tool_node)

# Define edges
graph.add_edge(START, "assistant")
graph.add_conditional_edges(
    "assistant",
    is_final_asnwer_node,
    {"tools": "tools", "end": END}
)

graph.add_edge("tools", "assistant")

repair_shop_agent = graph.compile(name="repair_shop_agent")
display(Image(repair_shop_agent.get_graph(xray=True).draw_mermaid_png()))


ticker = sys.argv[1] if len(sys.argv) > 1 else None
if not ticker:
    print("Usage: python cli.py <TICKER>")
    sys.exit(1)

prompt = f"Do the following: 1) Can you pull the latest income statements for {ticker}? 2) Parse the income statements."

all_chunks = []
for chunk in repair_shop_agent.stream(
    {"messages": [{"role": "user", "content": prompt}]} 
):
    all_chunks.append(chunk)
    
    # Stream and print the assistant's response as it comes
    pretty_print_messages(chunk)


# Optional: print final full message content if needed
final_response = None
for chunk in reversed(all_chunks):
    if "messages" in chunk and chunk["messages"]:
        final_response = chunk["messages"][-1].content
        break

if final_response:
    print("\nFinal Response:")
    print(final_response)
else:
    print("No valid assistant response found.")

