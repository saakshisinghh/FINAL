from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio
import random
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'tata-capital-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# LLM Configuration
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@tatacapital.com')

# OTP Configuration
OTP_EXPIRY_MINUTES = 5
OTP_LENGTH = 6

# Affordability Configuration
MAX_EMI_PERCENTAGE = 40  # Max EMI as % of monthly income
MAX_DTI_RATIO = 60  # Max debt-to-income ratio

# Email Helper Function
def send_email(to_email: str, subject: str, html_content: str, attachment_path: Optional[str] = None):
    """Send email via SendGrid with optional attachment"""
    if not SENDGRID_API_KEY:
        logger.warning(f"SendGrid API key not configured - Mock email sent to {to_email}")
        logger.info(f"📧 MOCK EMAIL:\nTo: {to_email}\nSubject: {subject}")
        return False
    
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                file_data = f.read()
            encoded_file = base64.b64encode(file_data).decode()
            
            attached_file = Attachment(
                FileContent(encoded_file),
                FileName(os.path.basename(attachment_path)),
                FileType('application/pdf'),
                Disposition('attachment')
            )
            message.attachment = attached_file
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent successfully to {to_email}: Status {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Ensure uploads directory exists
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

# ========== MODELS ==========

class VerificationStatus(BaseModel):
    phone_verified: bool = False
    email_verified: bool = False
    kyc_verified: bool = False
    phone_otp_sent_at: Optional[datetime] = None
    email_otp_sent_at: Optional[datetime] = None

class FinancialProfile(BaseModel):
    monthly_income: Optional[float] = None
    existing_emi: Optional[float] = 0.0
    employment_type: Optional[str] = None  # salaried, self-employed, business
    income_verified: bool = False

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str
    full_name: str
    phone: str
    address: str
    city: str
    age: int
    credit_score: int
    pre_approved_limit: float
    current_loans: List[Dict[str, Any]] = []
    verification: VerificationStatus = Field(default_factory=VerificationStatus)
    financial_profile: FinancialProfile = Field(default_factory=FinancialProfile)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    address: str
    city: str
    age: int

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str
    address: str
    city: str
    age: int
    credit_score: int
    pre_approved_limit: float
    current_loans: List[Dict[str, Any]]
    verification: VerificationStatus
    financial_profile: FinancialProfile

class OTPRequest(BaseModel):
    type: str  # 'phone' or 'email'

class OTPVerify(BaseModel):
    type: str  # 'phone' or 'email'
    otp: str

class FinancialProfileUpdate(BaseModel):
    monthly_income: float
    existing_emi: float = 0.0
    employment_type: str

class OTPRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    otp_type: str  # 'phone' or 'email'
    otp_code: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    verified: bool = False

class LoanApplication(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    tenure_months: int
    interest_rate: float
    purpose: str
    loan_intent: Optional[str] = None  # emergency, business, education, etc.
    affordability_check: Optional[Dict[str, Any]] = None
    status: str  # pending, approved, rejected, requires_documents, requires_verification
    emi: float
    total_payable: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rejection_reason: Optional[str] = None
    sanction_letter_path: Optional[str] = None

class LoanApplicationCreate(BaseModel):
    amount: float
    tenure_months: int
    purpose: str

class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    loan_application_id: Optional[str] = None
    status: str  # active, completed, abandoned
    conversation_stage: str = 'initial'  # initial, need_discovery, affordability_check, verification, loan_offer
    discovered_intent: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # user, assistant, system
    content: str
    agent_name: Optional[str] = None  # master, sales, verification, underwriting, sanction, need_discovery
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessageCreate(BaseModel):
    message: str

class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    loan_application_id: Optional[str] = None
    doc_type: str  # salary_slip, kyc, etc
    file_path: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ========== UTILITY FUNCTIONS ==========

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: str, email: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({'id': payload['user_id']}, {'_id': 0, 'password_hash': 0})
        if not user:
            raise HTTPException(status_code=401, detail='User not found')
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')

def calculate_emi(principal: float, rate_annual: float, tenure_months: int) -> float:
    """Calculate EMI using standard formula"""
    rate_monthly = rate_annual / (12 * 100)
    if rate_monthly == 0:
        return principal / tenure_months
    emi = principal * rate_monthly * ((1 + rate_monthly) ** tenure_months) / (((1 + rate_monthly) ** tenure_months) - 1)
    return round(emi, 2)

def generate_otp() -> str:
    """Generate a random OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(OTP_LENGTH)])

async def create_otp(user_id: str, otp_type: str) -> str:
    """Create and store OTP"""
    otp_code = generate_otp()
    otp_record = OTPRecord(
        user_id=user_id,
        otp_type=otp_type,
        otp_code=otp_code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    )
    await db.otp_records.insert_one(otp_record.model_dump())
    
    # Log OTP for testing (in production, this would be sent via SMS/Email)
    logger.info(f"🔐 OTP Generated for {otp_type}: {otp_code} (User: {user_id})")
    
    return otp_code

async def verify_otp(user_id: str, otp_type: str, otp_code: str) -> bool:
    """Verify OTP"""
    otp_record = await db.otp_records.find_one({
        'user_id': user_id,
        'otp_type': otp_type,
        'otp_code': otp_code,
        'verified': False
    }, {'_id': 0})
    
    if not otp_record:
        return False
    
    # Check if OTP is expired
    if datetime.fromisoformat(otp_record['expires_at'].replace('Z', '+00:00')) < datetime.now(timezone.utc):
        return False
    
    # Mark OTP as verified
    await db.otp_records.update_one(
        {'id': otp_record['id']},
        {'$set': {'verified': True}}
    )
    
    return True

def calculate_affordability(monthly_income: float, existing_emi: float, loan_amount: float, 
                           tenure_months: int, interest_rate: float) -> Dict[str, Any]:
    """Calculate loan affordability"""
    proposed_emi = calculate_emi(loan_amount, interest_rate, tenure_months)
    total_emi = existing_emi + proposed_emi
    
    emi_percentage = (total_emi / monthly_income) * 100 if monthly_income > 0 else 0
    
    # Calculate debt-to-income ratio
    total_annual_debt = total_emi * 12
    annual_income = monthly_income * 12
    dti_ratio = (total_annual_debt / annual_income) * 100 if annual_income > 0 else 0
    
    # Calculate max affordable loan
    max_emi_allowed = (monthly_income * MAX_EMI_PERCENTAGE / 100) - existing_emi
    max_affordable_loan = 0
    if max_emi_allowed > 0:
        rate_monthly = interest_rate / (12 * 100)
        if rate_monthly > 0:
            max_affordable_loan = max_emi_allowed * (((1 + rate_monthly) ** tenure_months) - 1) / (rate_monthly * ((1 + rate_monthly) ** tenure_months))
        else:
            max_affordable_loan = max_emi_allowed * tenure_months
    
    is_affordable = emi_percentage <= MAX_EMI_PERCENTAGE and dti_ratio <= MAX_DTI_RATIO
    
    return {
        'is_affordable': is_affordable,
        'proposed_emi': round(proposed_emi, 2),
        'total_emi': round(total_emi, 2),
        'emi_percentage': round(emi_percentage, 2),
        'dti_ratio': round(dti_ratio, 2),
        'max_emi_percentage': MAX_EMI_PERCENTAGE,
        'max_dti_ratio': MAX_DTI_RATIO,
        'max_affordable_loan': round(max_affordable_loan, 2),
        'monthly_income': monthly_income,
        'existing_emi': existing_emi,
        'recommendation': 'approved' if is_affordable else 'consider_lower_amount'
    }

# ========== MOCK SERVICES ==========

@api_router.get("/mock/credit-bureau/score/{user_id}")
async def get_credit_score(user_id: str):
    """Mock credit bureau API"""
    user = await db.users.find_one({'id': user_id}, {'_id': 0})
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return {
        'user_id': user_id,
        'credit_score': user['credit_score'],
        'score_date': datetime.now(timezone.utc).isoformat(),
        'bureau': 'CIBIL'
    }

@api_router.get("/mock/crm/verify/{user_id}")
async def verify_kyc(user_id: str):
    """Mock CRM KYC verification"""
    user = await db.users.find_one({'id': user_id}, {'_id': 0})
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return {
        'user_id': user_id,
        'kyc_status': 'verified',
        'phone_verified': user.get('verification', {}).get('phone_verified', False),
        'address_verified': True,
        'full_name': user['full_name'],
        'phone': user['phone'],
        'address': user['address'],
        'city': user['city']
    }

@api_router.get("/mock/offers/{user_id}")
async def get_pre_approved_offers(user_id: str):
    """Mock offer mart server"""
    user = await db.users.find_one({'id': user_id}, {'_id': 0})
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return {
        'user_id': user_id,
        'pre_approved_limit': user['pre_approved_limit'],
        'offers': [
            {
                'type': 'personal_loan',
                'max_amount': user['pre_approved_limit'],
                'min_rate': 10.5,
                'max_tenure': 60
            }
        ]
    }

# ========== AGENTIC AI SYSTEM ==========

class AgenticAIOrchestrator:
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.current_state = 'initial'
        self.loan_data = {}
        
    async def get_user_data(self):
        return await db.users.find_one({'id': self.user_id}, {'_id': 0, 'password_hash': 0})
    
    async def get_session_data(self):
        return await db.chat_sessions.find_one({'id': self.session_id}, {'_id': 0})
    
    async def update_session(self, updates: dict):
        await db.chat_sessions.update_one(
            {'id': self.session_id},
            {'$set': {**updates, 'updated_at': datetime.now(timezone.utc)}}
        )
    
    async def save_message(self, role: str, content: str, agent_name: Optional[str] = None, metadata: Optional[Dict] = None):
        message = ChatMessage(
            session_id=self.session_id,
            role=role,
            content=content,
            agent_name=agent_name,
            metadata=metadata
        )
        await db.chat_messages.insert_one(message.model_dump())
    
    async def get_chat_history(self):
        messages = await db.chat_messages.find(
            {'session_id': self.session_id},
            {'_id': 0}
        ).sort('created_at', 1).to_list(100)
        return messages
    
    async def need_discovery_agent(self, user_message: str) -> Dict[str, Any]:
        """Need Discovery Agent - Extract intent and assess needs"""
        user = await self.get_user_data()
        session = await self.get_session_data()
        
        # Use LLM to extract intent and understand needs
        context = f"""You are a Need Discovery specialist for loan applications.
        
Customer: {user['full_name']}
Message: {user_message}

Analyze the customer's message and extract:
1. Loan Intent/Purpose (emergency, business, education, home_renovation, wedding, medical, travel, debt_consolidation, other)
2. Urgency level (high, medium, low)
3. Amount range mentioned (if any)
4. Key concerns or requirements

Provide analysis in JSON format:
{{
    "intent": "purpose",
    "urgency": "level",
    "amount_mentioned": number or null,
    "concerns": ["list", "of", "concerns"],
    "needs_income_info": true/false,
    "recommended_questions": ["questions to ask"]
}}
"""
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"need_discovery_{self.session_id}",
            system_message="You are an expert at understanding customer needs for loan applications. Respond ONLY with valid JSON."
        )
        chat.with_model("openai", "gpt-5.1")
        
        response = await chat.send_message(UserMessage(text=context))
        
        try:
            analysis = json.loads(response.strip())
        except:
            # Fallback if LLM doesn't return JSON
            analysis = {
                'intent': 'general',
                'urgency': 'medium',
                'amount_mentioned': None,
                'concerns': [],
                'needs_income_info': True,
                'recommended_questions': ['What is your monthly income?', 'Do you have any existing loans?']
            }
        
        # Update session with discovered intent
        await self.update_session({
            'discovered_intent': analysis.get('intent'),
            'conversation_stage': 'need_discovery'
        })
        
        return analysis
    
    async def affordability_agent(self, loan_amount: float, tenure_months: int, interest_rate: float) -> Dict[str, Any]:
        """Affordability Agent - Assess if loan is affordable"""
        user = await self.get_user_data()
        financial_profile = user.get('financial_profile', {})
        
        monthly_income = financial_profile.get('monthly_income')
        existing_emi = financial_profile.get('existing_emi', 0)
        
        if not monthly_income:
            return {
                'status': 'needs_income_info',
                'message': 'Please provide your monthly income to assess affordability'
            }
        
        affordability = calculate_affordability(
            monthly_income=monthly_income,
            existing_emi=existing_emi,
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            interest_rate=interest_rate
        )
        
        return {
            'status': 'assessed',
            'affordability': affordability
        }
    
    async def master_agent(self, user_message: str) -> str:
        """Master Agent - Orchestrates the entire conversation"""
        user = await self.get_user_data()
        session = await self.get_session_data()
        chat_history = await self.get_chat_history()
        
        conversation_stage = session.get('conversation_stage', 'initial')
        verification = user.get('verification', {})
        financial_profile = user.get('financial_profile', {})
        
        # Build conversation context
        context = f"""You are the Master Agent for Tata Capital, a professional loan sales assistant. 
        
Customer Details:
- Name: {user['full_name']}
- Credit Score: {user['credit_score']}/900
- Pre-approved Loan Limit: ₹{user['pre_approved_limit']:,.0f}
- City: {user['city']}
- Phone Verified: {verification.get('phone_verified', False)}
- Email Verified: {verification.get('email_verified', False)}
- KYC Verified: {verification.get('kyc_verified', False)}
- Income Info Available: {financial_profile.get('monthly_income') is not None}

Conversation Stage: {conversation_stage}
Discovered Intent: {session.get('discovered_intent', 'Unknown')}

Your role:
1. Engage warmly and professionally
2. Understand customer needs through conversational inquiry
3. Ask about their income and existing obligations if not provided
4. Guide them through verification if needed
5. Assess affordability before recommending loan amounts
6. Keep the conversation natural and helpful

Recent Chat History:
{json.dumps([{'role': m['role'], 'content': m['content'][:100]} for m in chat_history[-5:]], indent=2)}

Customer's latest message: {user_message}

Provide a helpful, conversational response. Be specific about amounts, rates, and terms when discussing loans.
If the customer hasn't verified their phone/email, gently suggest doing so for a smoother process.
If income information is missing, ask about it naturally in the conversation.
"""
        
        # Use LLM for master agent response
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"master_{self.session_id}",
            system_message="You are a professional, warm, and helpful loan sales assistant for Tata Capital. Guide customers naturally through their loan journey."
        )
        chat.with_model("openai", "gpt-5.1")
        
        response = await chat.send_message(UserMessage(text=context))
        
        # Check if we should trigger need discovery
        if any(word in user_message.lower() for word in ['loan', 'need', 'want', 'borrow', 'money', 'apply']):
            if conversation_stage == 'initial':
                # Trigger need discovery in background
                need_analysis = await self.need_discovery_agent(user_message)
                logger.info(f"Need Discovery Analysis: {need_analysis}")
        
        return response
    
    async def sales_agent(self, user_message: str, loan_amount: float, tenure: int) -> Dict[str, Any]:
        """Sales Agent - Negotiates loan terms"""
        user = await self.get_user_data()
        
        # Calculate interest rate based on credit score
        if user['credit_score'] >= 800:
            interest_rate = 10.5
        elif user['credit_score'] >= 750:
            interest_rate = 11.5
        elif user['credit_score'] >= 700:
            interest_rate = 12.5
        else:
            interest_rate = 14.0
        
        emi = calculate_emi(loan_amount, interest_rate, tenure)
        total_payable = emi * tenure
        
        return {
            'loan_amount': loan_amount,
            'tenure_months': tenure,
            'interest_rate': interest_rate,
            'emi': emi,
            'total_payable': total_payable,
            'recommended': True
        }
    
    async def verification_agent(self) -> Dict[str, Any]:
        """Verification Agent - Validates KYC and user verification"""
        user = await self.get_user_data()
        verification = user.get('verification', {})
        
        # Check verification status
        phone_verified = verification.get('phone_verified', False)
        email_verified = verification.get('email_verified', False)
        kyc_verified = verification.get('kyc_verified', False)
        
        all_verified = phone_verified and email_verified and kyc_verified
        
        return {
            'status': 'verified' if all_verified else 'pending',
            'phone_verified': phone_verified,
            'email_verified': email_verified,
            'kyc_verified': kyc_verified,
            'message': 'All verifications complete' if all_verified else 'Please complete pending verifications',
            'pending_verifications': [
                v for v, status in [
                    ('phone', not phone_verified),
                    ('email', not email_verified),
                    ('kyc', not kyc_verified)
                ] if status
            ]
        }
    
    async def underwriting_agent(self, loan_amount: float) -> Dict[str, Any]:
        """Underwriting Agent - Credit evaluation and approval logic"""
        user = await self.get_user_data()
        credit_score = user['credit_score']
        pre_approved_limit = user['pre_approved_limit']
        verification = user.get('verification', {})
        financial_profile = user.get('financial_profile', {})
        
        result = {
            'approved': False,
            'status': 'pending',
            'message': '',
            'requires_documents': False,
            'requires_verification': False
        }
        
        # Check verification status
        if not verification.get('phone_verified') or not verification.get('email_verified'):
            result['status'] = 'requires_verification'
            result['requires_verification'] = True
            result['message'] = 'Please complete phone and email verification to proceed with your loan application.'
            return result
        
        # Rule 1: Reject if credit score < 700
        if credit_score < 700:
            result['status'] = 'rejected'
            result['message'] = f'Application rejected: Credit score ({credit_score}) is below minimum requirement of 700.'
            return result
        
        # Rule 2: Instant approval if amount <= pre-approved limit
        if loan_amount <= pre_approved_limit:
            # Check affordability if income info available
            if financial_profile.get('monthly_income'):
                # Determine interest rate
                if credit_score >= 800:
                    interest_rate = 10.5
                elif credit_score >= 750:
                    interest_rate = 11.5
                elif credit_score >= 700:
                    interest_rate = 12.5
                else:
                    interest_rate = 14.0
                
                affordability = calculate_affordability(
                    monthly_income=financial_profile['monthly_income'],
                    existing_emi=financial_profile.get('existing_emi', 0),
                    loan_amount=loan_amount,
                    tenure_months=36,  # Default tenure for calculation
                    interest_rate=interest_rate
                )
                
                if not affordability['is_affordable']:
                    result['status'] = 'rejected'
                    result['message'] = f"Application rejected: Loan amount exceeds affordability. Maximum affordable amount: ₹{affordability['max_affordable_loan']:,.0f}"
                    return result
            
            result['approved'] = True
            result['status'] = 'approved'
            result['message'] = f'Congratulations! Your loan of ₹{loan_amount:,.0f} is instantly approved.'
            return result
        
        # Rule 3: Conditional approval if amount <= 2x pre-approved limit
        if loan_amount <= (2 * pre_approved_limit):
            # Check if salary slip is uploaded
            doc = await db.documents.find_one({
                'user_id': self.user_id,
                'doc_type': 'salary_slip'
            }, {'_id': 0})
            
            if doc:
                # Simulate salary verification (assume uploaded = verified)
                result['approved'] = True
                result['status'] = 'approved'
                result['message'] = f'Loan of ₹{loan_amount:,.0f} approved after document verification.'
            else:
                result['status'] = 'requires_documents'
                result['requires_documents'] = True
                result['message'] = f'Please upload your salary slip to proceed with ₹{loan_amount:,.0f} loan.'
            return result
        
        # Rule 4: Reject if amount > 2x pre-approved limit
        result['status'] = 'rejected'
        result['message'] = f'Application rejected: Requested amount (₹{loan_amount:,.0f}) exceeds maximum eligible limit of ₹{2*pre_approved_limit:,.0f}.'
        return result
    
    async def sanction_letter_generator(self, loan_application_id: str) -> str:
        """Generate sanction letter PDF"""
        loan = await db.loan_applications.find_one({'id': loan_application_id}, {'_id': 0})
        user = await self.get_user_data()
        
        if not loan or loan['status'] != 'approved':
            raise HTTPException(status_code=400, detail='Loan not approved')
        
        # Generate PDF
        filename = f"sanction_letter_{loan_application_id}.pdf"
        filepath = UPLOADS_DIR / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        story.append(Paragraph('TATA CAPITAL LIMITED', title_style))
        story.append(Paragraph('LOAN SANCTION LETTER', title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Date
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], alignment=TA_RIGHT)
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d %B %Y')}", date_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Customer details
        story.append(Paragraph(f"<b>To,</b>", styles['Normal']))
        story.append(Paragraph(f"{user['full_name']}", styles['Normal']))
        story.append(Paragraph(f"{user['address']}", styles['Normal']))
        story.append(Paragraph(f"{user['city']}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Subject
        story.append(Paragraph(f"<b>Subject: Sanction of Personal Loan - Application No. {loan_application_id[:8]}</b>", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Body
        body_text = f"""Dear {user['full_name']},<br/><br/>
        We are pleased to inform you that your application for a Personal Loan has been sanctioned by Tata Capital Limited.
        <br/><br/>The loan details are as follows:"""
        story.append(Paragraph(body_text, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Loan details table
        data = [
            ['Loan Amount', f"₹{loan['amount']:,.2f}"],
            ['Interest Rate', f"{loan['interest_rate']}% per annum"],
            ['Tenure', f"{loan['tenure_months']} months"],
            ['EMI', f"₹{loan['emi']:,.2f}"],
            ['Total Amount Payable', f"₹{loan['total_payable']:,.2f}"],
        ]
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#0D9488'))
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Terms
        terms_text = """<b>Terms and Conditions:</b><br/>
        1. The loan is subject to all terms and conditions mentioned in the loan agreement.<br/>
        2. Repayment will be through EMI starting from next month.<br/>
        3. Prepayment is allowed with applicable charges.<br/>
        4. Please sign and return the loan agreement within 7 days.<br/><br/>
        Congratulations on your loan approval! We look forward to serving you.<br/><br/>
        <b>For Tata Capital Limited</b><br/>
        Authorized Signatory
        """
        story.append(Paragraph(terms_text, styles['Normal']))
        
        doc.build(story)
        
        # Update loan application with sanction letter path
        await db.loan_applications.update_one(
            {'id': loan_application_id},
            {'$set': {'sanction_letter_path': str(filepath)}}
        )
        
        return filename

# ========== AUTH ENDPOINTS ==========

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({'email': user_data.email}, {'_id': 0})
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    
    # Create user with random credit data
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        address=user_data.address,
        city=user_data.city,
        age=user_data.age,
        credit_score=random.randint(650, 850),
        pre_approved_limit=random.choice([50000, 100000, 150000, 200000, 300000, 500000]),
        current_loans=[],
        verification=VerificationStatus(),
        financial_profile=FinancialProfile()
    )
    
    await db.users.insert_one(user.model_dump())
    
    # Create token
    token = create_access_token(user.id, user.email)
    
    return {
        'token': token,
        'user': UserResponse(**user.model_dump()).model_dump()
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email}, {'_id': 0})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    
    token = create_access_token(user['id'], user['email'])
    
    user_response = UserResponse(**user)
    return {
        'token': token,
        'user': user_response.model_dump()
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user).model_dump()

# ========== OTP ENDPOINTS ==========

@api_router.post("/otp/send")
async def send_otp(otp_request: OTPRequest, current_user: dict = Depends(get_current_user)):
    """Send OTP to phone or email"""
    otp_type = otp_request.type
    
    if otp_type not in ['phone', 'email']:
        raise HTTPException(status_code=400, detail='Invalid OTP type')
    
    # Generate and store OTP
    otp_code = await create_otp(current_user['id'], otp_type)
    
    # Update user's OTP sent timestamp
    update_field = f'verification.{otp_type}_otp_sent_at'
    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {update_field: datetime.now(timezone.utc)}}
    )
    
    # Mock send OTP (in production, send via SMS/Email service)
    target = current_user['phone'] if otp_type == 'phone' else current_user['email']
    
    logger.info(f"📱 OTP Sent to {target}: {otp_code}")
    
    # For demo purposes, return OTP in response
    return {
        'success': True,
        'message': f'OTP sent to your {otp_type}',
        'demo_otp': otp_code,  # Only for demo - remove in production
        'target': target,
        'expires_in_minutes': OTP_EXPIRY_MINUTES
    }

@api_router.post("/otp/verify")
async def verify_otp_endpoint(otp_verify: OTPVerify, current_user: dict = Depends(get_current_user)):
    """Verify OTP"""
    otp_type = otp_verify.type
    otp_code = otp_verify.otp
    
    if otp_type not in ['phone', 'email']:
        raise HTTPException(status_code=400, detail='Invalid OTP type')
    
    # Verify OTP
    is_valid = await verify_otp(current_user['id'], otp_type, otp_code)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail='Invalid or expired OTP')
    
    # Update user's verification status
    update_field = f'verification.{otp_type}_verified'
    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {update_field: True}}
    )
    
    # If both phone and email verified, mark KYC as verified
    user = await db.users.find_one({'id': current_user['id']}, {'_id': 0})
    verification = user.get('verification', {})
    if verification.get('phone_verified') and verification.get('email_verified'):
        await db.users.update_one(
            {'id': current_user['id']},
            {'$set': {'verification.kyc_verified': True}}
        )
    
    return {
        'success': True,
        'message': f'{otp_type.capitalize()} verified successfully',
        'verified': True
    }

@api_router.post("/otp/resend")
async def resend_otp(otp_request: OTPRequest, current_user: dict = Depends(get_current_user)):
    """Resend OTP"""
    return await send_otp(otp_request, current_user)

# ========== FINANCIAL PROFILE ENDPOINTS ==========

@api_router.post("/profile/financial")
async def update_financial_profile(profile: FinancialProfileUpdate, current_user: dict = Depends(get_current_user)):
    """Update financial profile"""
    await db.users.update_one(
        {'id': current_user['id']},
        {'$set': {
            'financial_profile.monthly_income': profile.monthly_income,
            'financial_profile.existing_emi': profile.existing_emi,
            'financial_profile.employment_type': profile.employment_type
        }}
    )
    
    return {
        'success': True,
        'message': 'Financial profile updated successfully'
    }

@api_router.get("/profile/affordability")
async def check_affordability(
    amount: float,
    tenure: int,
    current_user: dict = Depends(get_current_user)
):
    """Check loan affordability"""
    financial_profile = current_user.get('financial_profile', {})
    monthly_income = financial_profile.get('monthly_income')
    
    if not monthly_income:
        raise HTTPException(status_code=400, detail='Please update your financial profile first')
    
    # Determine interest rate based on credit score
    credit_score = current_user['credit_score']
    if credit_score >= 800:
        interest_rate = 10.5
    elif credit_score >= 750:
        interest_rate = 11.5
    elif credit_score >= 700:
        interest_rate = 12.5
    else:
        interest_rate = 14.0
    
    affordability = calculate_affordability(
        monthly_income=monthly_income,
        existing_emi=financial_profile.get('existing_emi', 0),
        loan_amount=amount,
        tenure_months=tenure,
        interest_rate=interest_rate
    )
    
    return affordability

# ========== CHAT ENDPOINTS ==========

@api_router.post("/chat/start")
async def start_chat(current_user: dict = Depends(get_current_user)):
    session = ChatSession(
        user_id=current_user['id'],
        status='active',
        conversation_stage='initial'
    )
    await db.chat_sessions.insert_one(session.model_dump())
    
    # Initial greeting
    orchestrator = AgenticAIOrchestrator(current_user['id'], session.id)
    
    verification = current_user.get('verification', {})
    verification_status = ""
    if not verification.get('phone_verified') or not verification.get('email_verified'):
        verification_status = "\n\n💡 Quick tip: Verify your phone and email for faster loan processing!"
    
    greeting = f"Hello {current_user['full_name']}! 👋 I'm your personal loan assistant from Tata Capital. I'm here to help you get the best personal loan tailored to your needs.{verification_status}\n\nHow can I assist you today?"
    
    await orchestrator.save_message('assistant', greeting, 'master')
    
    return {
        'session_id': session.id,
        'message': greeting
    }

@api_router.post("/chat/{session_id}/message")
async def send_message(
    session_id: str,
    message_data: ChatMessageCreate,
    current_user: dict = Depends(get_current_user)
):
    # Verify session belongs to user
    session = await db.chat_sessions.find_one({'id': session_id, 'user_id': current_user['id']}, {'_id': 0})
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    
    orchestrator = AgenticAIOrchestrator(current_user['id'], session_id)
    
    # Save user message
    await orchestrator.save_message('user', message_data.message)
    
    # Get master agent response
    response = await orchestrator.master_agent(message_data.message)
    
    # Save assistant response
    await orchestrator.save_message('assistant', response, 'master')
    
    return {
        'message': response,
        'agent': 'master'
    }

@api_router.get("/chat/{session_id}/history")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    session = await db.chat_sessions.find_one({'id': session_id, 'user_id': current_user['id']}, {'_id': 0})
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    
    messages = await db.chat_messages.find(
        {'session_id': session_id},
        {'_id': 0}
    ).sort('created_at', 1).to_list(1000)
    
    return messages

# ========== LOAN ENDPOINTS ==========

@api_router.post("/loans/apply")
async def apply_loan(
    loan_data: LoanApplicationCreate,
    current_user: dict = Depends(get_current_user)
):
    orchestrator = AgenticAIOrchestrator(current_user['id'], str(uuid.uuid4()))
    
    # Sales agent calculates terms
    sales_result = await orchestrator.sales_agent('', loan_data.amount, loan_data.tenure_months)
    
    # Check affordability if financial profile available
    affordability_check = None
    financial_profile = current_user.get('financial_profile', {})
    if financial_profile.get('monthly_income'):
        affordability_result = await orchestrator.affordability_agent(
            loan_data.amount,
            loan_data.tenure_months,
            sales_result['interest_rate']
        )
        if affordability_result['status'] == 'assessed':
            affordability_check = affordability_result['affordability']
    
    # Verification agent
    kyc_result = await orchestrator.verification_agent()
    
    # Underwriting agent
    underwriting_result = await orchestrator.underwriting_agent(loan_data.amount)
    
    # Create loan application
    loan_app = LoanApplication(
        user_id=current_user['id'],
        amount=loan_data.amount,
        tenure_months=loan_data.tenure_months,
        interest_rate=sales_result['interest_rate'],
        purpose=loan_data.purpose,
        affordability_check=affordability_check,
        status=underwriting_result['status'],
        emi=sales_result['emi'],
        total_payable=sales_result['total_payable'],
        rejection_reason=underwriting_result.get('message') if underwriting_result['status'] == 'rejected' else None
    )
    
    await db.loan_applications.insert_one(loan_app.model_dump())
    
    # If approved, generate sanction letter and send email
    if underwriting_result['status'] == 'approved':
        try:
            sanction_file = await orchestrator.sanction_letter_generator(loan_app.id)
            underwriting_result['sanction_letter'] = sanction_file
            
            # Send approval email with sanction letter
            sanction_path = UPLOADS_DIR / sanction_file
            email_subject = f"🎉 Loan Approved - Tata Capital (Application #{loan_app.id[:8]})"
            email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0D9488;">Congratulations, {current_user['full_name']}! 🎉</h2>
                    <p>We are delighted to inform you that your personal loan application has been <strong>approved</strong>!</p>
                    
                    <div style="background-color: #F0FDFA; border-left: 4px solid #0D9488; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #0D9488;">Loan Details</h3>
                        <p><strong>Loan Amount:</strong> ₹{loan_app.amount:,.2f}</p>
                        <p><strong>Interest Rate:</strong> {loan_app.interest_rate}% per annum</p>
                        <p><strong>Tenure:</strong> {loan_app.tenure_months} months</p>
                        <p><strong>Monthly EMI:</strong> ₹{loan_app.emi:,.2f}</p>
                        <p><strong>Total Payable:</strong> ₹{loan_app.total_payable:,.2f}</p>
                    </div>
                    
                    <p>Please find your <strong>Sanction Letter</strong> attached to this email.</p>
                    
                    <p style="margin-top: 30px;">Next Steps:</p>
                    <ol>
                        <li>Review the attached sanction letter</li>
                        <li>Sign and return the loan agreement within 7 days</li>
                        <li>Complete any pending documentation</li>
                        <li>Loan disbursement will be processed within 24-48 hours</li>
                    </ol>
                    
                    <p style="margin-top: 30px;">If you have any questions, please don't hesitate to contact our customer support.</p>
                    
                    <p style="margin-top: 40px; color: #666; font-size: 14px;">
                        Best regards,<br/>
                        <strong>Tata Capital Loan Team</strong>
                    </p>
                </div>
            </body>
            </html>
            """
            send_email(current_user['email'], email_subject, email_body, str(sanction_path))
            
        except Exception as e:
            logger.error(f"Error generating sanction letter: {e}")
    
    # Handle other statuses (rejected, requires_documents, requires_verification)
    elif underwriting_result['status'] == 'rejected':
        email_subject = f"Loan Application Update - Tata Capital (Application #{loan_app.id[:8]})"
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #DC2626;">Loan Application Status Update</h2>
                <p>Dear {current_user['full_name']},</p>
                <p>Thank you for applying for a personal loan with Tata Capital.</p>
                
                <div style="background-color: #FEF2F2; border-left: 4px solid #DC2626; padding: 15px; margin: 20px 0;">
                    <p><strong>Application Status:</strong> Not Approved</p>
                    <p><strong>Reason:</strong> {underwriting_result.get('message', 'Does not meet current eligibility criteria')}</p>
                </div>
                
                <p>We encourage you to:</p>
                <ul>
                    <li>Review your credit score and work on improving it</li>
                    <li>Consider applying for a smaller loan amount</li>
                    <li>Contact our support team for personalized guidance</li>
                </ul>
                
                <p style="margin-top: 30px;">You may reapply after addressing the eligibility requirements.</p>
                
                <p style="margin-top: 40px; color: #666; font-size: 14px;">
                    Best regards,<br/>
                    <strong>Tata Capital Loan Team</strong>
                </p>
            </div>
        </body>
        </html>
        """
        send_email(current_user['email'], email_subject, email_body)
    
    elif underwriting_result['status'] == 'requires_verification':
        email_subject = f"Action Required: Verification Pending - Tata Capital (Application #{loan_app.id[:8]})"
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #D97706;">⚠️ Verification Required for Your Loan Application</h2>
                <p>Dear {current_user['full_name']},</p>
                <p>Thank you for applying for a personal loan of <strong>₹{loan_app.amount:,.2f}</strong>.</p>
                
                <div style="background-color: #FFFBEB; border-left: 4px solid #D97706; padding: 15px; margin: 20px 0;">
                    <p><strong>Action Required:</strong></p>
                    <p>Please complete phone and email verification to proceed with your application.</p>
                </div>
                
                <p>You can complete verification by logging into your account.</p>
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    Best regards,<br/>
                    <strong>Tata Capital Loan Team</strong>
                </p>
            </div>
        </body>
        </html>
        """
        send_email(current_user['email'], email_subject, email_body)
    
    elif underwriting_result['status'] == 'requires_documents':
        email_subject = f"Action Required: Upload Documents - Tata Capital (Application #{loan_app.id[:8]})"
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #D97706;">📄 Documents Required for Your Loan Application</h2>
                <p>Dear {current_user['full_name']},</p>
                <p>Thank you for applying for a personal loan of <strong>₹{loan_app.amount:,.2f}</strong>.</p>
                
                <div style="background-color: #FFFBEB; border-left: 4px solid #D97706; padding: 15px; margin: 20px 0;">
                    <p><strong>Action Required:</strong></p>
                    <p>Please upload your salary slip and other required documents to complete your application.</p>
                </div>
                
                <p><strong>Required Documents:</strong></p>
                <ul>
                    <li>Latest salary slip (last 3 months preferred)</li>
                    <li>PAN Card</li>
                    <li>Aadhaar Card</li>
                    <li>Bank statement (last 6 months)</li>
                </ul>
                
                <p>You can upload these documents by logging into your account at our loan portal.</p>
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    Best regards,<br/>
                    <strong>Tata Capital Loan Team</strong>
                </p>
            </div>
        </body>
        </html>
        """
        send_email(current_user['email'], email_subject, email_body)
    
    return {
        'loan_application': loan_app.model_dump(),
        'underwriting_result': underwriting_result
    }

@api_router.get("/loans")
async def get_loans(current_user: dict = Depends(get_current_user)):
    loans = await db.loan_applications.find(
        {'user_id': current_user['id']},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    return loans

@api_router.get("/loans/{loan_id}")
async def get_loan(
    loan_id: str,
    current_user: dict = Depends(get_current_user)
):
    loan = await db.loan_applications.find_one(
        {'id': loan_id, 'user_id': current_user['id']},
        {'_id': 0}
    )
    if not loan:
        raise HTTPException(status_code=404, detail='Loan not found')
    return loan

# ========== DOCUMENT ENDPOINTS ==========

@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = 'salary_slip',
    loan_application_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # Validate file type
    file_extension = file.filename.split('.')[-1].lower()
    allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg']
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}'
        )
    
    # Validate file size (10MB limit)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail='File size exceeds 10MB limit')
    
    # Save file
    filename = f"{current_user['id']}_{doc_type}_{uuid.uuid4()}.{file_extension}"
    filepath = UPLOADS_DIR / filename
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # Save document record
    doc = Document(
        user_id=current_user['id'],
        loan_application_id=loan_application_id,
        doc_type=doc_type,
        file_path=str(filepath)
    )
    await db.documents.insert_one(doc.model_dump())
    
    # If salary slip uploaded, mark income as verified
    if doc_type == 'salary_slip':
        await db.users.update_one(
            {'id': current_user['id']},
            {'$set': {'financial_profile.income_verified': True}}
        )
    
    # If document is linked to a loan application, re-evaluate it
    result = {
        'document_id': doc.id,
        'message': 'Document uploaded successfully'
    }
    
    if loan_application_id:
        loan = await db.loan_applications.find_one(
            {'id': loan_application_id, 'user_id': current_user['id']},
            {'_id': 0}
        )
        
        if loan and loan['status'] == 'requires_documents':
            # Re-evaluate the loan with underwriting agent
            orchestrator = AgenticAIOrchestrator(current_user['id'], str(uuid.uuid4()))
            underwriting_result = await orchestrator.underwriting_agent(loan['amount'])
            
            # Update loan status
            update_data = {
                'status': underwriting_result['status'],
                'updated_at': datetime.now(timezone.utc)
            }
            
            if underwriting_result['status'] == 'rejected':
                update_data['rejection_reason'] = underwriting_result['message']
            
            await db.loan_applications.update_one(
                {'id': loan_application_id},
                {'$set': update_data}
            )
            
            # Generate sanction letter if approved and send email
            if underwriting_result['status'] == 'approved':
                try:
                    sanction_file = await orchestrator.sanction_letter_generator(loan_application_id)
                    result['sanction_letter'] = sanction_file
                    
                    # Send approval email
                    sanction_path = UPLOADS_DIR / sanction_file
                    email_subject = f"🎉 Loan Approved After Document Verification - Tata Capital"
                    email_body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h2 style="color: #0D9488;">Great News, {current_user['full_name']}! 🎉</h2>
                            <p>Your documents have been verified and your loan application has been <strong>approved</strong>!</p>
                            
                            <div style="background-color: #F0FDFA; border-left: 4px solid #0D9488; padding: 15px; margin: 20px 0;">
                                <h3 style="margin-top: 0; color: #0D9488;">Loan Details</h3>
                                <p><strong>Loan Amount:</strong> ₹{loan['amount']:,.2f}</p>
                                <p><strong>Monthly EMI:</strong> ₹{loan['emi']:,.2f}</p>
                                <p><strong>Interest Rate:</strong> {loan['interest_rate']}% per annum</p>
                            </div>
                            
                            <p>Your sanction letter is attached to this email.</p>
                            
                            <p style="margin-top: 40px; color: #666; font-size: 14px;">
                                Best regards,<br/>
                                <strong>Tata Capital Loan Team</strong>
                            </p>
                        </div>
                    </body>
                    </html>
                    """
                    send_email(current_user['email'], email_subject, email_body, str(sanction_path))
                    
                except Exception as e:
                    logger.error(f"Error generating sanction letter: {e}")
            
            result['loan_status_updated'] = True
            result['new_loan_status'] = underwriting_result['status']
            result['message'] = f'Document uploaded and loan re-evaluated: {underwriting_result["message"]}'
    
    return result

@api_router.get("/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    docs = await db.documents.find(
        {'user_id': current_user['id']},
        {'_id': 0}
    ).sort('uploaded_at', -1).to_list(100)
    return docs

# ========== SANCTION LETTER ENDPOINTS ==========

@api_router.get("/sanction/{loan_id}/download")
async def download_sanction_letter(
    loan_id: str,
    current_user: dict = Depends(get_current_user)
):
    loan = await db.loan_applications.find_one(
        {'id': loan_id, 'user_id': current_user['id']},
        {'_id': 0}
    )
    
    if not loan:
        raise HTTPException(status_code=404, detail='Loan not found')
    
    if loan['status'] != 'approved':
        raise HTTPException(status_code=400, detail='Loan not approved')
    
    if not loan.get('sanction_letter_path'):
        # Generate if not exists
        orchestrator = AgenticAIOrchestrator(current_user['id'], str(uuid.uuid4()))
        filename = await orchestrator.sanction_letter_generator(loan_id)
        filepath = UPLOADS_DIR / filename
    else:
        filepath = Path(loan['sanction_letter_path'])
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail='Sanction letter not found')
    
    return FileResponse(
        path=str(filepath),
        filename=f"sanction_letter_{loan_id[:8]}.pdf",
        media_type='application/pdf'
    )

# ========== DASHBOARD ENDPOINTS ==========

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    # Get loan applications
    loans = await db.loan_applications.find(
        {'user_id': current_user['id']},
        {'_id': 0}
    ).to_list(100)
    
    active_loans = [l for l in loans if l['status'] == 'approved']
    pending_loans = [l for l in loans if l['status'] in ['requires_documents', 'requires_verification', 'pending']]
    
    total_borrowed = sum(l['amount'] for l in active_loans)
    total_emi = sum(l['emi'] for l in active_loans)
    
    verification = current_user.get('verification', {})
    financial_profile = current_user.get('financial_profile', {})
    
    return {
        'credit_score': current_user['credit_score'],
        'pre_approved_limit': current_user['pre_approved_limit'],
        'total_loans': len(loans),
        'active_loans': len(active_loans),
        'pending_applications': len(pending_loans),
        'total_borrowed': total_borrowed,
        'monthly_emi': total_emi,
        'available_credit': current_user['pre_approved_limit'] - total_borrowed,
        'verification_status': {
            'phone_verified': verification.get('phone_verified', False),
            'email_verified': verification.get('email_verified', False),
            'kyc_verified': verification.get('kyc_verified', False)
        },
        'financial_profile': {
            'monthly_income': financial_profile.get('monthly_income'),
            'existing_emi': financial_profile.get('existing_emi', 0),
            'employment_type': financial_profile.get('employment_type'),
            'income_verified': financial_profile.get('income_verified', False)
        }
    }

# ========== INITIALIZE SYNTHETIC DATA ==========

@api_router.post("/admin/init-data")
async def initialize_synthetic_data():
    """Initialize database with 10+ synthetic customers"""
    existing = await db.users.count_documents({})
    if existing > 0:
        return {'message': f'Database already has {existing} users'}
    
    synthetic_users = [
        {
            'email': 'rajesh.kumar@example.com',
            'password': 'password123',
            'full_name': 'Rajesh Kumar',
            'phone': '+91-9876543210',
            'address': '123 MG Road',
            'city': 'Mumbai',
            'age': 35,
            'credit_score': 780,
            'pre_approved_limit': 300000
        },
        {
            'email': 'priya.sharma@example.com',
            'password': 'password123',
            'full_name': 'Priya Sharma',
            'phone': '+91-9876543211',
            'address': '456 Residency Road',
            'city': 'Bangalore',
            'age': 28,
            'credit_score': 820,
            'pre_approved_limit': 500000
        },
        {
            'email': 'amit.patel@example.com',
            'password': 'password123',
            'full_name': 'Amit Patel',
            'phone': '+91-9876543212',
            'address': '789 SG Highway',
            'city': 'Ahmedabad',
            'age': 42,
            'credit_score': 750,
            'pre_approved_limit': 200000
        },
        {
            'email': 'sneha.reddy@example.com',
            'password': 'password123',
            'full_name': 'Sneha Reddy',
            'phone': '+91-9876543213',
            'address': '321 Banjara Hills',
            'city': 'Hyderabad',
            'age': 31,
            'credit_score': 690,
            'pre_approved_limit': 150000
        },
        {
            'email': 'vikram.singh@example.com',
            'password': 'password123',
            'full_name': 'Vikram Singh',
            'phone': '+91-9876543214',
            'address': '654 Connaught Place',
            'city': 'Delhi',
            'age': 38,
            'credit_score': 800,
            'pre_approved_limit': 400000
        },
        {
            'email': 'anjali.mehta@example.com',
            'password': 'password123',
            'full_name': 'Anjali Mehta',
            'phone': '+91-9876543215',
            'address': '987 Park Street',
            'city': 'Kolkata',
            'age': 29,
            'credit_score': 760,
            'pre_approved_limit': 250000
        },
        {
            'email': 'rahul.verma@example.com',
            'password': 'password123',
            'full_name': 'Rahul Verma',
            'phone': '+91-9876543216',
            'address': '147 Anna Salai',
            'city': 'Chennai',
            'age': 45,
            'credit_score': 850,
            'pre_approved_limit': 500000
        },
        {
            'email': 'kavita.joshi@example.com',
            'password': 'password123',
            'full_name': 'Kavita Joshi',
            'phone': '+91-9876543217',
            'address': '258 FC Road',
            'city': 'Pune',
            'age': 33,
            'credit_score': 720,
            'pre_approved_limit': 180000
        },
        {
            'email': 'deepak.gupta@example.com',
            'password': 'password123',
            'full_name': 'Deepak Gupta',
            'phone': '+91-9876543218',
            'address': '369 MI Road',
            'city': 'Jaipur',
            'age': 40,
            'credit_score': 680,
            'pre_approved_limit': 120000
        },
        {
            'email': 'neha.kapoor@example.com',
            'password': 'password123',
            'full_name': 'Neha Kapoor',
            'phone': '+91-9876543219',
            'address': '741 Dal Lake Road',
            'city': 'Srinagar',
            'age': 27,
            'credit_score': 790,
            'pre_approved_limit': 350000
        },
        {
            'email': 'arjun.nair@example.com',
            'password': 'password123',
            'full_name': 'Arjun Nair',
            'phone': '+91-9876543220',
            'address': '852 MG Road',
            'city': 'Kochi',
            'age': 36,
            'credit_score': 810,
            'pre_approved_limit': 450000
        },
        {
            'email': 'pooja.das@example.com',
            'password': 'password123',
            'full_name': 'Pooja Das',
            'phone': '+91-9876543221',
            'address': '963 GS Road',
            'city': 'Guwahati',
            'age': 30,
            'credit_score': 740,
            'pre_approved_limit': 220000
        }
    ]
    
    for user_data in synthetic_users:
        user = User(
            email=user_data['email'],
            password_hash=hash_password(user_data['password']),
            full_name=user_data['full_name'],
            phone=user_data['phone'],
            address=user_data['address'],
            city=user_data['city'],
            age=user_data['age'],
            credit_score=user_data['credit_score'],
            pre_approved_limit=user_data['pre_approved_limit'],
            current_loans=[],
            verification=VerificationStatus(),
            financial_profile=FinancialProfile()
        )
        await db.users.insert_one(user.model_dump())
    
    return {
        'message': f'Successfully created {len(synthetic_users)} synthetic users',
        'sample_login': {
            'email': 'rajesh.kumar@example.com',
            'password': 'password123'
        }
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
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
