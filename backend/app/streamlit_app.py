import os
import uuid

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="Data Dictionary Chatbot",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state ─────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "schema_filter" not in st.session_state:
    st.session_state.schema_filter = None


# ── Helpers ───────────────────────────────────────────────────────
def _send_feedback(trace_id: str, rating: str) -> None:
    try:
        requests.post(
            f"{API_BASE}/feedback",
            json={"trace_id": trace_id, "rating": rating},
            timeout=3,
        )
    except Exception:
        pass


def _render_response(data: dict) -> None:
    if data.get("sql"):
        st.code(data["sql"], language="sql")

    if data.get("explanation"):
        st.info(data["explanation"])

    if data.get("join_suggestions"):
        with st.expander(f"Join suggestions ({len(data['join_suggestions'])})"):
            for j in data["join_suggestions"]:
                st.code(
                    f"{j['join_type']} JOIN {j['to_table']} "
                    f"ON {j['from_table']}.{j['join_key']} "
                    f"= {j['to_table']}.{j['join_key']}",
                    language="sql",
                )
                if j.get("description"):
                    st.caption(j["description"])

    if data.get("retrieved_context"):
        with st.expander(f"Source columns used ({len(data['retrieved_context'])})"):
            for ctx in data["retrieved_context"]:
                st.markdown(
                    f"**{ctx['schema_name']}.{ctx['table_name']}."
                    f"{ctx['column_name']}** "
                    f"`{ctx['data_type']}` — {ctx['description']}"
                )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Confidence", f"{data.get('confidence', 0):.0%}")
    c2.metric("Latency",    f"{data.get('latency_ms', 0)} ms")
    c3.metric("Trace ID",   (data.get("trace_id") or "")[:8] + "…")
    c4.metric("Cols used",  len(data.get("retrieved_context", [])))

    tid = data.get("trace_id", str(uuid.uuid4()))
    col_a, col_b, _ = st.columns([1, 1, 6])
    if col_a.button("👍 Good", key=f"good_{tid}"):
        _send_feedback(tid, "good")
        st.toast("Thanks for the feedback!")
    if col_b.button("👎 Bad", key=f"bad_{tid}"):
        _send_feedback(tid, "bad")
        st.toast("Noted — helps improve accuracy.")


# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("Data Dictionary")
    st.caption(f"Session: `{st.session_state.session_id[:8]}…`")

    st.subheader("Filter by schema")
    schemas = ["All schemas", "Sales", "HR", "Finance"]
    selected = st.radio("Schema", schemas, index=0, label_visibility="collapsed")
    st.session_state.schema_filter = None if selected == "All schemas" else selected

    st.divider()
    st.subheader("Available tables")
    try:
        params = {}
        if st.session_state.schema_filter:
            params["schema"] = st.session_state.schema_filter
        resp = requests.get(f"{API_BASE}/tables", params=params, timeout=3)
        if resp.ok:
            for t in resp.json():
                with st.expander(f"{t['schema_name']}.{t['table_name']}"):
                    st.caption(t.get("description", "No description"))
        else:
            st.warning(f"API error {resp.status_code}")
    except Exception:
        st.info("Backend starting up…")

    st.divider()
    if st.button("New conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()


# ── Main chat ─────────────────────────────────────────────────────
st.title("Data Dictionary Chatbot")
st.caption("Ask in plain English — get back SQL with join suggestions.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.write(msg["content"])
        else:
            _render_response(msg["content"])

if prompt := st.chat_input(
    "e.g. 'Show me top 10 customers by revenue in Q1 2024'"
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/chat",
                    json={
                        "question": prompt,
                        "session_id": st.session_state.session_id,
                        "schema_filter": st.session_state.schema_filter,
                    },
                    timeout=30,
                )
                if resp.ok:
                    data = resp.json()
                    _render_response(data)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": data}
                    )
                else:
                    st.error(f"API error {resp.status_code}: {resp.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach backend. Is docker-compose up?")
            except Exception as e:
                st.error(f"Unexpected error: {e}")