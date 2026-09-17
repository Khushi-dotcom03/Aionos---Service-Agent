import os
import streamlit as st
import pandas as pd

from dotenv import load_dotenv

from policies import KB_ARTICLES
from data import EMPLOYEE_REQUESTS, TICKET_QUEUE_SEED
from agent import run_agent


load_dotenv()

st.set_page_config(
    page_title="Veridian IT Service Agent",
    page_icon="🛠️",
    layout="wide"
)


# -------------------- session state --------------------

if "processed" not in st.session_state:
    st.session_state.processed = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "chat_state" not in st.session_state:
    st.session_state.chat_state = None

if "all_tickets" not in st.session_state:
    st.session_state.all_tickets = list(TICKET_QUEUE_SEED)


# -------------------- page --------------------

st.title(" AIONOS — Internal IT Service Agent")



if not os.environ.get("GROQ_API_KEY"):
    st.error("GROQ_API_KEY is not set.")
    st.stop()


tab_chat, tab_batch, tab_kb, tab_tickets = st.tabs(
    [
        " Live Chat",
        " Employee Requests",
        " Knowledge Base",
        " Tickets"
    ]
)


# =========================================================
# LIVE CHAT
# =========================================================

with tab_chat:

    st.subheader("Talk to the agent")

    # Show complete conversation first
    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    # -----------------------------------------------------
    # Input MUST be at the bottom
    # -----------------------------------------------------

    user_msg = st.chat_input("Drop your issue here...")


    if user_msg:

        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_msg
        })


        # Send message to agent
        result = run_agent(
            user_msg,
            "Live Chat User",
            "livechat@veridiancorp.example",
            history=st.session_state.chat_history[:-1]
        )


        st.session_state.chat_state = result


        # -------------------------------------------------
        # Ticket
        # -------------------------------------------------

        ticket = result.get("ticket")

        if ticket:

            ticket_ids = {
                t.get("id")
                for t in st.session_state.all_tickets
                if t
            }

            if ticket.get("id") not in ticket_ids:
                st.session_state.all_tickets.append(ticket)


        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        reply = result.get("response_text", "")

        if (
            result.get("action") == "ASK_FOLLOW_UP"
            and result.get("follow_up_question")
        ):
            reply = result["follow_up_question"]


        # -------------------------------------------------
        # Source + ticket information
        # -------------------------------------------------

        sources = result.get("kb_sources", [])

        if sources:
            source_text = ", ".join(sources)
        else:
            source_text = "No matching policy"


        if ticket:

            reply += (
                f"\n\n*Source: {source_text} · "
                f"Ticket {ticket['id']} ({ticket['status']})*"
            )

        else:

            reply += (
                f"\n\n*Source: {source_text}*"
            )


        # Add assistant response to conversation
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": reply
        })


        # -------------------------------------------------
        # Audit trail for THIS chat
        # -------------------------------------------------

        with st.expander("View audit trail for this request"):

            for step in result.get("audit_trail", []):

                st.markdown(
                    f"`{step['time']}` "
                    f"**{step['step']}** — "
                    f"{step['detail']}"
                )


        # Rerun so the input moves below the new message
        st.rerun()


# =========================================================
# EMPLOYEE REQUESTS
# =========================================================

with tab_batch:

    st.subheader("Employee requests — REQ-01 to REQ-15")


    if st.button("▶ Process all 15 requests", type="primary"):

        progress = st.progress(0)

        for i, req in enumerate(EMPLOYEE_REQUESTS):

            progress.progress(
                (i + 1) / len(EMPLOYEE_REQUESTS)
            )

            result = run_agent(
                req["message"],
                req["employee"],
                req["email"]
            )

            st.session_state.processed[req["id"]] = result


            # Only save a ticket if one was actually created
            ticket = result.get("ticket")

            if ticket:

                ticket_ids = {
                    t.get("id")
                    for t in st.session_state.all_tickets
                    if t
                }

                if ticket.get("id") not in ticket_ids:
                    st.session_state.all_tickets.append(ticket)


        progress.empty()

        st.success("All requests processed.")


    # Show results

    for req in EMPLOYEE_REQUESTS:

        result = st.session_state.processed.get(req["id"])


        with st.expander(
            f"{req['id']} — {req['employee']}: {req['message']}"
        ):

            if not result:

                st.info(
                    "Not processed yet. "
                    "Click the button above."
                )

                continue


            action = result.get("action", "UNKNOWN")


            if action == "RESOLVE":
                st.success("RESOLVED")

            elif action == "ASK_FOLLOW_UP":
                st.warning("FOLLOW-UP NEEDED")

            else:
                st.error("ESCALATED")


            st.write(
                "**Source:**",
                ", ".join(result.get("kb_sources", []))
                or "No matching policy"
            )


            st.write(
                "**Priority:**",
                result.get("priority", "Medium")
            )


            if result.get("risk_flags"):

                st.write(
                    "**Risk:**",
                    ", ".join(result["risk_flags"])
                )


            st.write(
                "**Agent response:**",
                result.get("response_text", "")
            )


            if result.get("follow_up_question"):

                st.write(
                    "**Follow-up:**",
                    result["follow_up_question"]
                )


            if result.get("escalation_target"):

                st.write(
                    "**Escalated to:**",
                    result["escalation_target"]
                )


            # Ticket may not exist for follow-up
            ticket = result.get("ticket")

            if ticket:

                st.write(
                    f"**Ticket:** {ticket['id']} — "
                    f"{ticket['status']}"
                )

            else:

                st.write(
                    "**Ticket:** None — waiting for employee response"
                )


            # Audit trail
            with st.expander("View audit trail"):

                for step in result.get("audit_trail", []):

                    st.markdown(
                        f"`{step['time']}` "
                        f"**{step['step']}** — "
                        f"{step['detail']}"
                    )


# =========================================================
# KNOWLEDGE BASE
# =========================================================

with tab_kb:

    st.subheader("Knowledge Base")

    st.write(
        "These are the policies supplied in the assignment data pack."
    )


    for kb_id, article in KB_ARTICLES.items():

        st.markdown(
            f"### {kb_id} — {article['title']}"
        )

        st.write(article["text"])

        st.divider()


# =========================================================
# TICKETS
# =========================================================

with tab_tickets:

    st.subheader("Ticket Queue")


    st.write("### Existing tickets")

    seed_df = pd.DataFrame(TICKET_QUEUE_SEED)

    st.dataframe(
        seed_df,
        use_container_width=True,
        hide_index=True
    )


    new_tickets = [
        ticket
        for ticket in st.session_state.all_tickets
        if ticket not in TICKET_QUEUE_SEED
    ]


    st.write("### Tickets created by the agent")


    if new_tickets:

        new_df = pd.DataFrame(new_tickets)

        st.dataframe(
            new_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No new tickets have been created yet."
        )

