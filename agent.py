import os
import json
import re
from datetime import datetime

from groq import Groq
from langgraph.graph import StateGraph, END

from policies import KB_ARTICLES, CATEGORY_TO_KB
from data import TICKET_QUEUE_SEED, TODAY


MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def get_client():
    key = os.environ.get("GROQ_API_KEY")

    if not key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    return Groq(api_key=key)


def ask_llm(system_prompt, user_message):

    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1,
        max_tokens=700,
        response_format={"type": "json_object"}
    )

    text = response.choices[0].message.content.strip()

    # Remove markdown code fences
    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            f"LLM did not return JSON.\n\nModel response:\n{text}"
        )

    json_text = text[start:end + 1]

    try:
        return json.loads(json_text)

    except json.JSONDecodeError:

        # Sometimes the model puts an invalid backslash in a string.
        # Try removing those invalid escapes.
        json_text = re.sub(
            r'\\(?!["\\/bfnrtu])',
            r'\\\\',
            json_text
        )

        try:
            return json.loads(json_text)

        except json.JSONDecodeError:
            raise ValueError(
                "LLM returned invalid JSON.\n\n"
                f"Model response:\n{text}"
            )



def add_log(state, step, detail):
    state.setdefault("audit_trail", []).append({
        "step": step,
        "detail": detail,
        "time": datetime.now().strftime("%H:%M:%S")
    })


# ---------------------------------------------------------
# 1. Understand the employee's message
# ---------------------------------------------------------

def understand_issue(state):

    categories = list(CATEGORY_TO_KB.keys())

    prompt = f"""
You are an IT support intake assistant.

Classify the employee's issue into ONE of these categories:

{categories}

Also extract these details if they are present:
- asset_age_years
- failed_login_attempts
- wfh_days_per_week
- is_contractor
- forwarded_security_issue

If an important detail is missing, put it in missing_info.

Do not invent information.

Return ONLY JSON:

{{
  "category": "...",
  "entities": {{}},
  "missing_info": []
}}
"""

    history = state.get("history", [])

    previous = ""
    if history:
        previous = "\nPrevious conversation:\n"
        for item in history:
            previous += f"{item['role']}: {item['content']}\n"

    result = ask_llm(
        prompt,
        state["message"] + previous
    )

    state["category"] = result.get("category", "unclear")
    state["entities"] = result.get("entities", {})
    state["missing_info"] = result.get("missing_info", [])

    add_log(
        state,
        "Understand issue",
        f"Category: {state['category']}"
    )

    return state


# ---------------------------------------------------------
# 2. Get the relevant policy
# ---------------------------------------------------------

def get_policy(state):

    kb_ids = CATEGORY_TO_KB.get(
        state["category"],
        []
    )

    state["kb_sources"] = kb_ids

    if kb_ids:
        policy_text = []

        for kb_id in kb_ids:
            article = KB_ARTICLES[kb_id]

            policy_text.append(
                f"{kb_id}: {article['title']}\n"
                f"{article['text']}"
            )

        state["policy"] = "\n\n".join(policy_text)

    else:
        state["policy"] = "No matching policy found."

    add_log(
        state,
        "Find policy",
        f"Sources: {', '.join(kb_ids) if kb_ids else 'None'}"
    )

    return state


# ---------------------------------------------------------
# 3. Basic deterministic checks
# ---------------------------------------------------------

def check_risk(state):

    flags = []

    category = state["category"]
    entities = state.get("entities", {})

    if not state["kb_sources"]:
        flags.append("No policy found")

    if state.get("missing_info"):
        flags.append("Missing information")

    if category == "security_incident":
        if entities.get("forwarded_security_issue"):
            flags.append("Security incident was forwarded")

    if category == "admin_access_request":
        flags.append("Elevated access request")

    if category == "vpn_access":
        if entities.get("is_contractor"):
            flags.append("Contractor VPN requires manager approval")

    state["risk_flags"] = flags

    add_log(
        state,
        "Risk check",
        ", ".join(flags) if flags else "No major risk found"
    )

    return state


# ---------------------------------------------------------
# 4. Decide what to do
# ---------------------------------------------------------

