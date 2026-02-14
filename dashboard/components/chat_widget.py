"""Sidebar chat widget — ask natural-language questions about sensor data.

Uses A2A ``message/send`` (JSON-RPC) for chat with the Mac agent.
"""
from __future__ import annotations

import streamlit as st

from dashboard.a2a_client import extract_agent_reply, send_a2a_message


def render_chat_widget(macmini_url: str):
    """Render the chat widget inside st.sidebar."""
    st.markdown(
        '<div class="section-header">Agent Chat</div>',
        unsafe_allow_html=True,
    )

    # Init history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render existing messages
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            _render_user_message(msg["content"])
        else:
            _render_agent_message(msg["content"])

    # Chat input
    question = st.chat_input()
    if question and question != st.session_state.get("_last_q"):
        st.session_state._last_q = question
        st.session_state.chat_history.append({"role": "user", "content": question})
        answer = _send_question(macmini_url, question)
        st.session_state.chat_history.append({"role": "agent", "content": answer})

        # Trim to last 20 exchanges (40 messages)
        if len(st.session_state.chat_history) > 40:
            st.session_state.chat_history = st.session_state.chat_history[-40:]

        st.rerun()


def _send_question(macmini_url: str, question: str) -> str:
    """Send question via A2A message/send and return the agent's reply."""
    response = send_a2a_message(macmini_url, question, timeout=30.0)
    reply = extract_agent_reply(response)

    # Record the exchange in the Mac's A2A message log so the
    # conversation panel shows it.
    _record_message(macmini_url, question, reply)

    return reply


def _record_message(macmini_url: str, question: str, answer: str):
    """POST the chat exchange to the Mac so it appears in the A2A panel."""
    from datetime import datetime, timezone

    import httpx

    ts = datetime.now(timezone.utc).isoformat()
    try:
        httpx.post(
            f"{macmini_url}/api/record-message",
            json={"question": question, "answer": answer, "timestamp": ts},
            timeout=3.0,
        )
    except Exception:
        pass


def _render_user_message(content: str):
    """Render a user message with amber left border."""
    safe = _escape(content)
    st.markdown(
        f"""<div style="border-left: 3px solid #ffaa00; padding: 8px 12px;
            margin: 6px 0; background: #ffaa0010; border-radius: 0 4px 4px 0;
            word-wrap: break-word; overflow-wrap: break-word;">
            <span style="font-family: 'Outfit', sans-serif; font-size: 0.6rem;
                font-weight: 600; color: #ffaa00; text-transform: uppercase;
                letter-spacing: 0.08em;">You</span><br>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
                color: #e2e8f0;">{safe}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_agent_message(content: str):
    """Render an agent response with cyan left border."""
    safe = _format_agent_content(content)
    st.markdown(
        f"""<div style="border-left: 3px solid #00f0ff; padding: 8px 12px;
            margin: 6px 0; background: #00f0ff10; border-radius: 0 4px 4px 0;
            word-wrap: break-word; overflow-wrap: break-word;">
            <span style="font-family: 'Outfit', sans-serif; font-size: 0.6rem;
                font-weight: 600; color: #00f0ff; text-transform: uppercase;
                letter-spacing: 0.08em;">Agent</span><br>
            {safe}
        </div>""",
        unsafe_allow_html=True,
    )


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def _format_agent_content(text: str) -> str:
    """Format agent text — strip <think> tags if present."""
    import re as _re

    think_match = _re.search(r"<think>(.*?)</think>(.*)", text, _re.DOTALL)
    if think_match:
        answer = _escape(think_match.group(2).strip())
        if answer:
            return (
                f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;'
                f' color: #00f0ff;">{answer}</span>'
            )
    # Plain text
    return (
        f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;'
        f' color: #00f0ff;">{_escape(text)}</span>'
    )
