import os,json
import pandas as  pd
from dotenv import load_dotenv
load_dotenv()
DF_PATH = "titanic.csv"
df = pd.read_csv(DF_PATH)

# --- 1) Defining tools 
from langchain_core.tools import tool

@tool
def schema(dummy: str)-> str:
    """Gives columns name and data types in json """
    schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
    return json.dumps(schema)

@tool
def nulls(dummy:str)->str:
    """Gives columns with the number of missing values as json"""
    nulls = df.isna().sum()
    result = {col: int(n) for col, n in nulls.items() if n > 0}
    return json.dumps(result)

@tool
def desccribe(input_str:str)->str:
    """Returns describe() statistics.
    Optional: input_str can contain a comma-separated list of columns, e.g. "age, fare".
    """
    cols = None
    if input_str and input_str.strip():
        cols = [c.strip() for c in input_str.split(",") if c.strip() in df.columns]
    stats = df[cols].describe() if cols else df.describe()
    return stats.to_string()

# --- 2) Registering tools
tools = [schema, nulls, desccribe]


# --- 3) confifure LLM
from langchain_groq import ChatGroq
os.environ["GROQ_API_KEY"]=os.getenv("GROQ_API_KEY") or ""
llm=ChatGroq(model="llama-3.3-70b-versatile",temperature=0.1)


# --- 4) Narrow Prompt (Agent Behavior)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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

# --- 5) Create & Run Tool-Calling Agent ---
from langchain.agents import create_tool_calling_agent, AgentExecutor

agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,   # optional: True for debug logs
    max_iterations=3,
)

def ask_agent(query: str) -> str:
    return agent_executor.invoke({"input": query})["output"]

if __name__ == "__main__":
    user_query = "Which columns have missing values? List 'Column: Count'."
    result = agent_executor.invoke({"input": user_query})
    print("\n=== AGENT ANSWER ===")
    print(result["output"])

