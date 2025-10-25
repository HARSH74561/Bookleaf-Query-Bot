# main.py - Customer Query Bot Implementation

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import openai
from supabase import create_client, Client
import numpy as np
from fuzzywuzzy import fuzz, process
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import webbrowser
import threading

# Load environment variables
load_dotenv()

# Configuration
@dataclass
class Config:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "your-supabase-url")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "your-supabase-key")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your-openai-key")
    CONFIDENCE_THRESHOLD: float = 0.80  # 80% confidence threshold
    MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

config = Config()
openai.api_key = config.OPENAI_API_KEY

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Initialize Supabase Client (skip if using mock data)
try:
    if config.SUPABASE_URL != "your-supabase-url" and config.SUPABASE_KEY != "your-supabase-key":
        supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    else:
        print("⚠️  Supabase not configured - using mock data only")
        supabase = None
except Exception as e:
    print(f"⚠️  Supabase connection failed: {e} - using mock data")
    supabase = None

# Initialize Query Logger
class QueryLogger:
    def __init__(self, db_path="query_logs.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                channel TEXT,
                user_identifier TEXT,
                query TEXT NOT NULL,
                matched_author_email TEXT,
                confidence REAL,
                response TEXT,
                escalated BOOLEAN DEFAULT 0,
                error TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def log_query(self, query_data: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO query_logs 
            (timestamp, channel, user_identifier, query, matched_author_email, 
             confidence, response, escalated, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query_data.get('timestamp', datetime.now().isoformat()),
            query_data.get('channel', 'API'),
            query_data.get('user_identifier'),
            query_data.get('query'),
            query_data.get('matched_author_email'),
            query_data.get('confidence'),
            query_data.get('response'),
            query_data.get('escalated', False),
            query_data.get('error')
        ))
        conn.commit()
        conn.close()

logger = QueryLogger()

# Knowledge Base - BookLeaf Publishing Complete Information
KNOWLEDGE_BASE = """
📌 What We Don't Offer (Important Limitations)

To ensure clarity and avoid misunderstandings, here are some services and features BookLeaf Publishing does not currently offer:

Phone or Video Support
We do not offer phone calls, WhatsApp calls, or video meetings for support. All communication and assistance are provided via WhatsApp, email or our helpdesk.

Editing, Proofreading, or Design Services (Standalone)
We currently do not provide editing, proofreading, or custom cover design as separate services. The tools and templates available on your dashboard are designed for DIY usage.
Note: Some premium packages (e.g., Bestseller Breakthrough) may include additional consulting, but standalone editing/design services are not offered.

Publishing Outside Poetry
At this time, we only publish poetry books through our 21-Day Writing Challenge. Submissions of fiction, short stories, or novels are temporarily not accepted.

Book Type / Genre
Anthologies or group submissions are not accepted.

File Ownership / KDP Restrictions
BookLeaf does not provide source files, print-ready PDFs, or open/editable formats.
ISBNs issued by BookLeaf cannot be reused elsewhere (e.g., on KDP).

Sales-Related Clarity
BookLeaf cannot influence or guarantee sales, reviews, or star ratings on Amazon.

Additional Information
The AI agent must avoid confirming any awards, editor picks, or nominations unless explicitly listed in the KB.
No timeline or guarantee should be given for any award beyond what's stated in the knowledge base.

Shipping & Free Copies
Free international shipping is not provided, even for author copies, unless specifically mentioned.
Bot must decline special packaging or autographed copy requests.

Uncommon requests like tax invoices or customised publishing certificates should be escalated to a human agent.

Custom Publishing via Kindle Direct Publishing (KDP)
Authors are not permitted to use BookLeaf-provided files or ISBNs to upload their books to KDP or any other platform.
If you wish to publish independently, you'll need to:
- Use a different ISBN
- Create a new version of your book without BookLeaf branding and BookLeaf logo

Guaranteed Prime Badge on Amazon
We submit every eligible title for Prime consideration after it goes live, but Amazon independently decides whether to display the Prime badge. We cannot guarantee or expedite this.

Delivery Exemptions for Amazon Prime Members
Delivery charges on Amazon are handled entirely by Amazon, and may still apply to print-on-demand titles—even for Prime members.

This Knowledge Base is the only source of valid information
Always provide information strictly from this knowledge base. Do not confirm, promise, or mention any services, awards, or details that are not explicitly included here. If a query cannot be answered based on this knowledge base, escalate the query to a human representative and do not provide an unverified response.

Writing Challenge Availability
Registrations are always open. At any given time, BookLeaf is accepting new participants.
- Writers from India can sign up here: https://www.bookleafpub.in/writing-challenge
- Writers outside India can sign up here: https://www.bookleafpub.com/writing-challenge-us

Bestseller Breakthrough Package – Support & Deliverables

When Will a Publishing Consultant Contact Me?
If you've chosen the Bestseller Breakthrough Package, a dedicated Publishing Consultant will get in touch with you within 5–7 business days from the date of your final submission. They will communicate with you via email.
This consultant will:
- Act as your primary point of contact
- Guide you through every stage of the publishing process
- Address any questions, preferences, or concerns you have along the way

If it's been more than 7 business days and you haven't heard from them, you can always raise a support ticket for a status check.

What If My Assigned Publishing Consultant Isn't Responding?
If your assigned consultant has not been responding to your messages or emails:
- We sincerely apologize for the inconvenience caused.
- Please rest assured that we'll personally inform your consultant to get back to you as soon as possible.
- If you do not receive a response within 48 hours, feel free to reach out again — our support team will escalate the issue immediately.

Where Will My Book Be Published in Bestseller Breakthrough Package?
Under the Bestseller Breakthrough Package, your book is published globally and made available across multiple premium platforms, including:
- All 13 Amazon marketplaces (India, US, UK, Canada, Australia, etc.)
- Flipkart (India)
- Barnes & Noble
- Ingram Distribution Network – enabling access to 30,000+ bookstores and libraries worldwide
- BookLeaf Publishing Store (for the eBook version)

How Is the Copyright Registered Under This Package?
✅ Step 1: Initiation (After Your Paperback Goes Live)
Once your paperback version is published:
- You'll receive a copyright form
- You'll be asked to submit: Copy of PAN Card and/or Aadhaar Card, Basic personal details
- If you're using a pen name, a notarized or e-stamped affidavit may be required

✅ Step 2: Submission & Filing
- We file your copyright application on your behalf via the official Indian Copyright Office portal
- For international authors: We use BookLeaf's Indian address and phone number

✅ Step 3: Government Review & Certification
- Final copyright certificate is typically issued within 6–9 months
- Your work is legally protected from the moment your application is filed

How Many Author Copies Are Included?
Indian Authors:
- Receive 5 complimentary printed author copies with Bestseller Breakthrough Package
- Dispatched 15–20 business days after your book goes live
- Limited Publishing authors get a coupon to purchase one author copy

International Authors:
- Complimentary author copies are not provided
- Can order bulk copies at printing cost

🏆 The 21st Century Emily Dickinson Award
Eligibility: All authors who opt for the Bestseller Breakthrough Package are automatically eligible
Dispatch Timeline: 45–60 business days after your book is live on all platforms
The award is not personalized with author names due to batch processing system.

Royalty Queries & Sales Reports

How to Check Your Sales Report
Visit: https://ebooks.bookleafpub.com/sales-reports
Three report types:
- Live Sales – BookLeaf Store (eBooks only)
- Sales Report – International Author
- Sales Report – Indian Author

Update Schedule: Reports updated monthly after the 15th. First sales report available after 45-60 business days.

When and How Will I Receive My Royalty Payment?
Minimum Thresholds:
- Indian authors: ₹2000
- International authors: $100

Once threshold crossed:
- Inform us via helpdesk
- Receive Razorpay payout link via email
- Enter UPI ID or bank account details
- Payment transferred within 1 minute to 24 hours

For Bestseller Breakthrough authors: On-demand royalty after 30 business days (no minimum threshold)

eBook & Paperback Royalty Structure
📘 eBook Royalty: 80% royalty on net sale price (100% for Bestseller Breakthrough)
📗 Paperback Royalty: 80% of profit after all deductions (100% for Bestseller Breakthrough)

Use Royalty Calculator: https://www.bookleafpub.in/printing-cost-royalty-calculator

Understanding "80% Royalty"
80% refers to 80% of the profit earned, not 80% of the book's listed price.
Deductions include: Printing cost, Platform fees, GST, Handling, Distribution costs, Platform discounts

Understanding "100% Royalty" (Bestseller Breakthrough Only)
You receive the entire profit (after deductions) from each sale.

Author Queries After Publication

How Is the Price of My Book Determined?
Final price set by market strategy team based on:
- Total number of pages
- Cost of paper, printing, and GST
- Cover printing and lamination
- Royalty margin for author

How Are My Poems Protected?
- Confidentiality Agreements with all team members
- Secure encrypted submission systems
- Strict access control
- You retain full ownership
- Regular security audits

Author Copies – Limited Publishing
- Coupon code issued after publication
- Allows one free author copy via BookLeaf bookstore
- Valid only for Indian authors

When Will I Receive My Author Copy Coupon Code?
- Check confirmation email for review link
- Complete review
- Coupon code emailed within 10 business days

Why Am I Being Charged Delivery Fees for My Author Copy?
- Remote/non-standard courier zones may have minimal shipping charges
- We do not profit from this fee

Bulk Orders
Fill request form: https://docs.google.com/forms/d/e/1FAIpQLSeosYqrgnuZIWjbxikzijjk3-3AvRmlEFQgL821vi8sUbTXBw/viewform
- Custom payment link provided
- Delivered in 30–45 business days
- Sold at cost price, doesn't count toward royalties

Can I Get a Draft Copy to Upload on KDP?
No, we do not provide draft files or source files for KDP upload.
If publishing elsewhere, use different ISBN and version without our branding.

Why Is My Book Showing "Out of Stock" on Amazon?
- Amazon system syncing delays
- Typically resolves within 24–48 hours
- If persists beyond 48 hours, raise support ticket

Why Isn't My Book Marked as "Prime" on Amazon?
- We submit Prime request when book lists
- Decision and timeline controlled by Amazon
- Approval may take time

I Have Amazon Prime — Why Am I Still Being Charged Delivery?
- Amazon applies shipping fees on print-on-demand products
- We cannot control or remove Amazon's delivery charges

Post-Publishing Changes (Add-On)
- Update process begins within 4–5 business days
- Receive access to draft
- Re-initiate publishing with updated version

Publishing Certificate Request
Fill form: https://docs.google.com/forms/d/e/1FAIpQLSc2q8Npy9bO3zpDuQKiupQP3ALNp_oYDjiEW7I46iSAF9Z64Q/viewform

Add-On Services & Expert Publishing Options

1. 🌍 Global and Extended Distribution (₹5,499 / $75)
- All 13 Amazon marketplaces
- Barnes & Noble
- Ingram Distribution (30,000+ stores/libraries)

2. 🏆 21st Century Emily Dickinson Award (₹4,499 / $115)
- Trophy and certificate
- Recognition for author profile

3. 🔒 Global Distribution + Award + Copyright (₹8,899 / $135)
- Bundled service including all three

4. 🚀 Bestseller Breakthrough Package (₹11,999 / $249)
- Personal Publishing Manager
- Priority Publishing (half the usual time)
- Global Distribution
- 100% Royalty
- On-demand royalty
- Copyright Registration
- 5 Author Copies (Indian authors)
- Emily Dickinson Award
- Marketing guides

Add-On Payment Links
For Indian Authors:
- Bestseller Breakthrough: https://twa.bookleafpub.in/bestseller-breakthrough-india-dash-before-completion
- Global Dist + Award + Copyright: https://rzp.io/rzp/uVwzD96
- Global Distribution: https://rzp.io/l/3lfxiA4Sg
- Emily Dickinson Award: https://rzp.io/l/KMajEJzA
- Post Publishing Changes: https://rzp.io/l/3mXfNwdA

For International Authors:
- Bestseller Breakthrough: https://twa.bookleafpub.in/bestseller-breakthrough-international-dash-before-completion
- Global Dist + Award + Copyright: https://rzp.io/rzp/YVTtcIY
- Global Distribution: https://rzp.io/rzp/XDyMmRZ
- Emily Dickinson Award: https://pages.razorpay.com/pl_PXhkP2GXp6TJVc/view
- Indian Paperback Distribution: $35 https://www.bookleafpub.com/powerups-new
- Post Publishing Changes: https://rzp.io/rzp/91QXytJT

What Happens After I Submit My Final Draft?

Without Add-Ons (Limited Publishing):
- Published as: Paperback and eBook on BookLeaf Store
- Timeline: 30-45 business days
- Status shows "In Review" then "Published"

With Bestseller Breakthrough Package:
- Timeline: 18-22 business days
- Prioritized in production queue

Dashboard Portal – Submissions, Editing & Layout

Forgot Login Credentials?
Visit: https://dashboard.bookleafpub.in
Click "Forgot Password", enter email, receive reset code

Dashboard Tutorial Video
Watch: https://youtu.be/Z9wxMeo624k

Submitting Hindi Poems
- Use Google Input Tools or Hindi typing software
- Write in separate document and copy-paste
- Double-check formatting after pasting

Acknowledgement, Dedication, and Preface
- Preset and mandatory sections
- Cannot remove or change headings
- Appear as blank pages if left empty

Poem Submission
- Go to Book Interior
- Click "Add" for each poem
- Click "Save as Draft" after each entry
- No image uploads supported

Arranging Poems in Order
- No drag-and-drop support
- Delete and re-upload in desired sequence

Finalizing Poems – Preview Step
- Click "Preview and Finish"
- Shows formatted preview
- Preview loads within few minutes
- Can edit after preview by clicking "Previous Step"

Cover Design Guidelines
📱 Use laptop/desktop (mobile not supported)

Front Cover:
- Browse templates or use solid color
- Upload custom design (must be exactly 5x8 inches)

Back Cover:
- Custom back cover upload not supported
- Choose solid color backgrounds
- Edit text: About the Book (60 words), About the Author (60 words)
- Add profile picture (cannot be removed once uploaded)

Finalizing Cover:
- Click "Preview and Finish"
- Review carefully
- Click "Save and Continue" or "Back to Cover Design"

Login Credentials After Registration

When Will I Receive Login Credentials?
- Emailed within 2 minutes of successful payment
- Check Spam/Junk folder
- Raise support ticket if not received: https://bookleafpublishing.freshdesk.com/support/tickets/new

Returning Authors
- Use existing credentials
- Team must manually enable "Add a New Book" button
- Contact us with registered email for activation

Different Email Registration
- New account created
- No account merging supported
- Each email = unique dashboard

Multiple Challenges
- Only one active challenge at a time
- Complete current before starting new one

Support Contact
Helpdesk: https://bookleafpublishing.freshdesk.com/support/tickets/new
"""

class RAGSystem:
    """Retrieval-Augmented Generation System with Fallback"""
    
    def __init__(self):
        self.knowledge_base = KNOWLEDGE_BASE
        self.embeddings_cache = {}
        self.openai_available = False
        self._check_openai_availability()
    
    def _check_openai_availability(self):
        """Check if OpenAI API is available and has quota"""
        try:
            if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your-openai-key":
                response = openai.embeddings.create(
                    model="text-embedding-3-small",
                    input="test"
                )
                self.openai_available = True
                print("✅ OpenAI API connected successfully")
        except Exception as e:
            self.openai_available = False
            print(f"⚠️  OpenAI API unavailable: {str(e)[:80]}")
            print("📝 Using fallback keyword matching instead")
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI"""
        if not self.openai_available:
            return []
        
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        try:
            response = openai.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=text
            )
            embedding = response.data[0].embedding
            self.embeddings_cache[text] = embedding
            return embedding
        except Exception as e:
            print(f"Embedding error: {str(e)[:80]}")
            self.openai_available = False
            return []
    
    def semantic_search(self, query: str) -> str:
        """Find relevant context from knowledge base"""
        
        if not self.openai_available:
            return self._keyword_search(query)
        
        chunks = [chunk.strip() for chunk in self.knowledge_base.split('\n\n') if chunk.strip()]
        
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return self._keyword_search(query)
        
        chunk_scores = []
        for chunk in chunks:
            chunk_embedding = self.get_embedding(chunk)
            if chunk_embedding:
                similarity = np.dot(query_embedding, chunk_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                )
                chunk_scores.append((chunk, similarity))
        
        if not chunk_scores:
            return self._keyword_search(query)
        
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        relevant_context = "\n\n".join([chunk for chunk, _ in chunk_scores[:3]])
        
        return relevant_context
    
    def _keyword_search(self, query: str) -> str:
        """Fallback keyword-based search when embeddings unavailable"""
        query_lower = query.lower()
        keywords = query_lower.split()
        
        sections = self.knowledge_base.split('\n\n')
        
        section_scores = []
        for section in sections:
            section_lower = section.lower()
            score = sum(1 for keyword in keywords if keyword in section_lower)
            if score > 0:
                section_scores.append((section, score))
        
        section_scores.sort(key=lambda x: x[1], reverse=True)
        relevant_sections = [section for section, _ in section_scores[:3]]
        
        return "\n\n".join(relevant_sections) if relevant_sections else self.knowledge_base[:500]

rag_system = RAGSystem()

class AuthorMatcher:
    """Match queries to author profiles with fuzzy logic"""
    
    def __init__(self):
        self.authors_cache = None
        self.last_cache_update = None
    
    def get_authors(self) -> List[Dict]:
        """Fetch authors from Supabase (with caching)"""
        if self.authors_cache and self.last_cache_update:
            elapsed = (datetime.now() - self.last_cache_update).total_seconds()
            if elapsed < 300:
                return self.authors_cache
        
        try:
            if supabase is not None:
                response = supabase.table('authors').select('*').execute()
                self.authors_cache = response.data
                self.last_cache_update = datetime.now()
                return self.authors_cache
            else:
                return self._get_mock_data()
        except Exception as e:
            print(f"Database error: {e}")
            return self._get_mock_data()
    
    def _get_mock_data(self) -> List[Dict]:
        """Mock data for demonstration"""
        return [
            {
                "email": "sara.johnson@xyz.com",
                "book_title": "Echoes of Silence",
                "final_submission_date": "2024-09-15",
                "book_live_date": "2024-10-20",
                "royalty_status": "processed",
                "isbn": "978-93-12345-67-8",
                "add_on_services": ["Bestseller Package", "PR"],
                "author_copies_sent": True,
                "dashboard_access": True
            },
            {
                "email": "rajesh.kumar@email.com",
                "book_title": "The Digital Revolution",
                "final_submission_date": "2024-08-01",
                "book_live_date": "2024-09-10",
                "royalty_status": "pending_october",
                "isbn": "978-93-98765-43-2",
                "add_on_services": ["Award Submission"],
                "author_copies_sent": False,
                "dashboard_access": True
            },
            {
                "email": "priya.sharma@gmail.com",
                "book_title": "Monsoon Memories",
                "final_submission_date": "2024-10-01",
                "book_live_date": None,
                "royalty_status": "not_yet_live",
                "isbn": "978-93-11111-22-3",
                "add_on_services": ["Bestseller Package"],
                "author_copies_sent": False,
                "dashboard_access": True
            }
        ]
    
    def match_author(self, identifier: str) -> Tuple[Optional[Dict], float]:
        """Match user identifier to author"""
        authors = self.get_authors()
        
        if not authors:
            return None, 0.0
        
        for author in authors:
            if identifier.lower() == author['email'].lower():
                return author, 1.0
        
        matches = []
        for author in authors:
            email_score = fuzz.ratio(identifier.lower(), author['email'].lower()) / 100
            title_score = fuzz.partial_ratio(identifier.lower(), author['book_title'].lower()) / 100
            max_score = max(email_score, title_score)
            matches.append((author, max_score))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        best_match, confidence = matches[0]
        
        return best_match, confidence

author_matcher = AuthorMatcher()

class QueryClassifier:
    """Classify and route user queries"""
    
    QUERY_TYPES = {
        "book_status": ["is my book live", "when will book go live", "book published", "book status"],
        "royalty": ["royalty", "payment", "earnings", "money", "payout"],
        "author_copy": ["author copy", "complimentary copy", "free copies", "physical book"],
        "dashboard": ["dashboard", "login", "access", "credentials", "password"],
        "add_on": ["bestseller", "pr package", "award", "marketing", "add-on"],
        "sales": ["sales", "how many sold", "book performance", "revenue"],
        "timeline": ["timeline", "how long", "when will", "processing time"],
        "isbn": ["isbn", "copyright", "registration"]
    }
    
    def classify_query(self, query: str) -> str:
        """Classify query into predefined categories"""
        query_lower = query.lower()
        
        scores = {}
        for query_type, keywords in self.QUERY_TYPES.items():
            score = max([fuzz.partial_ratio(query_lower, keyword) for keyword in keywords])
            scores[query_type] = score
        
        best_match = max(scores.items(), key=lambda x: x[1])
        
        if best_match[1] < 60:
            return 'general'
        
        return best_match[0]

query_classifier = QueryClassifier()

class ResponseGenerator:
    """Generate contextual responses with GPT fallback to templates"""
    
    def generate_response(
        self, 
        query: str, 
        author_data: Optional[Dict], 
        confidence: float,
        query_type: str
    ) -> Tuple[str, bool]:
        """Generate response using GPT with RAG, fallback to templates"""
        
        if confidence < config.CONFIDENCE_THRESHOLD:
            escalation_msg = (
                "I apologize, but I couldn't confidently identify your account. "
                "I'm connecting you with a human agent who can better assist you. "
                "Please provide your registered email or book title for faster resolution."
            )
            return escalation_msg, True
        
        kb_context = rag_system.semantic_search(query)
        
        openai_available = (
            config.OPENAI_API_KEY and 
            config.OPENAI_API_KEY != "your-openai-key" and
            rag_system.openai_available
        )
        
        if not openai_available:
            return self._generate_template_response(query, author_data, query_type, kb_context)
        
        try:
            system_prompt = f"""You are BookLeaf Publishing's helpful customer support assistant.

You have access to:
1. Author's personal data from our database
2. General knowledge base about our services

Always be:
- Friendly and professional
- Specific with dates and details when available
- Honest if you don't have information
- Encouraging and supportive

Relevant Knowledge Base:
{kb_context}
"""
            
            if author_data:
                author_context = f"""
Author Information:
- Email: {author_data.get('email')}
- Book Title: "{author_data.get('book_title')}"
- Final Submission Date: {author_data.get('final_submission_date', 'Not yet submitted')}
- Book Live Date: {author_data.get('book_live_date', 'Not yet live')}
- Royalty Status: {author_data.get('royalty_status', 'N/A')}
- ISBN: {author_data.get('isbn', 'Being processed')}
- Add-on Services: {', '.join(author_data.get('add_on_services', [])) or 'None'}
- Author Copies Sent: {'Yes' if author_data.get('author_copies_sent') else 'No'}
- Dashboard Access: {'Yes' if author_data.get('dashboard_access') else 'No'}
"""
            else:
                author_context = "No specific author data available."
            
            user_message = f"""
{author_context}

User Query: {query}

Please provide a helpful, specific response based on the author's data and general knowledge base.
"""
            
            response = openai.chat.completions.create(
                model=config.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            return response_text, False
            
        except Exception as e:
            print(f"OpenAI error: {str(e)[:80]}, falling back to templates")
            return self._generate_template_response(query, author_data, query_type, kb_context)
    
    def _generate_template_response(
        self, 
        query: str, 
        author_data: Optional[Dict], 
        query_type: str,
        kb_context: str
    ) -> Tuple[str, bool]:
        """Generate template-based responses when OpenAI unavailable"""
        
        if not author_data:
            return (
                "I couldn't find your account details in our system. "
                "Could you please provide your registered email address or book title? "
                "This will help me assist you better.",
                False
            )
        
        book_title = author_data.get('book_title', 'your book')
        
        if query_type == "book_status":
            if author_data.get('book_live_date'):
                return (
                    f"Great news! Your book '{book_title}' went live on "
                    f"{author_data['book_live_date']}. It's now available on major platforms "
                    f"like Amazon, Flipkart, and our BookLeaf website. You can track real-time "
                    f"sales data through your author dashboard.",
                    False
                )
            else:
                submission_date = author_data.get('final_submission_date', 'your submission')
                return (
                    f"Your book '{book_title}' is currently in our production pipeline. "
                    f"Based on your submission date of {submission_date}, we expect it to go "
                    f"live within the next 2-3 weeks. You'll receive an email notification "
                    f"as soon as it's published. The typical timeline from final submission "
                    f"to going live is 30-45 days.",
                    False
                )
        
        elif query_type == "royalty":
            status = author_data.get('royalty_status', 'processing')
            if status == "processed":
                return (
                    f"Your latest royalty payment for '{book_title}' has been processed! "
                    f"The funds should appear in your registered bank account within 3-5 business days. "
                    f"You can view detailed sales reports and royalty breakdowns in your author dashboard. "
                    f"Royalty reports are generated on the 1st of each month.",
                    False
                )
            elif "pending" in status:
                month = status.replace("pending_", "").capitalize()
                return (
                    f"Your {month} royalty report for '{book_title}' is being prepared and will be "
                    f"available by the 5th of next month. Payment processing follows within 15 days "
                    f"of report generation. The minimum payout threshold is ₹2000 for Indian authors.",
                    False
                )
            else:
                return (
                    f"Royalty reports for '{book_title}' are generated monthly. Since your book "
                    f"isn't live yet, royalties will begin accumulating once sales start. "
                    f"You'll receive 80% of profit for paperbacks and 80% of net sale price for eBooks.",
                    False
                )
        
        elif query_type == "author_copy":
            if author_data.get('author_copies_sent'):
                return (
                    f"Your complimentary author copies for '{book_title}' were shipped to your "
                    f"registered address. If you haven't received them within 7-10 business days, "
                    f"please check with your local post office or contact our support team.",
                    False
                )
            else:
                return (
                    f"Your author copies for '{book_title}' will be shipped within 15-20 business days "
                    f"after your book goes live. Limited Publishing authors receive a coupon code for one free copy.",
                    False
                )
        
        elif query_type == "dashboard":
            if author_data.get('dashboard_access'):
                return (
                    f"Your author dashboard for '{book_title}' is accessible at https://dashboard.bookleafpub.in. "
                    f"If you're having trouble logging in, use the 'Forgot Password' option. "
                    f"For immediate assistance, raise a ticket at https://bookleafpublishing.freshdesk.com/support/tickets/new",
                    False
                )
            else:
                return (
                    f"Your dashboard access for '{book_title}' is being set up. You'll receive "
                    f"login credentials at {author_data.get('email')} within 2 minutes of successful payment. "
                    f"Please check your spam folder if you haven't received it.",
                    False
                )
        
        elif query_type == "add_on":
            services = author_data.get('add_on_services', [])
            if services:
                service_list = ", ".join(services)
                return (
                    f"Your active add-on services for '{book_title}' include: {service_list}. "
                    f"The Bestseller Breakthrough Package includes Personal Publishing Manager, Priority Publishing, "
                    f"Global Distribution, 100% Royalty, Copyright Registration, and Emily Dickinson Award.",
                    False
                )
            else:
                return (
                    f"You don't currently have any add-on services for '{book_title}'. "
                    f"We offer Bestseller Breakthrough Package (₹11,999), Global Distribution (₹5,499), "
                    f"and Emily Dickinson Award (₹4,499). Visit https://www.bookleafpub.in for details.",
                    False
                )
        
        elif query_type == "sales":
            if author_data.get('book_live_date'):
                return (
                    f"Sales data for '{book_title}' is available at https://ebooks.bookleafpub.com/sales-reports. "
                    f"Reports are updated monthly after the 15th. First report available 45-60 business days after book goes live.",
                    False
                )
            else:
                return (
                    f"Sales tracking for '{book_title}' will begin once your book goes live. "
                    f"You'll have access to detailed sales reports and analytics through your dashboard.",
                    False
                )
        
        else:
            return (
                f"Thank you for reaching out about '{book_title}'. "
                f"For specific assistance, please raise a support ticket at https://bookleafpublishing.freshdesk.com/support/tickets/new. "
                f"Our support team will respond within 24 hours (Mon-Sat, 10 AM - 6 PM IST).",
                False
            )

response_generator = ResponseGenerator()

# API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/query', methods=['POST'])
def handle_query():
    """Main query handling endpoint"""
    try:
        data = request.json
        user_query = data.get('query', '').strip()
        user_identifier = data.get('identifier', '').strip()
        channel = data.get('channel', 'API')
        
        if not user_query:
            return jsonify({"error": "Query is required"}), 400
        
        query_type = query_classifier.classify_query(user_query)
        
        matched_author = None
        confidence = 0.0
        
        if user_identifier:
            matched_author, confidence = author_matcher.match_author(user_identifier)
        else:
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, user_query)
            if emails:
                matched_author, confidence = author_matcher.match_author(emails[0])
        
        response_text, should_escalate = response_generator.generate_response(
            user_query,
            matched_author,
            confidence,
            query_type
        )
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'channel': channel,
            'user_identifier': user_identifier,
            'query': user_query,
            'matched_author_email': matched_author['email'] if matched_author else None,
            'confidence': confidence,
            'response': response_text,
            'escalated': should_escalate,
            'error': None
        }
        logger.log_query(log_data)
        
        return jsonify({
            "response": response_text,
            "confidence": confidence,
            "matched_author": matched_author['email'] if matched_author else None,
            "query_type": query_type,
            "escalated": should_escalate,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'channel': channel if 'channel' in locals() else 'API',
            'user_identifier': user_identifier if 'user_identifier' in locals() else None,
            'query': user_query if 'user_query' in locals() else None,
            'matched_author_email': None,
            'confidence': 0.0,
            'response': None,
            'escalated': True,
            'error': error_msg
        }
        logger.log_query(log_data)
        
        return jsonify({
            "error": error_msg,
            "escalated": True
        }), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """Retrieve query logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect(logger.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM query_logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({"logs": logs, "count": len(logs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_test_interface():
    """Serve the test interface HTML file"""
    try:
        with open('test.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({
            "message": "BookLeaf Query Bot API is running!",
            "endpoints": {
                "query": "POST /query - Submit customer query",
                "logs": "GET /logs - View query logs",
                "health": "GET /health - Health check"
            },
            "note": "test.html not found. Place test.html in the same directory as main.py"
        })

def open_browser():
    """Open browser after short delay to allow server startup"""
    import time
    time.sleep(1.5)
    try:
        print("🌐 Opening test interface in browser...")
        webbrowser.open('http://127.0.0.1:5000/')
        print("✅ Browser opened successfully!")
    except Exception as e:
        print(f"⚠️  Could not auto-open browser: {e}")
        print("📝 Please manually visit: http://127.0.0.1:5000/")

if __name__ == '__main__':
    print("🚀 BookLeaf Customer Query Bot Starting...")
    print(f"📊 Confidence Threshold: {config.CONFIDENCE_THRESHOLD * 100}%")
    print(f"🤖 AI Model: {config.MODEL}")
    print("="*50)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
