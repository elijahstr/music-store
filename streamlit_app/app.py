"""
Music Store Chat UI - Streamlit Frontend

A simple chat interface for the LangGraph-powered music store assistant.
"""

import streamlit as st
import streamlit.components.v1 as components
from langgraph_sdk import get_sync_client

# Configuration
LANGGRAPH_URL = "http://localhost:8123"
ASSISTANT_ID = "music_store"

# Available users for demo (all passwords are "demo123")
DEMO_USERS = {
    "julia": {"name": "Julia Schottenstein", "role": "employee", "password": "demo123"},
    "jake": {"name": "Jake Broekhuizen", "role": "customer", "password": "demo123"},
    "neil": {"name": "Neil Dahlke", "role": "customer", "password": "demo123"},
}

st.set_page_config(
    page_title="The Music Company Of San Francisco",
    page_icon="🎵",
    layout="centered",
)

# Custom CSS to match LangChain brand colors
st.markdown("""
<style>
    /* LangChain brand colors */
    :root {
        --lc-primary: #2F6868;
        --lc-primary-light: #84C4C0;
        --lc-primary-dark: #1C3C3C;
        --lc-bg: #ffffff;
        --lc-bg-secondary: #f4f6f6;
    }

    /* Force light mode backgrounds */
    .stApp {
        background-color: #ffffff !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
    }

    [data-testid="stHeader"] {
        background-color: #2F6868 !important;
    }

    /* Main content area */
    .main .block-container {
        background-color: #ffffff !important;
    }

    /* Top accent bar */
    .top-accent-bar {
        background: linear-gradient(90deg, #1C3C3C 0%, #2F6868 50%, #84C4C0 100%);
        height: 6px;
        width: 100%;
        margin-bottom: 1rem;
        border-radius: 3px;
    }

    /* Main title */
    h1 {
        color: #1C3C3C !important;
    }

    h2, h3 {
        color: #2F6868 !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #2F6868 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        transition: background-color 0.2s ease;
    }

    .stButton > button:hover {
        background-color: #1C3C3C !important;
        color: white !important;
    }

    /* Form submit button */
    .stFormSubmitButton > button {
        background-color: #2F6868 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
    }

    .stFormSubmitButton > button:hover {
        background-color: #1C3C3C !important;
    }

    /* Input fields - clean white with subtle border */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #1C3C3C !important;
        border: 1px solid #84C4C0 !important;
        border-radius: 6px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #2F6868 !important;
        box-shadow: 0 0 0 2px rgba(47, 104, 104, 0.3) !important;
        outline: none !important;
    }

    /* Override any red/default focus colors */
    .stTextInput > div > div {
        border-color: #84C4C0 !important;
    }

    .stTextInput > div > div:focus-within {
        border-color: #2F6868 !important;
        box-shadow: 0 0 0 2px rgba(47, 104, 104, 0.3) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #84C4C0 !important;
    }

    /* Labels */
    .stTextInput > label {
        color: #1C3C3C !important;
    }

    /* Override all focus states to use teal */
    *:focus {
        outline-color: #2F6868 !important;
    }

    input:focus, textarea:focus {
        border-color: #2F6868 !important;
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(47, 104, 104, 0.3) !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f4f6f6 !important;
    }

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #1C3C3C !important;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 8px;
        background-color: #f4f6f6 !important;
        border: 1px solid #84C4C0 !important;
        padding: 1rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* User messages - slightly different shade */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #e8f0f0 !important;
    }

    /* Status indicator */
    [data-testid="stStatus"] {
        border-color: #84C4C0 !important;
        background-color: #ffffff !important;
    }

    /* Links */
    a {
        color: #2F6868 !important;
    }

    a:hover {
        color: #1C3C3C !important;
    }

    /* Divider */
    hr {
        border-color: #84C4C0 !important;
    }

    /* Info boxes */
    .stAlert {
        border-left-color: #2F6868 !important;
        background-color: #f4f6f6 !important;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        border: 2px solid #2F6868 !important;
        border-radius: 8px !important;
        background-color: #ffffff !important;
        box-shadow: 0 2px 4px rgba(47, 104, 104, 0.1) !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #1C3C3C !important;
        box-shadow: 0 2px 8px rgba(47, 104, 104, 0.2) !important;
    }

    /* Chat input textarea */
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInputTextArea"],
    .stChatInput textarea {
        background-color: #ffffff !important;
        color: #1C3C3C !important;
        border: none !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #84C4C0 !important;
    }

    /* Chat input container */
    .stChatInputContainer,
    [data-testid="stChatInputContainer"] {
        background-color: #ffffff !important;
    }

    /* Bottom chat input area */
    [data-testid="stBottom"] {
        background-color: #f4f6f6 !important;
        border-top: 1px solid #84C4C0 !important;
        padding-top: 1rem !important;
    }

    [data-testid="stBottomBlockContainer"] {
        background-color: #f4f6f6 !important;
    }

    /* Role badges - custom styling */
    .role-badge-employee {
        background-color: #2F6868;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85em;
    }

    .role-badge-customer {
        background-color: #84C4C0;
        color: #1C3C3C;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85em;
    }

    /* Caption text */
    .stCaption, small, [data-testid="stCaptionContainer"] {
        color: #555555 !important;
    }

    /* All paragraph and text elements */
    p, span, div {
        color: #1C3C3C;
    }

    /* Strong/bold text */
    strong {
        color: #1C3C3C !important;
    }

    /* Code elements */
    code {
        color: #2F6868 !important;
        background-color: #e8f0f0 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }

    /* Form container */
    [data-testid="stForm"] {
        background-color: #f4f6f6 !important;
        padding: 1.5rem !important;
        border-radius: 8px !important;
        border: 1px solid #84C4C0 !important;
    }

    /* Markdown text blocks */
    [data-testid="stMarkdownContainer"] p {
        color: #1C3C3C !important;
    }

    /* Ensure main content text is visible */
    .main [data-testid="stVerticalBlock"] p,
    .main [data-testid="stVerticalBlock"] span {
        color: #1C3C3C !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.messages = []
    st.session_state.thread_id = None

# Always ensure pending_interrupt exists (for existing sessions after code update)
if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None


def authenticate(username: str, password: str) -> bool:
    """Validate username and password."""
    username = username.lower().strip()
    if username in DEMO_USERS:
        return DEMO_USERS[username]["password"] == password
    return False


def logout():
    """Clear session and log out user."""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.messages = []
    st.session_state.thread_id = None
    st.session_state.pending_interrupt = None


def login_page():
    """Render the login page."""
    # Top accent bar
    st.markdown('<div class="top-accent-bar"></div>', unsafe_allow_html=True)

    st.title("🎵 The Music Company Of San Francisco")
    st.subheader("Please log in to continue")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submit = st.form_submit_button("Log In", use_container_width=True)

        if submit:
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.current_user = username.lower().strip()
                st.session_state.messages = []
                st.session_state.thread_id = None
                st.rerun()
            else:
                st.error("Invalid username or password")

    st.divider()
    st.caption("Demo accounts:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**jake**")
        st.caption("Customer")
    with col2:
        st.markdown("**neil**")
        st.caption("Customer")
    with col3:
        st.markdown("**julia**")
        st.caption("Employee")
    st.caption("Password for all: `demo123`")


def get_client():
    """Create a LangGraph client with auth headers."""
    return get_sync_client(
        url=LANGGRAPH_URL,
        headers={"Authorization": f"Bearer {st.session_state.current_user}"},
    )


def stream_response_with_status(user_message: str, status_container, is_resume: bool = False, resume_value: dict = None):
    """Stream response from LangGraph backend with live status updates.

    Args:
        user_message: The user's message (ignored if is_resume=True)
        status_container: Streamlit status container for updates
        is_resume: If True, resume from an interrupt instead of sending new message
        resume_value: The value to send when resuming (e.g., {"confirmed": True})

    Returns:
        Tuple of (final_response, interrupt_data) where interrupt_data is None if no interrupt
    """
    client = get_client()

    # Create a thread if we don't have one
    if st.session_state.thread_id is None:
        thread = client.threads.create()
        st.session_state.thread_id = thread["thread_id"]

    final_response = ""
    interrupt_data = None

    # Either resume or start new run
    if is_resume and resume_value is not None:
        stream = client.runs.stream(
            thread_id=st.session_state.thread_id,
            assistant_id=ASSISTANT_ID,
            input=None,
            command={"resume": resume_value},
            stream_mode=["values", "updates"],
        )
    else:
        stream = client.runs.stream(
            thread_id=st.session_state.thread_id,
            assistant_id=ASSISTANT_ID,
            input={"messages": [{"role": "user", "content": user_message}]},
            stream_mode=["values", "updates"],
        )

    for chunk in stream:
        # Show which node is running
        if chunk.event == "updates":
            if isinstance(chunk.data, dict):
                # Check for interrupt in updates
                if "__interrupt__" in chunk.data:
                    interrupt_info = chunk.data["__interrupt__"]
                    if interrupt_info and len(interrupt_info) > 0:
                        # Extract the interrupt value
                        interrupt_obj = interrupt_info[0]
                        if hasattr(interrupt_obj, "value"):
                            interrupt_data = interrupt_obj.value
                        elif isinstance(interrupt_obj, dict):
                            interrupt_data = interrupt_obj.get("value", interrupt_obj)
                        else:
                            interrupt_data = interrupt_obj
                else:
                    for node_name in chunk.data.keys():
                        if node_name != "__metadata__":
                            status_container.update(label=f"Running: {node_name}...", state="running")

        # Extract response from values
        if chunk.event == "values":
            data = chunk.data
            if isinstance(data, dict):
                messages = data.get("messages", [])
            else:
                messages = getattr(data, "messages", [])

            if messages:
                last_msg = messages[-1]

                # Handle both dict and object forms
                if isinstance(last_msg, dict):
                    content = last_msg.get("content", "")
                    msg_type = last_msg.get("type", "")
                elif hasattr(last_msg, "content"):
                    content = last_msg.content
                    msg_type = getattr(last_msg, "type", "")
                else:
                    content = str(last_msg)
                    msg_type = "unknown"

                # Accept AI messages
                if msg_type == "ai" and content:
                    final_response = content

    return final_response, interrupt_data


def chat_page():
    """Render the main chat page."""
    user_info = DEMO_USERS[st.session_state.current_user]

    # Top accent bar
    st.markdown('<div class="top-accent-bar"></div>', unsafe_allow_html=True)

    # Auto-focus chat input on page load
    components.html("""
    <script>
        // Focus on chat input in parent Streamlit frame
        const focusChatInput = () => {
            const chatInput = window.parent.document.querySelector('[data-testid="stChatInput"] textarea');
            if (chatInput) {
                chatInput.focus();
            }
        };
        // Try multiple times to account for Streamlit's async rendering
        focusChatInput();
        setTimeout(focusChatInput, 100);
        setTimeout(focusChatInput, 300);
        setTimeout(focusChatInput, 500);
    </script>
    """, height=0)

    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎵 The Music Company Of San Francisco")
    with col2:
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

    # User info bar with custom badge
    role_class = "role-badge-employee" if user_info["role"] == "employee" else "role-badge-customer"
    st.markdown(
        f"Logged in as **{user_info['name']}** &nbsp; "
        f"<span class='{role_class}'>{user_info['role'].title()}</span>",
        unsafe_allow_html=True
    )

    if user_info["role"] == "employee":
        st.caption("As an employee, you can help customers with their orders and queries.")
    else:
        st.caption("As a customer, you can check your orders, get recommendations, and more.")

    st.divider()

    # Sidebar for chat controls
    with st.sidebar:
        st.header("Chat Options")
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = None
            st.rerun()

        st.divider()
        st.caption(f"Connected to: {LANGGRAPH_URL}")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle pending interrupt (confirmation dialog)
    if st.session_state.pending_interrupt:
        interrupt = st.session_state.pending_interrupt
        msg = interrupt.get("message", "Please confirm this action.")
        interrupt_type = interrupt.get("type", "confirmation")

        # Determine the right response key based on interrupt type
        # Employee tools use "approved", customer tools use "confirmed"
        is_manager_approval = interrupt_type == "manager_approval"
        confirm_key = "approved" if is_manager_approval else "confirmed"

        # Add anchor and auto-scroll to confirmation dialog
        st.markdown('<div id="interrupt-dialog"></div>', unsafe_allow_html=True)
        components.html("""
        <script>
            // Scroll to the interrupt dialog
            const scrollToDialog = () => {
                const dialog = window.parent.document.getElementById('interrupt-dialog');
                if (dialog) {
                    dialog.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            };
            setTimeout(scrollToDialog, 100);
            setTimeout(scrollToDialog, 300);
        </script>
        """, height=0)

        with st.chat_message("assistant"):
            title = "Manager Approval Required" if is_manager_approval else "Confirmation Required"
            st.warning(f"**{title}**\n\n{msg}")

            col1, col2 = st.columns(2)
            with col1:
                btn_label = "✓ Approve" if is_manager_approval else "✓ Confirm"
                if st.button(btn_label, use_container_width=True, type="primary"):
                    st.session_state.pending_interrupt = None
                    with st.status("Processing...", expanded=True) as status:
                        response, new_interrupt = stream_response_with_status(
                            "", status, is_resume=True, resume_value={confirm_key: True}
                        )
                        status.update(label="Complete!", state="complete", expanded=False)

                    if new_interrupt:
                        st.session_state.pending_interrupt = new_interrupt
                    elif response:
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()

            with col2:
                btn_label = "✗ Deny" if is_manager_approval else "✗ Cancel"
                if st.button(btn_label, use_container_width=True):
                    # Store interrupt info for denial message before clearing
                    denied_action = interrupt.get("action", "action")
                    st.session_state.pending_interrupt = None
                    with st.status("Cancelling...", expanded=True) as status:
                        response, new_interrupt = stream_response_with_status(
                            "", status, is_resume=True, resume_value={confirm_key: False}
                        )
                        status.update(label="Cancelled", state="complete", expanded=False)

                    # Use backend response if available, otherwise show denial acknowledgement
                    if response:
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        denial_msg = "Request denied." if is_manager_approval else "Action cancelled."
                        st.session_state.messages.append({"role": "assistant", "content": denial_msg})
                    st.rerun()

        # Don't show chat input while interrupt is pending
        return

    # Chat input
    if prompt := st.chat_input("Ask about music, orders, or recommendations..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response
        with st.chat_message("assistant"):
            try:
                with st.status("Processing...", expanded=True) as status:
                    response, interrupt_data = stream_response_with_status(prompt, status)
                    status.update(label="Complete!", state="complete", expanded=False)

                if interrupt_data:
                    # Store interrupt and show confirmation UI
                    st.session_state.pending_interrupt = interrupt_data
                    st.rerun()
                elif response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.warning("No response received from the assistant.")

            except Exception as e:
                error_msg = f"Error connecting to backend: {str(e)}"
                st.error(error_msg)
                st.caption("Make sure the LangGraph backend is running on port 8123")
                import traceback
                st.code(traceback.format_exc())


# Main routing
if st.session_state.authenticated:
    chat_page()
else:
    login_page()
