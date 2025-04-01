from typing import Dict, List, Tuple, Any, TypedDict, Annotated, Sequence
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.prompts import MessagesPlaceholder
from langchain.schema import AgentAction, AgentFinish
import operator
from typing import Union, List, Dict, Any
import json

# Define our state
class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]
    current_step: str
    memory: Dict[str, Any]
    summary: str
    human_input: str

# Initialize memories
short_term_memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

long_term_memory = ConversationSummaryMemory(
    memory_key="summary",
    return_messages=True,
    llm=ChatOpenAI(temperature=0)
)

# Create the agent nodes
def create_agent_node(agent_type: str):
    """Create an agent node based on the type."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a {agent_type} agent. Use the provided tools and memory to help with the task."),
        MessagesPlaceholder(variable_name="chat_history"),
        MessagesPlaceholder(variable_name="summary"),
        ("human", "{input}")
    ])
    
    llm = ChatOpenAI(temperature=0)
    
    # Define tools based on agent type
    tools = [
        Tool(
            name="summarize",
            func=lambda x: long_term_memory.predict_new_summary(x, x),
            description="Summarize the current conversation"
        ),
        Tool(
            name="store_memory",
            func=lambda x: short_term_memory.save_context({"input": x}, {"output": ""}),
            description="Store information in short-term memory"
        )
    ]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# Create the human-in-the-loop node
def human_in_loop(state: AgentState) -> AgentState:
    """Handle human interaction in the loop."""
    print("\nCurrent state:", state["current_step"])
    print("\nSummary of conversation:", state["summary"])
    print("\nLast messages:", state["messages"][-3:] if len(state["messages"]) > 3 else state["messages"])
    
    human_input = input("\nYour input (or 'continue' to proceed): ")
    if human_input.lower() == 'continue':
        return state
    
    state["human_input"] = human_input
    state["messages"].append(HumanMessage(content=human_input))
    return state

# Create the memory management node
def manage_memory(state: AgentState) -> AgentState:
    """Manage both short-term and long-term memory."""
    # Update short-term memory
    if state["messages"]:
        short_term_memory.save_context(
            {"input": state["messages"][-1].content},
            {"output": ""}
        )
    
    # Update long-term memory summary
    if len(state["messages"]) >= 3:
        state["summary"] = long_term_memory.predict_new_summary(
            state["messages"][-3:],
            state["messages"][-3:]
        )
    
    return state

# Create the main graph
def create_agent_graph(agent_type: str) -> Graph:
    """Create the main LangGraph flow."""
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("human", human_in_loop)
    workflow.add_node("agent", create_agent_node(agent_type))
    workflow.add_node("memory", manage_memory)
    
    # Add edges
    workflow.add_edge("human", "agent")
    workflow.add_edge("agent", "memory")
    workflow.add_edge("memory", "human")
    
    # Set entry point
    workflow.set_entry_point("human")
    
    # Compile the graph
    return workflow.compile()

# Example usage
def run_agent_flow(agent_type: str = "research"):
    """Run the agent flow with the specified agent type."""
    # Initialize the graph
    graph = create_agent_graph(agent_type)
    
    # Initialize the state
    initial_state = {
        "messages": [],
        "current_step": "start",
        "memory": {},
        "summary": "",
        "human_input": ""
    }
    
    # Run the graph
    for state in graph.stream(initial_state):
        if state["current_step"] == "end":
            break

if __name__ == "__main__":
    run_agent_flow() 