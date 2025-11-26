from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
from dotenv import load_dotenv

load_dotenv()


class AgentState(TypedDict):
    messages: list[BaseMessage]
    user_input: str
    selected_option: str | None
    journey_name: str | None
    conversation_step: str
    document_type: str | None
    existing_journeys: list[str] | None


# Initialize OpenRouter LLM via LangChain
def get_llm():
    """Lazy load LLM to ensure env vars are loaded"""
    return ChatOpenAI(
        model=os.getenv("DEFAULT_MODEL", "openrouter/bert-nebulon-alpha"),
        # model=os.getenv("DEFAULT_MODEL"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_BASE_URL"),
        temperature=0.7
    )


@tool
def get_existing_journeys() -> list[str]:
    """Get list of existing journey folders from the documents directory."""
    base_path = "documents/journeys"
    if not os.path.exists(base_path):
        return []
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]


def chatbot_agent_node(state: AgentState):
    """LangChain-powered chatbot agent for natural conversation handling"""
    
    llm = get_llm()
    conversation_step = state.get("conversation_step", "initial")
    user_input = state.get("user_input", "").strip()
    messages = state.get("messages", [])
    
    # Create agent with tools
    tools = [get_existing_journeys]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are TraceQA assistant, a helpful and friendly document management chatbot.
Your role is to guide users through managing journeys and their documents.
Be professional, clear, and concise in your responses.

IMPORTANT FORMATTING RULES:
- Use clear headings and bullet points where appropriate
- Keep responses well-structured and easy to read
- Use numbered lists for options (1., 2., etc.)
- Add appropriate spacing between sections
- Be conversational yet professional

Always remind users they can type 'cancel' or 'exit' at any time to restart the conversation.

