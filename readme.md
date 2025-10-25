# 🚀📚 BookLeaf Publishing - AI Customer Query Bot & Identity Unification

<div align="center">

![BookLeaf Logo](https://img.shields.io/badge/BookLeaf-Publishing-teal?style=for-the-badge)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange?style=for-the-badge&logo=openai)](https://openai.com/)
[![License](https://img.shields.io/badge/License-Assignment-red?style=for-the-badge)](LICENSE)

</div>

---

## 🌟 **OVERVIEW**

> Multi-channel Customer Query Bot & Identity Unification system for **BookLeaf Publishing** using modern AI and fuzzy matching algorithms.  
> Efficiently handle author queries across email, WhatsApp, Instagram, and unify identities with high accuracy.

---

## ⚡ **FEATURES**

### 🤖 Customer Query Bot
- AI-powered GPT-3.5-turbo queries with fallback templates
- Retrieval-Augmented Generation (RAG) with full BookLeaf knowledge base
- Multi-channel input: Email | WhatsApp | Instagram | API
- Confidence-based routing & escalation system (80% threshold)
- SQLite logging and detailed query analytics
- Auto-launch browser test interface (`test.html`)

### 🔗 Identity Unification
- Fuzzy matching on email, phone, name, social handles
- Weighted scoring for robust confidence measures
- Auto-matching, manual review, or new profile creation routing
- Profile merging & alternative email tracking
- Real-time unification reports and stats

---

## 🛠️ **TECH STACK**

| Component         | Technology         | Purpose                         |
|-------------------|--------------------|--------------------------------|
| Backend           | Python 3.12, Flask | API & logic                    |
| AI/ML             | OpenAI GPT-3.5     | Query understanding & response |
| Embeddings & RAG  | OpenAI Embeddings, NumPy | Contextual semantic search   |
| Identity Matching | fuzzywuzzy, thefuzz| Author identity matching        |
| Database          | SQLite, Supabase   | Logging & author data           |
| Frontend          | HTML/CSS/JS        | Test interface                  |

---

## 🚀 **GETTING STARTED**

### 📋 Prerequisites
- Python 3.12+  
- OpenAI API key (optional - fallback enabled)  
- Optional Supabase project for author data  

### 💾 Installation


git clone https://github.com/yourusername/bookleaf-query-bot.git
cd bookleaf-query-bot
pip install -r requirements.txt

Configuration:
Create `.env` file in the project root:
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url (optional)
SUPABASE_KEY=your_supabase_key (optional)

Running the Bots
----------------

Customer Query Bot:
python main.py

- Opens a browser window with test interface at http://127.0.0.1:5000
- Supports POST /query and GET /logs endpoints

Identity Unification Demo:
python identity_unifier.py

- Runs sample identity matching tests with confidence and action outputs

API Reference
-------------

POST /query
Submit a customer query to get responses.

Request body example:
{
  "query": "When will I get my royalty?",
  "identifier": "sara.johnson@xyz.com",
  "channel": "Email"
}

Response example:
{
  "response": "Your royalty payment has been processed...",
  "confidence": 0.90,
  "matched_author": "sara.johnson@xyz.com",
  "query_type": "royalty",
  "escalated": false,
  "timestamp": "2025-10-25T13:30:00"
}

GET /logs
Fetch recent query logs.

Usage Examples
--------------

- Query: "Is my book live yet?" → Provides book publication status if known
- Query: "How do I get author copies?" → Returns shipping status and policy
- Query: "Where is my royalty payment?" → Gives payment processing details
- Query: Unknown user email → Escalates to human support

Design Overview
---------------

Multi-channel Input → Query Classification → Author Matching → RAG Semantic Search → Response Generation → Confidence Routing → Logging

Identity Unification:
- Normalize and score email, phone, name, social handles
- Aggregate weighted scores → Determine matching action
- Create, merge, or review profiles accordingly

Future Enhancements
-------------------

- Vector DB (Pinecone/Weaviate) for scalable semantic search
- Fine-tuned GPT models on BookLeaf data
- Multilingual support including Hindi and regional languages
- Voice-based query processing (Whisper API)
- Analytics dashboard for query trends and escalation
- Rate limiting and authentication for API security

Contribution & Support
----------------------

Feel free to contribute improvements or reach out for support.

- Email: harshbisht7456@gmail.com  
- GitHub: https://github.com/HARSH74561/bookleaf-query-bot  
- Support tickets: https://bookleafpublishing.freshdesk.com/support/tickets/new

License
-------

This project is submitted as part of an assignment evaluation for BookLeaf Publishing. Rights retained by developer.

Acknowledgements
----------------

- OpenAI for GPT and Embeddings APIs  
- Supabase for backend database  
- fuzzywuzzy and thefuzz for identity matching  
- BookLeaf Publishing for the dataset and domain

Thank you for reviewing this project!
