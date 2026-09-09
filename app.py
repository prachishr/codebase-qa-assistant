import os
import shutil

import streamlit as st
from dotenv import load_dotenv
from git import Repo

from chunking import create_chunks
from ingestion import load_repository
from vector_store import create_vector_store
from RAG import generate_answer


# ============================================================
# Configuration
# ============================================================

load_dotenv()

REPO_PATH = "repo"
FAISS_PATH = "faiss_index"


# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="Codebase QA Assistant",
    page_icon="💻",
    layout="wide"
)


# ============================================================
# Custom Styling
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    .source-box {
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #ddd;
        margin-bottom: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# Session State
# ============================================================

if "repo_ready" not in st.session_state:
    st.session_state.repo_ready = False

if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# Header
# ============================================================

st.markdown(
    '<div class="main-title">💻 Codebase QA Assistant</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="subtitle">
    Ask questions about any public GitHub repository using
    repository-aware RAG.
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header("Repository")

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/user/repository"
    )

    analyze_button = st.button(
        "🔍 Analyze Repository",
        use_container_width=True
    )

    st.divider()

    st.markdown("### Pipeline")

    st.markdown(
        """
        1. 📥 Clone repository
        2. 📄 Extract code & docs
        3. 🌳 AST-aware code chunking
        4. 🧠 Generate embeddings
        5. 🔎 FAISS vector search
        6. 🤖 Generate RAG answer
        """
    )

    st.divider()

    if st.session_state.repo_ready:

        st.success("Repository ready")

    else:

        st.info("Analyze a repository to begin.")


# ============================================================
# Repository Analysis
# ============================================================

if analyze_button:

    if not repo_url.strip():

        st.error(
            "Please enter a GitHub repository URL."
        )

    elif "github.com" not in repo_url.lower():

        st.error(
            "Please enter a valid GitHub repository URL."
        )

    else:

        try:

            st.session_state.repo_ready = False
            st.session_state.messages = []

            # ------------------------------------------------
            # Remove previous repository
            # ------------------------------------------------

            if os.path.exists(REPO_PATH):
                try:
                    shutil.rmtree(REPO_PATH)
                except Exception as e:
                    st.error(f"Could not remove old repository folder: {e}")
                    st.stop()

            # ------------------------------------------------
            # Remove previous FAISS index
            # ------------------------------------------------

            if os.path.exists(FAISS_PATH):

                shutil.rmtree(
                    FAISS_PATH,
                    ignore_errors=True
                )

            # ------------------------------------------------
            # Clone repository
            # ------------------------------------------------

            with st.status(
                "Analyzing repository...",
                expanded=True
            ) as status:

                st.write(
                    "📥 Cloning GitHub repository..."
                )

                Repo.clone_from(
                    repo_url.strip(),
                    REPO_PATH,
                    depth=1
                )

                st.write(
                    "📄 Extracting repository files..."
                )

                documents = load_repository(
                    REPO_PATH
                )

                st.write(
                    f"Found {len(documents)} repository documents."
                )

                # ------------------------------------------------
                # Create chunks
                # ------------------------------------------------

                st.write(
                    "🌳 Creating AST-aware and documentation chunks..."
                )

                chunks = create_chunks(
                    documents
                )

                st.write(
                    f"Created {len(chunks)} chunks."
                )

                # ------------------------------------------------
                # Create vector store
                # ------------------------------------------------

                st.write(
                    "🧠 Generating embeddings and building FAISS..."
                )

                create_vector_store()

                st.write(
                    "🔎 FAISS vector database created."
                )

                status.update(
                    label="Repository analyzed successfully!",
                    state="complete"
                )

            st.session_state.repo_ready = True
            st.session_state.repo_url = repo_url.strip()

            st.success(
                "Repository is ready. You can now ask questions!"
            )

        except Exception as e:

            st.session_state.repo_ready = False

            st.error(
                f"Repository analysis failed: {str(e)}"
            )


# ============================================================
# Repository Information
# ============================================================

if st.session_state.repo_ready:

    st.subheader("Repository Ready")

    col1, col2, col3 = st.columns(3)

    try:

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

        git_count = sum(
            1
            for document in documents
            if document["type"] == "git_history"
        )

        with col1:

            st.metric(
                "Total Documents",
                len(documents)
            )

        with col2:

            st.metric(
                "Code Files",
                code_count
            )

        with col3:

            st.metric(
                "Documentation Files",
                documentation_count
            )

    except Exception:

        pass

    st.divider()


# ============================================================
# Chat History
# ============================================================

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

            with st.expander(
                "📚 Sources"
            ):

                displayed_sources = set()

                for source in message["sources"]:

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


# ============================================================
# Question Input
# ============================================================

if st.session_state.repo_ready:

    question = st.chat_input(
        "Ask a question about the repository..."
    )

    if question:

        # ----------------------------------------------------
        # Display user question
        # ----------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        with st.chat_message("user"):

            st.markdown(question)

        # ----------------------------------------------------
        # Generate answer
        # ----------------------------------------------------

        with st.chat_message("assistant"):

            with st.spinner(
                "Searching the repository and generating an answer..."
            ):

                try:

                    answer, results = generate_answer(
                        question
                    )

                    st.markdown(answer)

                    # ----------------------------------------
                    # Sources
                    # ----------------------------------------

                    if results:

                        with st.expander(
                            "📚 Sources"
                        ):

                            displayed_sources = set()

                            for source in results:

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

                    # ----------------------------------------
                    # Save conversation
                    # ----------------------------------------

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": results
                        }
                    )

                except Exception as e:

                    error_message = (
                        f"Unable to generate answer: {str(e)}"
                    )

                    st.error(
                        error_message
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_message,
                            "sources": []
                        }
                    )

else:

    st.info(
        "👈 Enter a public GitHub repository URL "
        "in the sidebar and click **Analyze Repository** "
        "to get started."
    )