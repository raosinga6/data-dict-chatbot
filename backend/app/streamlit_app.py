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
if "selected_table" not in st.session_state:
    st.session_state.selected_table = None
if "tables_cache" not in st.session_state:
    st.session_state.tables_cache = []


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


def _fetch_tables() -> list:
    try:
        params = {}
        if st.session_state.schema_filter:
            params["schema"] = st.session_state.schema_filter
        resp = requests.get(f"{API_BASE}/tables", params=params, timeout=5)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return []

def _fetch_columns(schema_name: str, table_name: str) -> dict:
    urls = [
        f"{API_BASE}/tables/{schema_name}/{table_name}/columns",
        f"{API_BASE}/tables/{table_name}/columns",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=5)
            #st.write(f"DEBUG: {url} → {resp.status_code}")  # temporary
            if resp.ok:
                data = resp.json()
                #st.write(f"DEBUG response: {data}")          # temporary
                if isinstance(data, list):
                    return {"columns": data, "joins": []}
                if isinstance(data, dict):
                    return data
        except Exception:
            #st.write(f"DEBUG error: {e}")                    # temporary
            continue
    return {}


def _render_column_detail(col: dict) -> None:
    """Render a single column row with type badges and PII flag."""
    badges = []
    if col.get("is_pk"):
        badges.append("🔑 PK")
    if col.get("is_fk"):
        badges.append("🔗 FK")
    if col.get("pii"):
        badges.append("🔴 PII")

    badge_str = "  ".join(badges)
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(
            f"**{col['name']}**"
            + (f"  {badge_str}" if badge_str else "")
        )
        if col.get("description"):
            st.caption(col["description"])
        if col.get("business_name") and col["business_name"] != col["name"]:
            st.caption(f"Business name: *{col['business_name']}*")
    with col2:
        st.code(col.get("data_type", "unknown"), language=None)
        nullable = "nullable" if col.get("is_nullable", True) else "NOT NULL"
        st.caption(nullable)
        if col.get("examples"):
            st.caption(f"e.g. {', '.join(str(x) for x in col['examples'][:3])}")


def _render_joins(joins: list) -> None:
    """Render join relationships as SQL snippets."""
    if not joins:
        st.caption("No outbound joins defined")
        return
    for j in joins:
        cardinality = j.get("cardinality", "")
        cardinality_icon = {
            "one_to_many":  "1→N",
            "many_to_many": "N→N",
            "one_to_one":   "1→1",
        }.get(cardinality, "→")
        st.caption(f"{cardinality_icon}  **{j['right_table']}**")
        st.code(
            f"{j.get('join_type','INNER').upper()} JOIN {j['right_table']} "
            f"ON this.{j['left_col']} = {j['right_table']}.{j['right_col']}",
            language="sql",
        )


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
    st.title("🗄️ Data Dictionary")
    st.caption(f"Session: `{st.session_state.session_id[:8]}…`")

    # Schema filter
    st.subheader("Filter by schema")
    schemas = ["All schemas", "public", "sales", "hr", "finance"]
    selected = st.radio("Schema", schemas, index=0, label_visibility="collapsed")
    st.session_state.schema_filter = None if selected == "All schemas" else selected

    st.divider()

    # Search box
    search_term = st.text_input(
        "🔍 Search columns",
        placeholder="e.g. revenue, customer_id…",
        key="column_search",
    )

    if search_term and len(search_term) >= 2:
        try:
            resp = requests.get(
                f"{API_BASE}/schema/search",
                params={"q": search_term, "limit": 10},
                timeout=5,
            )
            if resp.ok:
                results = resp.json()
                st.caption(f"{len(results)} columns found")
                for r in results:
                    with st.expander(f"{r['table']}.{r['column']}"):
                        st.code(r.get("data_type", ""), language=None)
                        st.caption(r.get("description", "No description"))
                        if r.get("pii"):
                            st.error("🔴 PII column")
            else:
                st.caption("Search unavailable")
        except Exception:
            st.caption("Search unavailable")

    st.divider()

    # Tables list with column detail on expand
    st.subheader("Available tables")

    tables = _fetch_tables()
    st.session_state.tables_cache = tables

    if not tables:
        st.info("No tables found or backend starting up…")
    else:
        st.caption(f"{len(tables)} tables in dictionary")

        for t in tables:
            schema = t.get("schema_name", "public")
            table  = t.get("table_name", "")
            label  = f"**{schema}.{table}**"

            with st.expander(label):
                # Description
                desc = t.get("description", "")
                if desc:
                    st.caption(desc)

                # Fetch column detail
                with st.spinner("Loading columns…"):
                    detail = _fetch_columns(schema, table)

                if not detail or not isinstance(detail, dict):
                    st.warning("Could not load column details")
                    continue

                columns = detail.get("columns") or []
                joins   = detail.get("joins") or []

                # Column stats summary
                pk_count  = sum(1 for c in columns if c.get("is_pk"))
                fk_count  = sum(1 for c in columns if c.get("is_fk"))
                pii_count = sum(1 for c in columns if c.get("pii"))

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Columns", len(columns))
                m2.metric("PKs",     pk_count)
                m3.metric("FKs",     fk_count)
                m4.metric("PII",     pii_count)

                st.divider()

                # Columns tab + Joins tab
                tab_cols, tab_joins = st.tabs(["Columns", "Joins"])

                with tab_cols:
                    for col in columns:
                        _render_column_detail(col)
                        st.divider()

                with tab_joins:
                    _render_joins(joins)

                # Quick action — prefill chat
                if st.button(
                    f"Ask about {table}",
                    key=f"ask_{schema}_{table}",
                    use_container_width=True,
                ):
                    st.session_state.prefill = (
                        f"What columns are in the {schema}.{table} table "
                        f"and how does it join to related tables?"
                    )
                    st.rerun()

    st.divider()
    if st.button("🔄 New conversation", use_container_width=True):
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

# Handle prefill from sidebar "Ask about table" button
#prefill_value = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""

# Handle prefill from sidebar "Ask about table" button
if "prefill" in st.session_state:
    prefill_value = st.session_state.pop("prefill")
    st.session_state.messages.append({"role": "user", "content": prefill_value})
    st.rerun()

if prompt := st.chat_input("e.g. 'Show me top 10 customers by revenue in Q1 2024'"):
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