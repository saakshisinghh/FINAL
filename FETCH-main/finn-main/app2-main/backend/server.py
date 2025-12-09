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

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Ensure uploads directory exists
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

# ========== MODELS ==========

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

class LoanApplication(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    tenure_months: int
    interest_rate: float
    purpose: str
    status: str  # pending, approved, rejected, requires_documents
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # user, assistant, system
    content: str
    agent_name: Optional[str] = None  # master, sales, verification, underwriting, sanction
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
        'phone_verified': True,
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
    
    async def save_message(self, role: str, content: str, agent_name: Optional[str] = None):
        message = ChatMessage(
            session_id=self.session_id,
            role=role,
            content=content,
            agent_name=agent_name
        )
        await db.chat_messages.insert_one(message.model_dump())
    
    async def get_chat_history(self):
        messages = await db.chat_messages.find(
            {'session_id': self.session_id},
            {'_id': 0}
        ).sort('created_at', 1).to_list(100)
        return messages
    
    async def master_agent(self, user_message: str) -> str:
        """Master Agent - Orchestrates the entire conversation"""
        user = await self.get_user_data()
        chat_history = await self.get_chat_history()
        
        # Build conversation context
        context = f"""You are the Master Agent for Tata Capital, a professional loan sales assistant. 
        
Customer Details:
- Name: {user['full_name']}
- Credit Score: {user['credit_score']}/900
- Pre-approved Loan Limit: ₹{user['pre_approved_limit']:,.0f}
- City: {user['city']}

Your role:
1. Engage warmly and professionally
2. Understand customer needs
3. Guide them through the personal loan process
4. Coordinate with worker agents when needed
5. Keep the conversation natural and helpful

Current conversation stage: {self.current_state}

Chat History:
{json.dumps([{'role': m['role'], 'content': m['content'][:100]} for m in chat_history[-5:]], indent=2)}

Customer's latest message: {user_message}

Provide a helpful, conversational response. If discussing loan details, be specific about amounts, rates, and terms."""
        
        # Use LLM for master agent response
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"master_{self.session_id}",
            system_message="You are a professional loan sales assistant for Tata Capital. Be warm, helpful, and guide customers naturally."
        )
        chat.with_model("openai", "gpt-5.1")
        
        response = await chat.send_message(UserMessage(text=context))
        
        # Determine if we need to invoke worker agents
        if any(word in user_message.lower() for word in ['apply', 'loan', 'amount', 'need', 'want']):
            if self.current_state == 'initial':
                self.current_state = 'discussing_loan'
        
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
        """Verification Agent - Validates KYC"""
        user = await self.get_user_data()
        
        # Call mock CRM API
        kyc_data = {
            'status': 'verified',
            'phone_verified': True,
            'address_verified': True,
            'message': f'KYC verified for {user["full_name"]}'
        }
        
        return kyc_data
    
    async def underwriting_agent(self, loan_amount: float) -> Dict[str, Any]:
        """Underwriting Agent - Credit evaluation and approval logic"""
        user = await self.get_user_data()
        credit_score = user['credit_score']
        pre_approved_limit = user['pre_approved_limit']
        
        result = {
            'approved': False,
            'status': 'pending',
            'message': '',
            'requires_documents': False
        }
        
        # Rule 1: Reject if credit score < 700
        if credit_score < 700:
            result['status'] = 'rejected'
            result['message'] = f'Application rejected: Credit score ({credit_score}) is below minimum requirement of 700.'
            return result
        
        # Rule 2: Instant approval if amount <= pre-approved limit
        if loan_amount <= pre_approved_limit:
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
        current_loans=[]
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

# ========== CHAT ENDPOINTS ==========

@api_router.post("/chat/start")
async def start_chat(current_user: dict = Depends(get_current_user)):
    session = ChatSession(
        user_id=current_user['id'],
        status='active'
    )
    await db.chat_sessions.insert_one(session.model_dump())
    
    # Initial greeting
    orchestrator = AgenticAIOrchestrator(current_user['id'], session.id)
    greeting = f"Hello {current_user['full_name']}! 👋 I'm your personal loan assistant from Tata Capital. I'm here to help you get the best personal loan tailored to your needs. How can I assist you today?"
    
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
        status=underwriting_result['status'],
        emi=sales_result['emi'],
        total_payable=sales_result['total_payable'],
        rejection_reason=underwriting_result.get('message') if underwriting_result['status'] == 'rejected' else None
    )
    
    await db.loan_applications.insert_one(loan_app.model_dump())
    
    # If approved, generate sanction letter
    if underwriting_result['status'] == 'approved':
        try:
            sanction_file = await orchestrator.sanction_letter_generator(loan_app.id)
            underwriting_result['sanction_letter'] = sanction_file
        except Exception as e:
            print(f"Error generating sanction letter: {e}")
    
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
            
            # Generate sanction letter if approved
            if underwriting_result['status'] == 'approved':
                try:
                    sanction_file = await orchestrator.sanction_letter_generator(loan_application_id)
                    result['sanction_letter'] = sanction_file
                except Exception as e:
                    print(f"Error generating sanction letter: {e}")
            
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
    pending_loans = [l for l in loans if l['status'] == 'requires_documents']
    
    total_borrowed = sum(l['amount'] for l in active_loans)
    total_emi = sum(l['emi'] for l in active_loans)
    
    return {
        'credit_score': current_user['credit_score'],
        'pre_approved_limit': current_user['pre_approved_limit'],
        'total_loans': len(loans),
        'active_loans': len(active_loans),
        'pending_applications': len(pending_loans),
        'total_borrowed': total_borrowed,
        'monthly_emi': total_emi,
        'available_credit': current_user['pre_approved_limit'] - total_borrowed
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
            current_loans=[]
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
