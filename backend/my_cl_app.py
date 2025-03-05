import os
import json
import requests
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import declarative_base

import chainlit as cl
import chainlit.socket
from chainlit.session import WebsocketSession
from chainlit.user_session import user_sessions
from chainlit.telemetry import trace_event
from chainlit.types import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from db.models import Base, User
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Log to stdout for Docker logs
)
logger = logging.getLogger('runx-chatbot')

# Load environment variables
load_dotenv()

# Database connection with error handling
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set. Exiting...")
    sys.exit(1)

try:
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Database engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database engine: {str(e)}")
    sys.exit(1)

# Function to get the data layer
@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo=DATABASE_URL)

# Authentication API endpoint
AUTH_API_URL = os.environ.get("AUTH_API_URL")
if not AUTH_API_URL:
    logger.warning("AUTH_API_URL not set. Authentication might fail.")

# Custom function to resume a thread and ensure metadata is a dictionary
async def custom_resume_thread(session: WebsocketSession):
    data_layer = get_data_layer()
    if not data_layer or not session.user or not session.thread_id_to_resume:
        return
    
    thread = await data_layer.get_thread(thread_id=session.thread_id_to_resume)
    if not thread:
        return

    author = thread.get("userIdentifier")
    user_is_author = author == session.user.identifier

    if user_is_author:
        metadata = thread.get("metadata") or {}
        logger.info(f"Session ID: {session.id}")
        logger.info(f"Metadata: {metadata}")
        logger.info(f"Metadata Type: {type(metadata)}")

        # Ensure metadata is always a dictionary
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)  # Convert JSON string to dict
                logger.info("Successfully parsed metadata JSON string to dict")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metadata as JSON: {metadata}")
                metadata = {}  # Default to empty dict on error

        user_sessions[session.id] = metadata.copy()

        if chat_profile := metadata.get("chat_profile"):
            session.chat_profile = chat_profile
        if chat_settings := metadata.get("chat_settings"):
            session.chat_settings = chat_settings

        trace_event("thread_resumed")
        return thread

# Override Chainlit's resume_thread with the custom function
chainlit.socket.resume_thread = custom_resume_thread

# User authentication callback with improved error handling
@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    try:
        async with AsyncSessionLocal() as session:
            payload = {"email": username, "password": password}
            
            try:
                response = requests.post(AUTH_API_URL, json=payload, timeout=10)  # Add timeout for Docker networking
            except requests.exceptions.RequestException as e:
                logger.error(f"Authentication API request failed: {str(e)}")
                return None
        
            if response.status_code == 201:
                user_data = response.json()
                profile = user_data.get("profile", {})
                
                user_id = profile.get("id")
                user_name = profile.get("name", "Unknown")
                token = user_data.get("token")
                
                logger.info(f"User authenticated: {user_name} (ID: {user_id})")

                # Check if user exists in the database
                try:
                    result = await session.execute(select(User).filter(User.identifier == username))
                    user = result.scalars().first()
                    
                    if not user:
                        logger.info(f"Creating new user in database: {username}")
                        new_user = User(
                            identifier=username,
                            metadata_={"name": user_name, "id": user_id, "token": token, "provider": "api"},
                        )
                        session.add(new_user)
                        await session.commit()
                        user = new_user
                    else:
                        logger.info(f"User found in database: {username}")
                        # Ensure metadata is a dictionary
                        if isinstance(user.metadata_, str):
                            user.metadata_ = json.loads(user.metadata_)

                    return cl.User(identifier=user.identifier, metadata=user.metadata_)
                except Exception as e:
                    logger.error(f"Database operation failed during authentication: {str(e)}")
                    await session.rollback()
                    return None
            else:
                logger.warning(f"Authentication failed with status code: {response.status_code}")
                return None  # Authentication failed
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        return None

# Event triggered when a new chat starts
# @cl.on_chat_start
# async def on_chat_start():
#     cl.user_session.set("chat_history", [])
#     logger.info("New chat session started")
#     await cl.Message(content="Welcome to RunX Healthcare Chatbot!!!").send()

# Event triggered when a user resumes a chat
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    cl.user_session.set("chat_history", [])
    
    message_count = 0
    for message in thread["steps"]:
        if message["type"] == "user_message":
            cl.user_session.get("chat_history").append({"role": "user", "content": message["output"]})
            message_count += 1
        elif message["type"] == "assistant_message":
            cl.user_session.get("chat_history").append({"role": "assistant", "content": message["output"]})
            message_count += 1
    
    logger.info(f"Chat resumed with {message_count} previous messages")

