import os
import json
import pandas as pd
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY") or ""


def build_agent(df: pd.DataFrame):
    """Build an agent for a given DataFrame."""

    # --- 1) Defining tools (bound to this dataframe)
    @tool
    def schema(dummy: str) -> str:
        """Gives columns name and data types in json"""
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        return json.dumps(schema)

    @tool
    def nulls(dummy: str) -> str:
        """Gives columns with the number of missing values as json"""
        nulls = df.isna().sum()
        result = {col: int(n) for col, n in nulls.items() if n > 0}
        return json.dumps(result)

    @tool
    def describe(input_str: str) -> str:
        """Returns describe() statistics.
        Optional: input_str can contain a comma-separated list of columns, e.g. "age, fare".
        """
        cols = None
        if input_str and input_str.strip():
            cols = [c.strip() for c in input_str.split(",") if c.strip() in df.columns]
        stats = df[cols].describe() if cols else df.describe()
        return stats.to_string()

    tools = [schema, nulls, describe]

    # --- 2) Configure LLM
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)

    # --- 3) Prompt
    SYSTEM_PROMPT = (
        "You are a data-focused assistant. "
        "If a question requires information from the CSV, first use an appropriate tool. "
        "Use only one tool call per step if possible. "
        "Answer concisely and in a structured way. "
        "If no tool fits, briefly explain why.\n\n"
        "Available tools:\n{tools}\n"
        "Use only these tools: {tool_names}."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    _tool_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    _tool_names = ", ".join(t.name for t in tools)
    prompt = prompt.partial(tools=_tool_desc, tool_names=_tool_names)

    # --- 4) Create agent
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=3)

    def ask_agent(query: str) -> str:
        return agent_executor.invoke({"input": query})["output"]

    return ask_agent


# Demo usage if run directly
if __name__ == "__main__":
    csv_file = "titanic.csv"
    df = pd.read_csv(csv_file)
    ask_agent = build_agent(df)
    result = ask_agent("Which columns have missing values? List 'Column: Count'.")
    print("\n=== AGENT ANSWER ===")
    print(result)
