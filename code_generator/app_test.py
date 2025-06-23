import streamlit as st
from langchain.schema import AIMessage, HumanMessage
from langchain.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import os

### Observability Langsmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ["LANGCHAIN_PROJECT"] = "App-Test-Chatbot"

# -------- CONFIGURE YOUR GROQ API KEY AND MODEL --------
GROQ_API_KEY = ""
GROQ_API_URL = "https://api.groq.com/openai/v1"
MODEL_NAME = "llama-3.1-8b-instant"





# -------- LANGCHAIN WRAPPER FOR GROQ --------
class GroqChatModel(ChatOpenAI):
    def __init__(self, **kwargs):
        super().__init__(openai_api_key=GROQ_API_KEY,
                         base_url=GROQ_API_URL,
                         model=MODEL_NAME,
                         **kwargs)

# -------- STATE TYPE FOR LANGGRAPH --------
class ChatState(TypedDict):
    messages: List
    user_input: str

# -------- NODES --------
def input_handler_node(state: ChatState) -> ChatState:
    return state

def llm_node(state: ChatState) -> ChatState:
    print("User said:", state["user_input"])  # Optional debug log
    chat = GroqChatModel(temperature=0.7)
    response = chat(state["messages"])
    state["messages"].append(response)
    return state

# -------- LANGGRAPH FLOW --------
graph = StateGraph(ChatState)
graph.add_node("input_handler", input_handler_node)  # Renamed node
graph.add_node("llm", llm_node)
graph.set_entry_point("input_handler")
graph.add_edge("input_handler", "llm")
graph.add_edge("llm", END)
compiled_graph = graph.compile()

# -------- STREAMLIT UI --------
st.title("🤖 LangGraph + Groq Chatbot")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_query = st.text_input("You:", key="input")
submit = st.button("Send")

if submit and user_query:
    # Prepare state for LangGraph
    chat_state = {
        "messages": st.session_state.chat_history + [HumanMessage(content=user_query)],
        "user_input": user_query,
    }

    # Run through LangGraph
    final_state = compiled_graph.invoke(chat_state)

    # Update memory
    st.session_state.chat_history = final_state["messages"]

# Show full chat
if not st.session_state.chat_history:
    st.info("Start chatting by typing a message above and clicking Send!")

for msg in st.session_state.chat_history:
    role = "You" if isinstance(msg, HumanMessage) else "AI"
    st.markdown(f"**{role}:** {msg.content}")

if st.button("Reset Chat"):
    st.session_state.chat_history = []