# Event triggered when a user sends a message
@cl.on_message
async def on_message(message: cl.Message):
    chat_history = cl.user_session.get("chat_history")
    chat_history.append({"role": "user", "content": message.content})
    logger.info(f"Received user message: {message.content[:50]}...")

    # Add system prompt at the beginning of the chat if not present
    system_prompt = {
        "role": "system",
        "content": """  
            "You are RunX Healthcare Chatbot, an AI assistant specialized in health-related topics. "
            "Your role is to provide guidance on wellness, sleep, exercise, and nutrition. "
            "For any non-health-related questions, provide a brief response and redirect the user to stay on topic. "
            "You are not a doctor and cannot provide medical diagnoses or prescriptions."

## 🔹 Rules & Guidelines:
1️⃣ **Health & Wellness Focus**:
   - Provide high-quality responses related to physical and mental health, nutrition, fitness, sleep, and general well-being.
   - Offer scientifically backed advice where possible but remind users to consult a medical professional for serious concerns.

2️⃣ **Handling Medical Advice**:
   - You are **not a doctor** and cannot diagnose, prescribe medication, or provide medical treatments.
   - If a user asks about a medical emergency or specific condition, **encourage them to consult a healthcare professional**.

3️⃣ **Encouraging Healthy Habits**:
   - Promote **healthy lifestyles**, including balanced diets, regular exercise, good sleep hygiene, and stress management.
   - Provide practical and **motivational advice** on maintaining these habits.

4️⃣ **Handling Off-Topic Queries**:
   - If a question is **not related to healthcare**, respond **politely but briefly**, encouraging the user to stay on health-related topics.
   - Example:
     - ❌ User: "Tell me about the stock market."
     - ✅ Bot: "I'm here to assist with healthcare topics! However, you can find stock market insights from a financial expert."

5️⃣ **Respect & Empathy**:
   - Maintain a **calm, professional, and supportive** tone.
   - Be respectful and encourage **positive mental health awareness**.

6️⃣ **Confidentiality & Ethical AI**:
   - Do not store or retain **personal health data**.
   - Avoid sharing **sensitive** or **personalized** medical advice.

## 🔹 Examples of Allowed Topics:
✅ **"How can I improve my sleep?"**  
✅ **"What are some healthy meal ideas?"**  
✅ **"How much exercise should I do daily?"**  

## 🔹 Topics to Avoid or Handle Briefly:
❌ **"How do I invest in crypto?"** → "I specialize in healthcare topics! Please check with a financial expert."  
❌ **"Can you diagnose my symptoms?"** → "I'm not a doctor, and I recommend consulting a healthcare professional for accurate diagnosis."  
❌ **"What's the best car to buy?"** → "I focus on health advice! For car recommendations, consider a vehicle expert."
        """
    }
    
    if not any(msg["role"] == "system" for msg in chat_history):
        chat_history.insert(0, system_prompt)
        logger.info("Added system prompt to chat history")

    # Fetch OpenAI API key from environment variables
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        await cl.Message(content="Error: LLM API key not found in environment variables").send()
        return
    
    try:
        client = OpenAI(api_key=openai_api_key)
        logger.info("Sending request to OpenAI API")
        
        chat_response = client.chat.completions.create(
            model="gpt-4o",
            messages=chat_history,
            timeout=25,
        )
        
        response_content = chat_response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": response_content})
        logger.info(f"Received response from OpenAI API: {response_content[:50]}...")
        
        await cl.Message(content=response_content).send()
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        await cl.Message(content=f"I apologize, but I encountered an error while processing your request. Please try again later.").send()

# Add health check for Docker
@cl.on_chat_start
async def health_check():
    # Initialize chat history
    cl.user_session.set("chat_history", [])
    logger.info("New chat session started")
    
    # Run health checks
    try:
        # Check database connection
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            row =  result.fetchone()
            logger.info("Database connection verified on startup")
            
        # Verify OpenAI API key exists
        if os.environ.get("OPENAI_API_KEY"):
            logger.info("OpenAI API key verified")
        else:
            logger.warning("OpenAI API key missing")
            
        logger.info("Health check complete - service ready")
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
    
    # Send welcome message
    await cl.Message(content="Welcome to RunX Healthcare Chatbot!!!").send()