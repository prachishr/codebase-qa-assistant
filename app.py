import os
import shutil
import stat
import json

import streamlit as st
from dotenv import load_dotenv
from git import Repo
from supabase import create_client

from database import (
    initialize_database,
    create_conversation,
    update_conversation,
    save_message,
    get_conversations,
    get_messages,
    delete_conversation
)
# Configuration

load_dotenv(override=True)

REPO_PATH = "repo"
FAISS_PATH = "faiss_index"
REPO_STATE_FILE = "repo_state.json"


# Page Configuration
st.set_page_config(
    page_title="Codebase QA Assistant",
    page_icon="app_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Custom Styling

st.markdown(
    """
    <style>

    .stApp {
        background: #0b0f19;
    }

    .main {
        background: #0b0f19;
    }

    /* Make the sticky top header opaque so scrolled content is
    hidden behind it instead of bleeding through half-visible. */
    header[data-testid="stHeader"] {
        background: #0b0f19;
    }

    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 7rem;
        max-width: 1450px;
    }

    .main-title {
        font-size: 2.25rem;
        font-weight: 750;
        letter-spacing: -1.1px;
        margin: 0 0 0.3rem 0;
        color: #f4f6fb;
        text-align: left;
    }

    .subtitle {
        color: #9299aa;
        font-size: 1.05rem;
        line-height: 1.6;
        margin: 0 0 1.5rem 0;
    }

    /* =====================================================
       SIDEBAR
       ===================================================== */

    section[data-testid="stSidebar"] {
        background: #111522;
        border-right: 1px solid #252b3b;
    }

    section[data-testid="stSidebar"] > div {
        background: #111522;
    }


    .sidebar-brand {
        padding: 13px 14px;
        margin: 2px 0 18px 0;
        border-radius: 11px;
        background: linear-gradient(135deg, #191d31, #151927);
        border: 1px solid #3b4161;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
    }

    .sidebar-brand-title {
        color: #f4f6fb;
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: -0.2px;
        line-height: 1.25;
    }

    .sidebar-brand-accent {
        width: 34px;
        height: 3px;
        margin-top: 7px;
        border-radius: 99px;
        background: #7c5cff;
    }

    .sidebar-heading {
        font-size: 0.78rem;
        font-weight: 700;
        color: #8f96a8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 18px;
        margin-bottom: 10px;
    }

    .stButton > button {
        border-radius: 9px;
        border: 1px solid #30384d;
        background: #171c2a;
        color: #e8ebf2;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        border-color: #7c5cff;
        color: #ffffff;
        background: #1c2233;
    }

    /* =====================================================
       NEW ANALYSIS HOME
       ===================================================== */

    .welcome-wrap {
        max-width: 760px;
        margin: 2.4rem auto 1.7rem auto;
        text-align: center;
    }

    .welcome-icon {
        width: 58px;
        height: 58px;
        margin: 0 auto 1rem auto;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #171c2a;
        border: 1px solid #30384d;
        color: #9b8cff;
        font-size: 1.8rem;
    }

    .welcome-title {
        font-size: 2.25rem;
        font-weight: 750;
        color: #f4f6fb;
        margin-bottom: 0.6rem;
    }

    .welcome-subtitle {
        color: #8f98ab;
        font-size: 0.98rem;
        line-height: 1.6;
        max-width: 650px;
        margin: 0 auto;
    }

    .url-label {
        width: 100%;
        margin: 0 0 0.5rem 0;
        color: #cdd3df;
        font-weight: 600;
        font-size: 0.9rem;
        text-align: left;
    }

    .url-hint {
        max-width: 760px;
        margin: 0.65rem auto 0 auto;
        text-align: center;
        color: #697287;
        font-size: 0.78rem;
    }

    .analysis-progress-card {
        padding: 18px 20px;
        border-radius: 14px;
        border: 1px solid #2b3448;
        background: #121824;
        margin: 1.5rem 0 1rem 0;
    }

    .analysis-progress-title {
        color: #f0f2f7;
        font-size: 1.15rem;
        font-weight: 700;
    }

    .analysis-progress-subtitle {
        color: #7f889b;
        font-size: 0.86rem;
        margin-top: 0.3rem;
    }

    /* =====================================================
       REPOSITORY DASHBOARD
       ===================================================== */

    .repo-identity-card {
        padding: 18px 20px;
        border-radius: 14px;
        border: 1px solid #2b3448;
        background: linear-gradient(135deg, #121b2b, #101622);
        margin: 1rem 0 1.1rem 0;
    }

    .repo-identity-status {
        color: #f1f4fa;
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .repo-identity-name {
        color: #9da6b8;
        font-size: 0.94rem;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #17213a, #111827);
        border: 1px solid #34415f;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
    }

    [data-testid="stMetricLabel"] {
        color: #aeb8cc;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: #f4f7ff;
        font-weight: 700;
    }

    .section-divider {
        height: 1px;
        background: #252b3b;
        margin: 1.4rem 0;
    }

    .empty-chat {
        padding: 2.2rem 1rem 1.5rem 1rem;
        text-align: center;
    }

    .empty-chat-title {
        color: #e9edf5;
        font-size: 1.25rem;
        font-weight: 650;
        margin-bottom: 0.4rem;
    }

    .empty-chat-subtitle {
        color: #7f889b;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    [data-testid="stChatMessage"] {
        background: transparent;
    }

    [data-testid="stChatMessageContent"] {
        color: #e8ebf2;
    }

    /* =====================================================
       RIGHT PANEL
       ===================================================== */

    .analysis-heading {
        font-size: 1.08rem;
        font-weight: 750;
        color: #f0f2f7;
        margin: 0 0 0.8rem 0;
        padding: 0;
    }

    .info-heading {
        font-size: 1.08rem;
        font-weight: 750;
        color: #f0f2f7;
        margin-top: 1.25rem;
        margin-bottom: 0.9rem;
    }

    [data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }

    /* =====================================================
       CHAT INPUT
       ===================================================== */

    [data-testid="stChatInput"] {
        border: 1px solid #30384d;
        background: #151a28;
        border-radius: 12px;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #7c5cff;
        box-shadow: 0 0 0 1px #7c5cff;
    }

    /* =====================================================
       RESPONSIVE
       ===================================================== */

    @media (max-width: 900px) {

        .welcome-wrap {
            margin-top: 3rem;
        }

        .welcome-title {
            font-size: 1.8rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)

# Supabase Authentication

def get_supabase_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    # Streamlit Cloud fallback.
    if not supabase_url or not supabase_key:
        try:
            supabase_url = st.secrets["SUPABASE_URL"]
            supabase_key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass

    if not supabase_url or not supabase_key:
        st.error(
            "Supabase configuration is missing. "
            "Add SUPABASE_URL and SUPABASE_KEY to your .env file "
            "or Streamlit secrets."
        )
        st.stop()

    return create_client(supabase_url, supabase_key)


supabase = get_supabase_client()


def show_auth_screen():
    st.markdown("""
    <style>
    .auth-bg {
        position: fixed; inset: 0; pointer-events: none; z-index: 0;
        background: radial-gradient(ellipse at 50% 30%, rgba(124,92,255,0.10), transparent 55%);
    }
    .auth-hero { text-align: center; margin: 3rem auto 2rem auto; }
    .auth-hero-icon {
        width: 52px; height: 52px; margin: 0 auto 1rem auto;
        border-radius: 14px; display: flex; align-items: center;
        justify-content: center; background: #171c2a;
        border: 1px solid #30384d; color: #9b8cff; font-size: 1.5rem;
    }
    .auth-hero-title {
        font-size: 1.9rem; font-weight: 750; letter-spacing: -0.8px;
        color: #f4f6fb; margin: 0 0 0.5rem 0;
    }
    .auth-hero-sub { color: #8f98ab; font-size: 0.92rem; line-height: 1.55; }

    div[data-testid="stColumn"]:has(div.stTabs) {
        background: #111522; border: 1px solid #252b3b;
        border-radius: 16px; padding: 2rem 2rem 1.5rem 2rem;
        box-shadow: 0 20px 50px -20px rgba(0,0,0,0.6);
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stTabs [data-baseweb="tab-list"] {
        gap: 8px; justify-content: center;
        border-bottom: 1px solid #252b3b; margin-bottom: 1.2rem;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stTabs [data-baseweb="tab"] {
        background: transparent; color: #8f96a8; font-weight: 600;
        font-size: 0.88rem; padding: 8px 16px;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stTabs [aria-selected="true"] {
        color: #fff !important; background: rgba(124,92,255,0.08) !important;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stTabs [data-baseweb="tab-highlight"] {
        background-color: #7c5cff !important; height: 2px !important;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stTextInput input {
        background: #0d1220 !important; border: 1px solid #2b3448 !important;
        border-radius: 9px !important; color: #e8ebf2 !important;
        padding: 11px 13px !important;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stTextInput input:focus {
        border-color: #7c5cff !important;
        box-shadow: 0 0 0 3px rgba(124,92,255,0.12) !important;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stButton > button {
        width: 100%; background: #7c5cff; color: #fff;
        border: 1px solid #7c5cff; border-radius: 9px;
        padding: 10px 16px; font-weight: 600; font-size: 0.9rem;
        transition: all 0.15s ease;
    }
    div[data-testid="stColumn"]:has(div.stTabs) .stButton > button:hover {
        background: #8d70ff; border-color: #8d70ff;
        transform: translateY(-1px);
        box-shadow: 0 8px 20px -8px rgba(124,92,255,0.5); color: #fff;
    }
    </style>
    <div class="auth-bg"></div>
    <div class="auth-hero">
        <div class="auth-hero-icon">⌘</div>
        <div class="auth-hero-title">Codebase QA Assistant</div>
        <div class="auth-hero-sub">
            Sign in to analyze repositories and keep your
            conversation history private to your account.
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, auth_col, _ = st.columns([1, 1.3, 1])


    with auth_col:
        login_tab, signup_tab = st.tabs(["🔐 Login", "✨ Sign Up"])

        with login_tab:
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            if st.button(
                "Login",
                use_container_width=True,
                key="login_button"
            ):
                if not login_email.strip() or not login_password:
                    st.error("Please enter your email and password.")
                else:
                    try:
                        response = supabase.auth.sign_in_with_password(
                            {
                                "email": login_email.strip(),
                                "password": login_password
                            }
                        )

                        if response.user is None:
                            st.error(
                                "Login failed. Please check your credentials."
                            )
                        else:
                            st.session_state.user_id = str(response.user.id)
                            st.session_state.user_email = (
                                response.user.email or login_email.strip()
                            )
                            st.session_state.authenticated = True
                            st.rerun()

                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")

        with signup_tab:
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input(
                "Password",
                type="password",
                key="signup_password"
            )
            signup_confirm = st.text_input(
                "Confirm Password",
                type="password",
                key="signup_confirm"
            )

            if st.button(
                "Create Account",
                use_container_width=True,
                key="signup_button"
            ):
                if not signup_email.strip() or not signup_password:
                    st.error("Please enter your email and password.")
                elif len(signup_password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif signup_password != signup_confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        response = supabase.auth.sign_up(
                            {
                                "email": signup_email.strip(),
                                "password": signup_password
                            }
                        )

                        if (
                            response.user is not None
                            and response.session is not None
                        ):
                            st.session_state.user_id = str(response.user.id)
                            st.session_state.user_email = (
                                response.user.email or signup_email.strip()
                            )
                            st.session_state.authenticated = True
                            st.rerun()
                        else:
                            st.success(
                                "Account created. Please check your email "
                                "to verify your account, then log in."
                            )

                    except Exception as e:
                        st.error(f"Sign up failed: {str(e)}")


# Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = ""


# Require authentication before accessing the application.
if not st.session_state.authenticated or not st.session_state.user_id:
    show_auth_screen()
    st.stop()


# Database Initialization
try:
    initialize_database()
except Exception as e:
    st.error(f"Database initialization failed: {e}")
    st.stop()


# Session State
if "repo_ready" not in st.session_state:
    st.session_state.repo_ready = False

if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "conversation_title" not in st.session_state:
    st.session_state.conversation_title = "New Conversation"

if "analyzing" not in st.session_state:
    st.session_state.analyzing = False

if "restore_repository" not in st.session_state:
    st.session_state.restore_repository = False


# Repository Helpers

def remove_readonly(func, path, exc_info):

    try:

        os.chmod(
            path,
            stat.S_IWRITE
        )

        func(path)

    except Exception:

        pass


def remove_repository():

    if os.path.exists(REPO_PATH):

        shutil.rmtree(
            REPO_PATH,
            onerror=remove_readonly
        )


def remove_faiss():

    if os.path.exists(FAISS_PATH):

        shutil.rmtree(
            FAISS_PATH,
            ignore_errors=True
        )


def save_repo_state(repo_url):

    with open(
        REPO_STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "repository_url": repo_url
            },
            f
        )


def get_saved_repo_url():

    if not os.path.exists(
        REPO_STATE_FILE
    ):

        return ""

    try:

        with open(
            REPO_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return data.get(
            "repository_url",
            ""
        )

    except Exception:

        return ""


def repository_already_loaded(repo_url):

    saved_url = get_saved_repo_url()

    return (
        saved_url.strip().lower()
        == repo_url.strip().lower()
        and os.path.exists(REPO_PATH)
        and os.path.exists(FAISS_PATH)
    )


def get_repository_name(repo_url):

    url = repo_url.rstrip("/")

    name = url.split("/")[-1]

    if name.endswith(".git"):

        name = name[:-4]

    return name


def detect_tech_stack(repo_path):

    """
    Detect a practical, user-facing tech stack from repository
    files and common dependency/configuration files.

    This is intentionally lightweight so it does not add another
    expensive analysis step during repository ingestion.
    """

    stack = []
    extensions = set()
    file_names = set()
    dependency_text = ""

    try:

        for root, dirs, files in os.walk(repo_path):

            dirs[:] = [
                d for d in dirs
                if d not in {
                    ".git",
                    ".venv",
                    "venv",
                    "node_modules",
                    "__pycache__",
                    "dist",
                    "build"
                }
            ]

            for file in files:

                file_names.add(file.lower())

                extension = os.path.splitext(file)[1].lower()

                if extension:
                    extensions.add(extension)

                # Read common dependency/config files only.
                if file.lower() in {
                    "requirements.txt",
                    "pyproject.toml",
                    "package.json",
                    "package-lock.json",
                    "poetry.lock",
                    "pipfile",
                    "dockerfile"
                }:

                    try:

                        with open(
                            os.path.join(root, file),
                            "r",
                            encoding="utf-8",
                            errors="ignore"
                        ) as f:

                            dependency_text += (
                                f.read().lower()
                                + "\n"
                            )

                    except Exception:
                        pass

    except Exception:

        return ["Repository files"]

    # Languages

    if ".py" in extensions:
        stack.append("Python")

    if ".js" in extensions or ".jsx" in extensions:
        stack.append("JavaScript")

    if ".ts" in extensions or ".tsx" in extensions:
        stack.append("TypeScript")

    if ".java" in extensions:
        stack.append("Java")

    if ".cpp" in extensions or ".cc" in extensions or ".cxx" in extensions:
        stack.append("C++")

    if ".cs" in extensions:
        stack.append("C#")

    if ".go" in extensions:
        stack.append("Go")

    if ".php" in extensions:
        stack.append("PHP")

    if ".rb" in extensions:
        stack.append("Ruby")

    # Frameworks / Tools

    if (
        "streamlit" in dependency_text
        or "streamlit" in file_names
    ):
        stack.append("Streamlit")

    if "fastapi" in dependency_text:
        stack.append("FastAPI")

    if "flask" in dependency_text:
        stack.append("Flask")

    if "django" in dependency_text:
        stack.append("Django")

    if (
        "react" in dependency_text
        or "react-dom" in dependency_text
    ):
        stack.append("React")

    if "next" in dependency_text:
        stack.append("Next.js")

    if "node" in dependency_text or "package.json" in file_names:
        stack.append("Node.js")

    if "langchain" in dependency_text:
        stack.append("LangChain")

    if "tensorflow" in dependency_text:
        stack.append("TensorFlow")

    if "torch" in dependency_text or "pytorch" in dependency_text:
        stack.append("PyTorch")

    if "scikit-learn" in dependency_text or "sklearn" in dependency_text:
        stack.append("scikit-learn")

    if "pandas" in dependency_text:
        stack.append("Pandas")

    if "numpy" in dependency_text:
        stack.append("NumPy")

    if "dockerfile" in file_names or "docker-compose.yml" in file_names:
        stack.append("Docker")

    if ".ipynb" in extensions:
        stack.append("Jupyter")

    if not stack:
        stack.append("Repository files")

    # Keep the sidebar compact.
    return list(dict.fromkeys(stack))[:8]


# Lazy Imports
def get_repository_functions():

    from ingestion import load_repository
    from chunking import create_chunks
    from vector_store import create_vector_store

    return (
        load_repository,
        create_chunks,
        create_vector_store
    )


def get_rag_function():

    from RAG import generate_answer

    return generate_answer


# Repository Preparation

def prepare_repository(repo_url, status_container):

    repo_url = repo_url.strip()

    # Reuse existing repository

    if repository_already_loaded(
        repo_url
    ):

        st.session_state.repo_ready = True
        st.session_state.repo_url = repo_url

        return

    (
        load_repository,
        create_chunks,
        create_vector_store
    ) = get_repository_functions()

    # Remove old repository

    status_container.write(
        "🧹 Preparing workspace..."
    )

    remove_repository()

    remove_faiss()

    # --------------------------------------------------------
    # Clone repository
    # --------------------------------------------------------

    status_container.write(
        "📥 Cloning GitHub repository..."
    )

    Repo.clone_from(
        repo_url,
        REPO_PATH,
        depth=1
    )

    # Extract
    status_container.write(
        "📄 Extracting repository files..."
    )

    documents = load_repository(
        REPO_PATH
    )

    status_container.write(
        f"📄 Found {len(documents)} repository documents."
    )
    # Chunk

    status_container.write(
        "🌳 Creating AST-aware and documentation chunks..."
    )

    chunks = create_chunks(
        documents
    )

    status_container.write(
        f"🌳 Created {len(chunks)} chunks."
    )

    # Embeddings + FAISS

    status_container.write(
        "🧠 Generating embeddings and building FAISS..."
    )

    create_vector_store()

    status_container.write(
        "🔎 FAISS vector database created."
    )

    # Save state

    save_repo_state(
        repo_url
    )

    st.session_state.repo_ready = True
    st.session_state.repo_url = repo_url

# Conversation Helpers

def generate_chat_title(question):

    title = question.strip().replace(
        "\n",
        " "
    )

    if len(title) > 42:

        title = (
            title[:42].rstrip()
            + "..."
        )

    return title


def load_previous_chat(conversation_id):

    conversations = get_conversations(st.session_state.user_id)

    selected = None

    for conversation in conversations:

        if conversation[0] == conversation_id:

            selected = conversation

            break

    if selected is None:

        return

    conversation_id = selected[0]

    title = selected[1]

    repository_url = selected[2] or ""

    messages = get_messages(
        st.session_state.user_id,
        conversation_id
    )

    st.session_state.conversation_id = (
        conversation_id
    )

    st.session_state.conversation_title = (
        title or "Conversation"
    )

    st.session_state.repo_url = (
        repository_url
    )

    st.session_state.messages = (
        messages
    )

    if repository_url:

        if repository_already_loaded(
            repository_url
        ):

            st.session_state.repo_ready = True

        else:

            st.session_state.repo_ready = False

            st.session_state.restore_repository = True

    else:

        st.session_state.repo_ready = False


def display_sources(sources):

    if not sources:

        return

    with st.expander(
        "📚 Sources"
    ):

        displayed_sources = set()

        for source in sources:

            if isinstance(
                source,
                dict
            ):

                file_name = source.get(
                    "file",
                    "Unknown"
                )

                path = source.get(
                    "path",
                    ""
                )

            else:

                file_name = source.metadata.get(
                    "file",
                    "Unknown"
                )

                path = source.metadata.get(
                    "path",
                    ""
                )

            source_key = (
                file_name,
                path
            )

            if source_key in displayed_sources:

                continue

            displayed_sources.add(
                source_key
            )

            st.markdown(
                f"""
                <div class="source-box">
                📄 <strong>{file_name}</strong><br>
                <small>{path}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

# LEFT SIDEBAR

with st.sidebar:
    # Application name

    st.markdown(
        '''
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Codebase QA Assistant</div>
            <div class="sidebar-brand-accent"></div>
        </div>
        ''',
        unsafe_allow_html=True
    )

    # Account
    st.markdown(
        '<div class="sidebar-heading">👤 Account</div>',
        unsafe_allow_html=True
    )

    st.caption(st.session_state.user_email)

    if st.button(
        "Logout",
        use_container_width=True,
        key="logout_button"
    ):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

        for key in [
            "authenticated",
            "user_id",
            "user_email",
            "repo_ready",
            "repo_url",
            "messages",
            "conversation_id",
            "conversation_title",
            "analyzing",
            "restore_repository",
            "pending_analysis_url",
            "repo_stats"
        ]:
            st.session_state.pop(key, None)

        st.rerun()

    st.divider()

    # New Chat

    if st.button(
        "➕  New Chat",
        use_container_width=True
    ):

        # Clear current conversation
        st.session_state.messages = []

        st.session_state.conversation_id = None

        st.session_state.conversation_title = (
            "New Conversation"
        )

        # Clear current repository
        st.session_state.repo_ready = False
        st.session_state.repo_url = ""

        # Remove restore flag if present
        st.session_state.restore_repository = False

        st.rerun()

    st.divider()
    # Current Repository

    st.markdown(
        '<div class="sidebar-heading">📦 Current Repository</div>',
        unsafe_allow_html=True
    )

    if st.session_state.repo_url:

        current_repo_name = get_repository_name(
            st.session_state.repo_url
        )

        if st.session_state.repo_ready:

            st.markdown(
                f"""
                <div style="
                    padding: 10px 12px;
                    border-radius: 9px;
                    border: 1px solid rgba(255,255,255,0.10);
                    background: rgba(255,255,255,0.025);
                    margin-bottom: 10px;
                ">
                    🟢 <strong>{current_repo_name}</strong>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                f"""
                <div style="
                    padding: 10px 12px;
                    border-radius: 9px;
                    border: 1px solid rgba(255,255,255,0.10);
                    background: rgba(255,255,255,0.025);
                    margin-bottom: 10px;
                ">
                    📦 <strong>{current_repo_name}</strong><br>
                    <small style="color:#888;">
                        Repository not loaded
                    </small>
                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.caption(
            "No repository selected."
        )

    st.divider()

    # Previous Chats

    st.markdown(
        '<div class="sidebar-heading">💬 Previous Chats</div>',
        unsafe_allow_html=True
    )

    try:

        conversations = get_conversations(st.session_state.user_id)

        if conversations:

            for conversation in conversations:

                conversation_id = conversation[0]
                title = conversation[1] or "Conversation"
                repository_url = conversation[2] or ""

                repository_name = (
                    get_repository_name(repository_url)
                    if repository_url
                    else "No repository"
                )

                # Limit long titles
                display_title = title

                if len(display_title) > 30:

                    display_title = (
                        display_title[:30].rstrip()
                        + "..."
                    )

                # Chat + Delete columns

                chat_col, delete_col = st.columns(
                    [5, 1]
                )

                with chat_col:

                    if st.button(
                        f"💬 {display_title}",
                        key=f"chat_{conversation_id}",
                        use_container_width=True
                    ):

                        load_previous_chat(
                            conversation_id
                        )

                        st.rerun()

                with delete_col:

                    if st.button(
                        "🗑️",
                        key=f"delete_{conversation_id}",
                        help="Delete this conversation"
                    ):

                        delete_conversation(
                            st.session_state.user_id,
                            conversation_id
                        )

                        if (
                            st.session_state.conversation_id
                            == conversation_id
                        ):

                            st.session_state.conversation_id = None
                            st.session_state.messages = []
                            st.session_state.conversation_title = (
                                "New Conversation"
                            )

                        st.rerun()

                st.markdown(
                    f"""
                    <div style="
                        margin-left: 14px;
                        margin-top: -8px;
                        margin-bottom: 10px;
                        color: #888;
                        font-size: 0.75rem;
                    ">
                        📦 {repository_name}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:

            st.caption(
                "No previous chats yet."
            )

    except Exception as e:

        st.warning(
            f"Could not load chats: {e}"
        )

# MAIN APPLICATION UI

if "pending_analysis_url" not in st.session_state:
    st.session_state.pending_analysis_url = ""

if "repo_stats" not in st.session_state:
    st.session_state.repo_stats = {
        "documents": 0,
        "code": 0,
        "documentation": 0
    }

# NEW CHAT / ANALYSIS LANDING SCREEN

if (
    not st.session_state.repo_ready
    and not st.session_state.pending_analysis_url
):

    st.markdown(
        """
        <div class="subtitle">
            Analyze, understand and explore any public GitHub
            repository with repository-aware RAG.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="welcome-wrap">'
        '<div class="welcome-icon">⌘</div>'
        '<div class="welcome-title">Start a new analysis</div>'
        '<div class="welcome-subtitle">'
        'Paste a public GitHub repository URL below to inspect its '
        'architecture, understand the code, and ask repository-aware questions.'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="url-label">GitHub Repository URL</div>',
        unsafe_allow_html=True
    )

    repo_url_input = st.text_input(
        "GitHub Repository URL",
        value="",
        placeholder="https://github.com/user/repository",
        label_visibility="collapsed"
    )

    analyze_button = st.button(
        "🔍  Analyze Repository",
        use_container_width=True
    )

    st.markdown(
        """
        <div class="url-hint">
            Supports public GitHub repositories
        </div>
        """,
        unsafe_allow_html=True
    )

    if analyze_button:

        if not repo_url_input.strip():

            st.error(
                "Please enter a GitHub repository URL."
            )

        elif "github.com" not in repo_url_input.lower():

            st.error(
                "Please enter a valid GitHub repository URL."
            )

        else:

            st.session_state.pending_analysis_url = (
                repo_url_input.strip()
            )

            st.session_state.repo_url = (
                repo_url_input.strip()
            )

            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.session_state.conversation_title = (
                "New Conversation"
            )

            st.rerun()

# REPOSITORY ANALYSIS PROGRESS

elif (
    not st.session_state.repo_ready
    and st.session_state.pending_analysis_url
):

    analysis_col, _ = st.columns(
        [3.2, 1.15],
        gap="large"
    )

    with analysis_col:

        st.markdown(
            """
            <div class="subtitle">
                Preparing your repository workspace...
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="analysis-progress-card">
                <div class="analysis-progress-title">
                    ⚙️ Repository Analysis
                </div>
                <div class="analysis-progress-subtitle">
                    This may take a little longer for larger repositories.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        try:

            with st.status(
                "Analyzing repository...",
                expanded=True
            ) as status:

                prepare_repository(
                    st.session_state.pending_analysis_url,
                    status
                )

                # Calculate repository metrics once after preparation.
                load_repository, _, _ = (
                    get_repository_functions()
                )

                documents = load_repository(
                    REPO_PATH
                )

                code_count = sum(
                    1
                    for document in documents
                    if document["type"] == "code"
                )

                documentation_count = sum(
                    1
                    for document in documents
                    if document["type"] == "documentation"
                )

                st.session_state.repo_stats = {
                    "documents": len(documents),
                    "code": code_count,
                    "documentation": documentation_count
                }

                status.update(
                    label="Repository ready!",
                    state="complete"
                )

            st.session_state.repo_ready = True
            st.session_state.pending_analysis_url = ""

            st.rerun()

        except Exception as e:

            st.session_state.repo_ready = False
            st.session_state.pending_analysis_url = ""

            st.error(
                f"Analysis failed: {str(e)}"
            )

# REPOSITORY DASHBOARD

elif st.session_state.repo_ready:

    repo_name = get_repository_name(
        st.session_state.repo_url
    )

    # Use a two-column layout only after a repository exists.
    main_col, right_col = st.columns(
        [3.2, 1.15],
        gap="large"
    )

    with main_col:

        st.markdown(
            """
            <div class="subtitle">
                Ask questions about any public GitHub repository
                using repository-aware RAG.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="repo-identity-card">
                <div class="repo-identity-status">
                    🟢 Repository Ready
                </div>
                <div class="repo-identity-name">
                    📦 {repo_name}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        metric1, metric2, metric3 = st.columns(3)

        with metric1:
            st.metric(
                "Total Documents",
                st.session_state.repo_stats.get(
                    "documents",
                    0
                )
            )

        with metric2:
            st.metric(
                "Code Files",
                st.session_state.repo_stats.get(
                    "code",
                    0
                )
            )

        with metric3:
            st.metric(
                "Documentation",
                st.session_state.repo_stats.get(
                    "documentation",
                    0
                )
            )

        st.markdown(
            '<div class="section-divider"></div>',
            unsafe_allow_html=True
        )

        if not st.session_state.messages:

            st.markdown(
                """
                <div class="empty-chat">
                    <div class="empty-chat-title">
                        What would you like to know?
                    </div>
                    <div class="empty-chat-subtitle">
                        Ask about the architecture, files, functions,
                        dependencies, implementation, or workflow.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            for message in st.session_state.messages:

                with st.chat_message(
                    message["role"]
                ):

                    st.markdown(
                        message["content"]
                    )

                    if (
                        message["role"] == "assistant"
                        and message.get("sources")
                    ):

                        display_sources(
                            message["sources"]
                        )

    # --------------------------------------------------------
    # Right-side Repository Info
    # --------------------------------------------------------

    with right_col:

        st.markdown(
            '<div class="analysis-heading">📊 Repository Info</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            "**Repository**"
        )

        st.code(
            repo_name,
            language=None
        )

        st.markdown(
            "**🧩 Tech Stack**"
        )

        tech_stack = detect_tech_stack(
            REPO_PATH
        )

        for technology in tech_stack:

            st.markdown(
                f"- `{technology}`"
            )

        st.markdown(
            "**Status**"
        )

        st.markdown(
            "🟢 Ready"
        )

        st.markdown(
            "**Vector Store**"
        )

        st.markdown(
            "🔎 FAISS"
        )

        st.markdown(
            "**Embeddings**"
        )

        st.markdown(
            "🧠 Hugging Face"
        )

        st.markdown(
            "**LLM**"
        )

        st.markdown(
            "🤖 Groq"
        )

# CHAT INPUT

if st.session_state.repo_ready:

    question = st.chat_input(
        "Ask a question about the repository..."
    )

    if question:

        if st.session_state.conversation_id is None:

            title = generate_chat_title(
                question
            )

            conversation_id = create_conversation(
                st.session_state.user_id,
                title=title,
                repository_url=st.session_state.repo_url
            )

            st.session_state.conversation_id = (
                conversation_id
            )

            st.session_state.conversation_title = title

        if len(st.session_state.messages) == 0:

            title = generate_chat_title(
                question
            )

            update_conversation(
                st.session_state.user_id,
                st.session_state.conversation_id,
                title=title,
                repository_url=st.session_state.repo_url
            )

            st.session_state.conversation_title = title

        st.session_state.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        save_message(
            st.session_state.user_id,
            st.session_state.conversation_id,
            "user",
            question
        )

        with st.spinner(
            "Searching repository and generating answer..."
        ):

            try:

                generate_answer = get_rag_function()

                answer, results = generate_answer(
                    question
                )

                source_files = []

                for result in results:

                    source_files.append(
                        {
                            "file": result.metadata.get(
                                "file",
                                "Unknown"
                            ),
                            "path": result.metadata.get(
                                "path",
                                ""
                            )
                        }
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": source_files
                    }
                )

                save_message(
                    st.session_state.user_id,
                    st.session_state.conversation_id,
                    "assistant",
                    answer,
                    source_files
                )

            except Exception as e:

                error_message = (
                    f"Unable to generate answer: {str(e)}"
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                        "sources": []
                    }
                )

                save_message(
                    st.session_state.user_id,
                    st.session_state.conversation_id,
                    "assistant",
                    error_message,
                    []
                )

        st.rerun()