Current conversation step: {conversation_step}
Journey name (if set): {journey_name}
Document type (if set): {document_type}
"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    
    # Route based on conversation step
    
    # Check for cancel/exit commands
    if user_input.lower() in ["cancel", "exit", "quit", "restart"]:
        result = agent_executor.invoke({
            "input": "User wants to restart. Acknowledge their request and present the main menu options again.",
            "chat_history": [],
            "conversation_step": "initial",
            "journey_name": None,
            "document_type": None
        })
        return {
            "messages": [AIMessage(content=result["output"])],
            "user_input": "",
            "selected_option": None,
            "journey_name": None,
            "conversation_step": "awaiting_option",
            "document_type": None,
            "existing_journeys": None
        }
    
    if conversation_step == "initial":
        result = agent_executor.invoke({
            "input": "Greet the user warmly and present them with two well-formatted options:\n1. Add a journey (e.g., POS, Inventory Management, etc.)\n2. New document under an existing journey (updates like annextures, addendums, emails, etc.)\n\nAsk them to enter 1 or 2. Also mention they can type 'cancel' or 'exit' at any time to restart.",
            "chat_history": messages,
            "conversation_step": conversation_step,
            "journey_name": state.get("journey_name"),
            "document_type": state.get("document_type")
        })
        
        return {
            **state,
            "messages": messages + [AIMessage(content=result["output"])],
            "conversation_step": "awaiting_option"
        }
    
    elif conversation_step == "awaiting_option":
        if user_input == "1":
            result = agent_executor.invoke({
                "input": "User wants to create a new journey. Ask them for the journey name in a friendly way.",
                "chat_history": messages,
                "conversation_step": conversation_step,
                "journey_name": state.get("journey_name"),
                "document_type": state.get("document_type")
            })
            return {
                **state,
                "messages": messages + [AIMessage(content=result["output"])],
                "selected_option": "1",
                "conversation_step": "awaiting_journey_name"
            }
        elif user_input == "2":
            journeys = get_existing_journeys.invoke({})
            if not journeys:
                result = agent_executor.invoke({
                    "input": "No existing journeys found. Politely tell the user to create a journey first by selecting option 1.",
                    "chat_history": messages,
                    "conversation_step": conversation_step,
                    "journey_name": state.get("journey_name"),
                    "document_type": state.get("document_type")
                })
                return {
                    **state,
                    "messages": messages + [AIMessage(content=result["output"])],
                    "conversation_step": "initial"
                }
            
            journey_list = "\n".join([f"{i+1}) {j}" for i, j in enumerate(journeys)])
            result = agent_executor.invoke({
                "input": f"Show the user these existing journeys in a clean, numbered format:\n\n{journey_list}\n\nAsk them to select by entering the number. Remind them they can type 'cancel' to go back.",
                "chat_history": messages,
                "conversation_step": conversation_step,
                "journey_name": state.get("journey_name"),
                "document_type": state.get("document_type")
            })
            
            return {
                **state,
                "messages": messages + [AIMessage(content=result["output"])],
                "selected_option": "2",
                "conversation_step": "awaiting_journey_selection",
                "existing_journeys": journeys
            }
        else:
            result = agent_executor.invoke({
                "input": f"User entered '{user_input}' which is invalid. Politely ask them to enter 1 or 2 only.",
                "chat_history": messages,
                "conversation_step": conversation_step,
                "journey_name": state.get("journey_name"),
                "document_type": state.get("document_type")
            })
            return {
                **state,
                "messages": messages + [AIMessage(content=result["output"])],
                "conversation_step": "awaiting_option"
            }
    
    elif conversation_step == "awaiting_journey_name":
        result = agent_executor.invoke({
            "input": f"User wants to create a journey named '{user_input}'. Confirm the journey creation and ask them to upload a PDF document.",
            "chat_history": messages,
            "conversation_step": conversation_step,
            "journey_name": user_input,
            "document_type": state.get("document_type")
        })
        return {
            **state,
            "messages": messages + [AIMessage(content=result["output"])],
            "journey_name": user_input,
            "conversation_step": "awaiting_document_upload"
        }
    
    elif conversation_step == "awaiting_journey_selection":
        journeys = state.get("existing_journeys", [])
        try:
            selection = int(user_input) - 1
            if 0 <= selection < len(journeys):
                selected_journey = journeys[selection]
                result = agent_executor.invoke({
                    "input": f"User selected journey '{selected_journey}'. Show them these document type options in a clean format:\n\n1. Addendum\n2. Annexture\n3. Email\n4. Other\n\nAsk them to select by entering the number (1-4). Remind them they can type 'cancel' to go back.",
                    "chat_history": messages,
                    "conversation_step": conversation_step,
                    "journey_name": selected_journey,
                    "document_type": state.get("document_type")
                })
                
                return {
                    **state,
                    "messages": messages + [AIMessage(content=result["output"])],
                    "journey_name": selected_journey,
                    "conversation_step": "awaiting_document_type"
                }
        except:
            pass
        
        result = agent_executor.invoke({
            "input": "User entered an invalid selection. Politely ask them to enter a valid number from the list.",
            "chat_history": messages,
            "conversation_step": conversation_step,
            "journey_name": state.get("journey_name"),
            "document_type": state.get("document_type")
        })
        return {
            **state,
            "messages": messages + [AIMessage(content=result["output"])],
            "conversation_step": "awaiting_journey_selection"
        }
    
    elif conversation_step == "awaiting_document_type":
        type_map = {"1": "addendum", "2": "annexture", "3": "email", "4": "other"}
        doc_type = type_map.get(user_input)
        
        if doc_type:
            result = agent_executor.invoke({
                "input": f"User selected document type '{doc_type}'. Confirm the selection and ask them to upload their PDF document.",
                "chat_history": messages,
                "conversation_step": conversation_step,
                "journey_name": state.get("journey_name"),
                "document_type": doc_type
            })
            return {
                **state,
                "messages": messages + [AIMessage(content=result["output"])],
                "document_type": doc_type,
                "conversation_step": "awaiting_document_upload"
            }
        else:
            result = agent_executor.invoke({
                "input": "User entered an invalid option. Politely ask them to enter 1, 2, 3, or 4 only.",
                "chat_history": messages,
                "conversation_step": conversation_step,
                "journey_name": state.get("journey_name"),
                "document_type": state.get("document_type")
            })
            return {
                **state,
                "messages": messages + [AIMessage(content=result["output"])],
                "conversation_step": "awaiting_document_type"
            }
    
    elif conversation_step == "document_uploaded":
        # After document upload, restart conversation
        result = agent_executor.invoke({
            "input": "The document has been uploaded and test cases are being generated. Thank the user and ask what they'd like to do next:\n\n1. Add another journey\n2. Add another document to an existing journey\n\nRemind them they can type 'cancel' or 'exit' at any time.",
            "chat_history": messages,
            "conversation_step": conversation_step,
            "journey_name": state.get("journey_name"),
            "document_type": state.get("document_type")
        })
        return {
            **state,
            "messages": messages + [AIMessage(content=result["output"])],
            "conversation_step": "awaiting_option"
        }
    
    return state


def create_orchestrator_graph():
    """Create the LangGraph orchestrator with LangChain agent nodes"""
    
    workflow = StateGraph(AgentState)
    
    # Add chatbot agent node
    workflow.add_node("chatbot", chatbot_agent_node)
    
    # Set entry point
    workflow.set_entry_point("chatbot")
    
    # End after chatbot processes
    workflow.add_edge("chatbot", END)
    
    return workflow.compile()