def decide(state):

    prompt = """
You are an IT support decision assistant.

Use ONLY the policy provided below.

Choose one action:

RESOLVE
- The request can be answered using the policy.

ASK_FOLLOW_UP
- One important piece of information is missing.

ESCALATE
- A human team, manager, Finance, IT Security, or another authority is required.
- Or there is no applicable policy.

Return ONLY JSON:

{
  "action": "RESOLVE",
  "response": "...",
  "follow_up": null,
  "escalation_target": null
}
"""

    user = f"""
Employee issue:
{state['message']}

Category:
{state['category']}

Details:
{json.dumps(state.get('entities', {}))}

Missing information:
{state.get('missing_info', [])}

Risk flags:
{state.get('risk_flags', [])}

Policy:
{state['policy']}
"""

    result = ask_llm(prompt, user)

    state["action"] = result.get("action", "ESCALATE")
    state["response_text"] = result.get("response", "")
    state["follow_up_question"] = result.get("follow_up")
    state["escalation_target"] = result.get("escalation_target")

    # Don't let the LLM decide priority.
    state["priority"] = get_priority(state)

    add_log(
        state,
        "Decision",
        f"Action: {state['action']}, Priority: {state['priority']}"
    )

    return state


# ---------------------------------------------------------
# Priority is controlled by Python
# ---------------------------------------------------------

def get_priority(state):

    category = state["category"]
    message = state["message"].lower()
    risk = state.get("risk_flags", [])

    # High
    if category == "security_incident":
        return "High"

    if category == "admin_access_request":
        return "High"

    if "urgent" in message or "immediately" in message:
        return "High"

    # Low
    if category == "guest_wifi":
        return "Low"

    if category == "password_reset":
        return "Low"

    # Medium
    return "Medium"


# ---------------------------------------------------------
# 5. Create a ticket ONLY when required
# ---------------------------------------------------------

ticket_number = 1052


def create_ticket(state):

    global ticket_number

    ticket_id = f"TK-{ticket_number}"
    ticket_number += 1

    if state["action"] == "ESCALATE":
        if state.get("escalation_target"):
            status = f"Escalated to {state['escalation_target']}"
        else:
            status = "Escalated to human reviewer"

    else:
        status = "Resolved"

    state["ticket"] = {
        "id": ticket_id,
        "employee": state.get("employee_name", "Live Chat User"),
        "email": state.get("employee_email", ""),
        "date": TODAY,
        "category": state["category"],
        "issue_summary": state["message"],
        "kb_sources_cited": state["kb_sources"],
        "risk_flags": state["risk_flags"],
        "action": state["action"],
        "status": status,
        "priority": state["priority"],
        "response_to_employee": state["response_text"]
    }

    add_log(
        state,
        "Create ticket",
        f"{ticket_id} created"
    )

    return state


# ---------------------------------------------------------
# Graph
# ---------------------------------------------------------

def after_decision(state):

    # IMPORTANT:
    # Asking a question is not a ticket.
    if state["action"] == "ASK_FOLLOW_UP":
        return "finish"

    return "ticket"


def build_graph():

    graph = StateGraph(dict)

    graph.add_node("understand", understand_issue)
    graph.add_node("policy", get_policy)
    graph.add_node("risk", check_risk)
    graph.add_node("decide", decide)
    graph.add_node("ticket", create_ticket)

    graph.set_entry_point("understand")

    graph.add_edge("understand", "policy")
    graph.add_edge("policy", "risk")
    graph.add_edge("risk", "decide")

    graph.add_conditional_edges(
        "decide",
        after_decision,
        {
            "finish": END,
            "ticket": "ticket"
        }
    )

    graph.add_edge("ticket", END)

    return graph.compile()


AGENT = build_graph()


def run_agent(
    message,
    employee_name="Live Chat User",
    employee_email="livechat@veridian-corp.example",
    history=None
):

    state = {
        "message": message,
        "employee_name": employee_name,
        "employee_email": employee_email,
        "history": history or [],
        "audit_trail": []
    }

    return AGENT.invoke(state)

