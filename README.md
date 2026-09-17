# AIONOS — Internal Service Agent

An agentic AI prototype for handling internal employee service requests across IT, HR, and Finance-style workflows.

The agent understands employee issues in natural language, finds the relevant company policy from the supplied knowledge base, checks for risk or missing information, and decides whether to resolve the request, ask a follow-up question, or escalate it.

## Problem

Internal support requests are often written in informal or incomplete language. A support agent needs to:

* Understand what the employee is asking
* Identify the relevant internal policy
* Ask for missing information when required
* Avoid making up company policies
* Escalate sensitive or risky requests
* Create a structured ticket when action is required
* Maintain an audit trail of the decision process
* Show the policy source used for the response

## Solution

The prototype uses an agentic workflow:

```text
Employee Request
       ↓
Understand Issue
       ↓
Find Relevant Policy
       ↓
Risk Check
       ↓
Decide Action
   ↙      ↓       ↘
Resolve  Follow-up  Escalate
       ↓
Create Ticket
       ↓
Employee Response
```

The workflow is implemented using **LangGraph**, with an LLM used for natural-language understanding and decision support.

## Key Features

* Natural-language employee support
* Policy-grounded responses
* Knowledge-base source citation
* Missing-information detection
* Risk checks
* Three decision paths:

  * `RESOLVE`
  * `ASK_FOLLOW_UP`
  * `ESCALATE`
* Structured ticket creation
* Ticket priority and status
* Audit trail of agent steps
* Interactive Streamlit interface
* Employee request processing
* Knowledge Base viewer
* Ticket Queue viewer

## Knowledge Base

The prototype uses the supplied AIONOS assignment data pack as its source of truth.

The knowledge base contains policies covering areas such as:

* Password Reset
* VPN Access
* Laptop Replacement
* Software Installation
* Printer Troubleshooting
* Email Mailbox Quota
* Guest Wi-Fi
* Expense Software Access
* Security Incident Reporting
* WFH Equipment
* Asset Management

The agent is designed to use the supplied policies rather than inventing company-specific rules.

## Example Scenarios

### 1. Password Lockout

**Employee:**

> I am locked out after 6 failed password attempts.

**Agent behavior:**

* Identifies the request as a password reset issue
* Uses KB-01
* Detects that the number of failed attempts exceeds the stated threshold
* Provides the policy-grounded resolution
* Creates a structured ticket where required

### 2. VPN Access

**Employee:**

> I need VPN access.

The agent can ask for additional information when the request does not contain enough context to determine the applicable VPN policy.

For example, contractor VPN access has additional approval requirements.

### 3. Security Incident

**Employee:**

> I received a phishing email and forwarded it to my teammates.

The agent identifies this as a security-sensitive request and routes it toward escalation using the supplied security incident policy.

## Architecture

```text
                    ┌─────────────────────┐
                    │   Employee Input    │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  Understand Issue   │
                    │     LLM + Python    │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │    Get Policy       │
                    │  AIONOS Knowledge    │
                    │       Base          │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │     Risk Check      │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │    Decide Action    │
                    │ Resolve / Follow-up │
                    │     / Escalate      │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   Create Ticket     │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Employee Response   │
                    └─────────────────────┘

              ┌──────────────────────────────┐
              │      Data & Knowledge       │
              │                              │
              │  Knowledge Base + Tickets   │
              └──────────────────────────────┘
```

## Tech Stack

* **Python** — backend and agent logic
* **Streamlit** — interactive web interface
* **LangGraph** — agent workflow orchestration
* **Groq API** — LLM inference
* **GPT-OSS-120B** — language model
* **Pandas** — data and ticket display
* **python-dotenv** — environment configuration

## Project Structure

```text
Aionos---Service-Agent/
│
├── app.py
├── agent.py
├── data.py
├── policies.py
├── requirements.txt
├── README.md
└── .gitignore
```

### File Responsibilities

**`app.py`**

Streamlit application and user interface.

**`agent.py`**

Agent workflow, LLM calls, policy routing, risk checks, decisions, tickets, and audit trail.

**`data.py`**

Employee requests, ticket queue data, and supplied assignment data.

**`policies.py`**

Knowledge-base articles and policy mappings.

**`requirements.txt`**

Python dependencies required to run the application.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Khushi-dotcom03/Aionos---Service-Agent.git
cd Aionos---Service-Agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Groq API key

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key_here
```

Do **not** commit or upload the `.env` file.

The repository includes `.gitignore` rules to prevent the API key from being committed.

### 5. Run the application

```bash
streamlit run app.py
```

The Streamlit interface will open in the browser.

## AI Usage

The LLM is used primarily for:

1. Understanding natural-language employee requests
2. Extracting relevant information from the request
3. Supporting the final action decision

The application code controls the workflow, policy mapping, risk checks, ticket structure, and output handling.

This separation helps keep company policy data grounded in the supplied assignment material.

## Agent Workflow

The agent follows these stages:

1. **Understand Issue**
   Classifies the employee request and extracts useful entities.

2. **Find Policy**
   Maps the identified category to the relevant supplied KB article.

3. **Risk Check**
   Checks for missing information, sensitive requests, and other risk conditions.

4. **Decide Action**
   Selects `RESOLVE`, `ASK_FOLLOW_UP`, or `ESCALATE`.

5. **Create Ticket**
   Creates a structured ticket when the workflow requires an actionable record.

6. **Respond**
   Returns the result to the employee along with the relevant KB source.

## Limitations

This is a prototype built for the AIONOS Agentic AI Factory assignment.

Current limitations include:

* Local/in-memory ticket storage
* No enterprise authentication
* No direct connection to a real ITSM system
* Supplied policy data is stored locally rather than in a production retrieval system
* LLM usage depends on API availability and rate limits
* Production deployment would require stronger security, monitoring, evaluation, and access controls

## Future Improvements

* Integration with ServiceNow or another ITSM platform
* Enterprise authentication and role-based access
* Persistent database-backed tickets and audit logs
* Retrieval-Augmented Generation (RAG) for larger policy collections
* Human approval workflows
* Automated policy evaluation and test suites
* Monitoring and observability
* Support for additional internal departments and workflows

## Assignment Context

This project was developed as a prototype for the **AIONOS Agentic AI Factory — Assignment 2: Internal Service Agent**.

The prototype demonstrates how an agent can combine LLM-based language understanding with deterministic workflow logic and policy grounding to handle internal employee service requests.
