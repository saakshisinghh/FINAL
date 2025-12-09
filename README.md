Tata Capital Agentic AI Loan Assistant
AI-Powered Conversational Loan Sales Platform | Multi-Agent Architecture | EY Hackathon 2024
📘 Overview

The Tata Capital Agentic AI Loan Assistant is an end-to-end AI-powered loan sales automation platform designed for the BFSI sector. Built for the EY Hackathon 2024, the system simulates a human loan officer using a multi-agent AI architecture capable of:

Understanding customer needs

Performing verification (OTP, KYC)

Running affordability checks

Underwriting credit decisions

Generating sanction letters automatically

The solution uses a Master-Worker Agentic model, FastAPI backend, React frontend, and GPT-5.1 (via Emergent) for natural conversation.

🎯 Problem Statement

Traditional loan journeys require manual effort, leading to:

Lower conversion rates

Non-personalized offers

Slow verification and underwriting

High operational costs

Goal: Build an AI agent capable of acting as a personalized sales executive who can autonomously handle the loan journey from intent → verification → underwriting → approval.

🧱 System Architecture
4
High-Level Architecture
Frontend (React)
   │
   ▼
Backend (FastAPI)
   │
   ├── Master Agent (Conversation Orchestrator)
   │       └── Worker Agents
   │             ├── Need Discovery Agent
   │             ├── Sales Agent (EMI + Rates)
   │             ├── Verification Agent
   │             ├── Affordability Agent
   │             ├── Underwriting Agent
   │             └── Sanction Letter Generator
   │
   ▼
MongoDB Database

🤖 Agentic AI System
1. Master Agent (Orchestrator)

Handles conversation flow, decides which agent to trigger, maintains journey stages:

Initial

Need Discovery

Affordability Check

Verification

Loan Offer

Backed by GPT-5.1, ensuring warm human-like dialogue.

2. Need Discovery Agent

Extracts:

Loan purpose

Urgency

Mentioned amount

Customer concerns

Outputs structured JSON for downstream agents.

3. Sales Agent

Works like a banking RM:

Determines interest rate (based on credit score)

Calculates EMI using reducing balance formula

Provides optimized loan recommendations

4. Verification Agent

Handles:

Phone OTP

Email OTP

KYC (via mock CRM)

Tracks timestamps, expiry, and verification states.

5. Affordability Agent

Uses industry standards:

EMI ≤ 40% of income

DTI ≤ 60%

Determines maximum eligible loan dynamically.

6. Underwriting Agent

Implements NBFC-style 3-tier approval logic:

Tier	Conditions	Output
Instant Approval	Within pre-approved limit + score ≥ 700	Approved
Conditional	Requires salary slip	Needs Documents
Reject	Score < 700 OR exceeds limit	Rejected
7. Sanction Letter Generator

Creates a professional PDF:

Loan details (Rate, EMI, Tenure)

Customer information

Terms & conditions

Tata Capital branding

Sent via email + downloadable in dashboard.

✨ Key Features
🔐 Secure Authentication

JWT-based login

Bcrypt hashed passwords

💬 Conversational AI Chatbot

Context-aware multi-turn conversation

Replicates a human loan officer

🧮 Smart Loan Evaluation

Dynamic EMI calculator

Affordability & DTI calculations

Credit-score based interest rate

📄 Document & Verification Flow

Automated OTP

Salary slip upload

Re-evaluation trigger

📈 User Dashboard

Credit score

Pre-approved limit

Active & past loans

Sanction letters

🔧 Technology Stack
Backend

FastAPI

Python 3.9+

MongoDB (Motor)

GPT-5.1 

ReportLab (PDF)

SendGrid

Frontend

React 19

Tailwind CSS

React Router

Axios

Radix UI

Sonner (notifications)

🚀 Installation
1. Clone Repository
git clone <repository-url>
cd "EY hackathonn/FINAL"

2. Backend Setup
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001


Edit .env for:

MONGO_URL

JWT_SECRET

EMERGENT_LLM_KEY

SENDGRID_API_KEY

Backend runs at:
👉 http://localhost:8001

3. Frontend Setup
cd frontend
yarn install
yarn start


Frontend runs at:
👉 http://localhost:3000

4. Demo Data
curl -X POST http://localhost:8001/api/admin/init-data

🗂️ Project Structure
backend/
  server.py
  requirements.txt
  .env
  uploads/
frontend/
  src/
    pages/
    components/
    context/
  public/
  .env
README.md

📚 API Documentation (Summary)
Authentication

POST /api/auth/register

POST /api/auth/login

GET /api/auth/me

Chat

POST /api/chat/start

POST /api/chat/{session_id}/message

GET /api/chat/{session_id}/history

Loan

POST /api/loans/apply

GET /api/loans

GET /api/sanction/{loan_id}/download

Profile & Verification

POST /api/profile/financial

POST /api/otp/send

POST /api/otp/verify

🛠️ Business Logic Summary
Interest Rates
Credit Score	Rate
≥ 800	10.5%
≥ 750	11.5%
≥ 700	12.5%
< 700	14%
Affordability Rules

EMI ≤ 40% of income

DTI ≤ 60%

Underwriting Decision Tree
IF credit < 700 → Reject
IF not verified → Needs Verification
IF amount ≤ limit → Instant Approval
IF amount ≤ 2× limit → Need Documents
ELSE → Reject

🧪 Testing Scenarios
✅ Instant Approval

High score + within limit → Approved + sanction letter.

📝 Document Required

Loan > limit → salary slip upload → re-evaluation.

❌ Rejection

Credit score < 700 or loan exceeds limits.

🤖 Conversational Flow

Intent → income → EMI suggestion → apply → approve.



🔮 Future Enhancements

Voice-based assistant

OCR document validation

Multi-language support

Fraud detection models

Real credit bureau / Aadhaar integrations

Admin analytics dashboards

❤️ Team & Acknowledgements

Built for EY Hackathon 2024
Inspired by Tata Capital’s digital lending ecosystem.

Thanks to:
EY Hackathon organizers



⭐ Final Words

This project demonstrates:

Real Agentic AI orchestration

Human-like personal loan sales assistance

Automated underwriting

Bank-grade workflows built with modern tech

A complete, scalable, AI-first loan sales engine.
