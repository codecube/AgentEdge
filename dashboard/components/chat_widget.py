"""Sidebar chat widget — ask natural-language questions about sensor data.

Uses A2A ``message/send`` (JSON-RPC) for chat with the Mac Mini agent.
Falls back to the REST ``/api/chat`` endpoint for a fast data-only answer.
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
    if question:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": question})

        # Send via A2A message/send
        answer = _send_question(macmini_url, question)
        st.session_state.chat_history.append({"role": "agent", "content": answer})

        # Trim to last 20 exchanges (40 messages)
        if len(st.session_state.chat_history) > 40:
            st.session_state.chat_history = st.session_state.chat_history[-40:]

        st.rerun()


def _send_question(macmini_url: str, question: str) -> str:
    """Send question via A2A message/send and return the agent's reply."""
    response = send_a2a_message(macmini_url, question, timeout=30.0)
    return extract_agent_reply(response)


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
    """Parse <think> tags: grey for thinking, cyan for answer."""
    import re as _re

    think_match = _re.search(r"<think>(.*?)</think>(.*)", text, _re.DOTALL)
    if think_match:
        thinking = _escape(think_match.group(1).strip())
        answer = _escape(think_match.group(2).strip())
        parts = []
        if thinking:
            parts.append(
                f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.75rem;'
                f' color: #64748b; font-style: italic;">{thinking}</span>'
            )
        if answer:
            parts.append(
                f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;'
                f' color: #00f0ff;">{answer}</span>'
            )
        return "<br>".join(parts)
    # No thinking tags — plain text answer in cyan
    return (
        f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;'
        f' color: #00f0ff;">{_escape(text)}</span>'
    )
