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
        # Save user info and message to database
        user_message = {
            "id": str(uuid.uuid4()),
            "user_info": chat_data.user_info.dict(),
            "message": chat_data.message,
            "timestamp": datetime.utcnow()
        }
        await db.chat_messages.insert_one(user_message)
        
        # Initialize variables
        user_name = chat_data.user_info.name
        
        # Handle empty or whitespace-only messages
        if not chat_data.message or not chat_data.message.strip():
            ai_response = f"Hi {user_name}! I'm here to help you reduce your crypto insurance premiums. Please ask me any questions about crypto security, insurance options, or premium reduction strategies!"
            recommendations = [
                "Hardware wallet usage = 40% premium reduction",
                "Two-factor authentication = 15% reduction",
                "Regular security audits = 10% reduction",
                "Proper backup procedures = 20% reduction"
            ]
        else:
            # Intelligent AI response system based on message content
            message_lower = chat_data.message.lower()
            
            # Security-related keywords and responses
            if any(keyword in message_lower for keyword in ['hardware wallet', 'cold storage', 'ledger', 'trezor']):
                ai_response = f"Excellent question, {user_name}! Hardware wallets are the gold standard for crypto security. Using a hardware wallet like Ledger or Trezor can reduce your insurance premiums by up to 40%. These devices keep your private keys offline, making them nearly impossible to hack remotely."
                recommendations = [
                    "Hardware wallet usage = 40% premium reduction",
                    "Consider Ledger Nano X or Trezor Model T",
                    "Store seed phrase securely (separate location)",
                    "Enable PIN protection on device"
                ]
            
            elif any(keyword in message_lower for keyword in ['2fa', 'two factor', 'authentication', 'google authenticator']):
                ai_response = f"Great thinking, {user_name}! Two-factor authentication is crucial. Using 2FA on all your crypto accounts can reduce premiums by 15%. Avoid SMS-based 2FA - use app-based authenticators like Google Authenticator or hardware keys like YubiKey."
                recommendations = [
                    "App-based 2FA = 15% premium reduction",
                    "Use Google Authenticator or Authy",
                    "Avoid SMS-based 2FA (vulnerable to SIM swaps)",
                    "Consider hardware keys for maximum security"
                ]
            
            elif any(keyword in message_lower for keyword in ['exchange', 'binance', 'coinbase', 'kraken', 'centralized']):
                ai_response = f"Important consideration, {user_name}! Keeping crypto on exchanges increases risk and premiums. Moving funds to self-custody (hardware wallet) can reduce your premium by 30-50%. Only keep trading amounts on exchanges."
                recommendations = [
                    "Self-custody reduces premiums by 30-50%",
                    "Only keep trading amounts on exchanges",
                    "Use reputable exchanges with insurance coverage",
                    "Enable all available security features"
                ]
            
            elif any(keyword in message_lower for keyword in ['defi', 'smart contract', 'protocol', 'yield farming', 'liquidity']):
                ai_response = f"Smart question, {user_name}! DeFi carries higher risks but there are ways to reduce premiums: Use only audited protocols, start with established platforms like Uniswap/Aave, and consider DeFi insurance add-ons."
                recommendations = [
                    "Use only audited protocols = 20% reduction",
                    "Stick to established platforms (Uniswap, Aave)",
                    "Consider DeFi-specific insurance coverage",
                    "Monitor protocol health regularly"
                ]
            
            elif any(keyword in message_lower for keyword in ['scam', 'phishing', 'fake', 'suspicious']):
                ai_response = f"Crucial awareness, {user_name}! Scam protection education can reduce premiums by 10%. Always verify URLs, never click suspicious links, and use bookmarks for important sites. Our AI monitors for new scam patterns 24/7."
                recommendations = [
                    "Scam awareness training = 10% reduction",
                    "Always verify website URLs",
                    "Use bookmarks for important sites",
                    "Report suspicious activities immediately"
                ]
            
            elif any(keyword in message_lower for keyword in ['premium', 'cost', 'price', 'reduce', 'lower', 'cheaper']):
                ai_response = f"Perfect question, {user_name}! Here's how to maximize your premium reductions: Combine hardware wallet (40% off) + 2FA (15% off) + security audit (10% off) = up to 65% total savings. The more security measures, the lower your premium!"
                recommendations = [
                    "Hardware wallet = 40% reduction",
                    "2FA on all accounts = 15% reduction", 
                    "Regular security audits = 10% reduction",
                    "Combine all measures for maximum savings"
                ]
            
            elif any(keyword in message_lower for keyword in ['backup', 'seed phrase', 'recovery', 'lost keys']):
                ai_response = f"Critical topic, {user_name}! Proper backup procedures can reduce premiums by 20%. Store your seed phrase on metal backup plates, use multiple secure locations, and never store digitally. Lost key coverage requires verified backup procedures."
                recommendations = [
                    "Metal backup plates = 20% reduction",
                    "Multiple secure storage locations",
                    "Never store seed phrases digitally",
                    "Document your backup procedures"
                ]
            
            elif any(keyword in message_lower for keyword in ['multisig', 'multi-signature', 'multiple keys']):
                ai_response = f"Advanced security, {user_name}! Multi-signature wallets offer the highest protection and can reduce premiums by up to 50%. Requires 2+ signatures for transactions. Great for high-value holdings."
                recommendations = [
                    "Multi-signature setup = 50% reduction",
                    "Requires 2-3 signature approvals",
                    "Ideal for holdings above €50,000",
                    "Consider Gnosis Safe or Casa solutions"
                ]
            
            else:
                # General response for other questions
                ai_response = f"Hi {user_name}! I'm here to help you reduce your crypto insurance premiums. Based on your question about '{chat_data.message}', I can provide personalized advice. The key is implementing multiple security layers - each one reduces your premium!"
                recommendations = [
                    "Hardware wallet usage = 40% premium reduction",
                    "Two-factor authentication = 15% reduction",
                    "Regular security audits = 10% reduction",
                    "Proper backup procedures = 20% reduction"
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