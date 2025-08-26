# Financial-Data-Agent

This project demonstrates an **Agentic AI** framework for fetching and processing financial data from EDGAR.


- **OpenAI Client** as the driving LLM for the agent. 
- **LangGraph** for creating the agentic framework and connecting the assistant agent to the tools.

---

## TOOLS:

- Fetch financial statements using EDGAR API.
- Fetch earnings data for the given ticker.
- Get financial news regarding the desired ticker.
- Get stock prices and technical indicators.
- Get order book information.
- Capture screenshot and describe the image.
- Parse the financial data and save into CSV.

---

## Project Structure

```
Financial-Data-Agent/
├── Agent.py # Main file for interaction with the agent and tools.
├── extract_EDGAR_tool.py # Tool for accessing financial statements using EDGAR API.
├── financial_tools.py # Contains all financial processing tools and stock price, order book, etc.
├── image_description_tool.py # Takes a screenshot of a website and passes it to a VLLM for description. (i.e. take screenshot of a price graph).
├── print_messages.py # print the messages comming from the Agent and format them in a readable way.
└── README.md
```

---

## Requirements

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

---

## 1. Interact with the agent

Call the Agent.py and pass in the ticker to obtain the financial statements and parse the data.

```bash
python Agent.py AAPL
```

---

