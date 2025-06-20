from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime
import requests


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class UserInfo(BaseModel):
    name: str
    email: str
    phone: str

class ChatMessage(BaseModel):
    message: str
    user_info: UserInfo

class ChatResponse(BaseModel):
    response: str
    recommendations: List[str] = []

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_data: ChatMessage):
    try:
        # Get HF API key from environment
        hf_api_key = os.environ.get('HF_API_KEY')
        if not hf_api_key:
            raise HTTPException(status_code=500, detail="Hugging Face API key not configured")
        
        # Save user info and message to database
        user_message = {
            "id": str(uuid.uuid4()),
            "user_info": chat_data.user_info.dict(),
            "message": chat_data.message,
            "timestamp": datetime.utcnow()
        }
        await db.chat_messages.insert_one(user_message)
        
        # Prepare the context for premium reduction advice
        context = f"""You are a crypto insurance AI advisor helping users reduce their insurance premiums. 
        The user {chat_data.user_info.name} is asking: {chat_data.message}
        
        Provide helpful advice about:
        1. Security best practices that can reduce premium costs
        2. Risk assessment for their crypto holdings
        3. Insurance coverage recommendations
        4. Specific actionable steps to lower their risk profile
        
        Keep responses concise and actionable. Focus on premium reduction strategies."""
        
        # Call Hugging Face API
        headers = {
            "Authorization": f"Bearer {hf_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": context,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        # Using a good conversational model
        hf_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-large"
        
        response = requests.post(hf_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            # Fallback response if HF API fails
            ai_response = f"Hello {chat_data.user_info.name}! I'm here to help you reduce your crypto insurance premiums. Based on your question about '{chat_data.message}', I recommend focusing on improving your security setup. Would you like specific advice on hardware wallets, 2FA setup, or DeFi risk management?"
            recommendations = [
                "Use a hardware wallet (40% premium reduction)",
                "Enable 2FA on all accounts (15% reduction)",
                "Regular security audits (10% reduction)"
            ]
        else:
            result = response.json()
            ai_response = result[0]["generated_text"] if result else f"Hello {chat_data.user_info.name}! I'm here to help you lower your premium costs. What specific crypto security concerns do you have?"
            
            # Generate recommendations based on common premium reduction strategies
            recommendations = [
                "Hardware wallet usage can reduce premiums by up to 40%",
                "Multi-factor authentication saves 15% on premiums",
                "Cold storage practices offer additional discounts",
                "Regular portfolio rebalancing towards stablecoins reduces risk"
            ]
        
        # Save AI response to database
        ai_message = {
            "id": str(uuid.uuid4()),
            "user_id": user_message["id"],
            "response": ai_response,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow()
        }
        await db.ai_responses.insert_one(ai_message)
        
        return ChatResponse(response=ai_response, recommendations=recommendations)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()