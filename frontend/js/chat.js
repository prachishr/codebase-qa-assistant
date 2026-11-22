
document.addEventListener("DOMContentLoaded", async () => {

    /* =====================================
       1. GET PAGE PARAMETERS
    ===================================== */

    const params = new URLSearchParams(window.location.search);

    const repositoryId = params.get("repository_id");
    const conversationId = params.get("conversation_id");

    const dashboardContent = document.querySelector(".dashboard-content");

    let activeConversation = null;


    /* =====================================
       2. LOAD CONVERSATION HISTORY
    ===================================== */

    async function loadConversationHistory() {

        const conversationList =
            document.getElementById("conversationList");

        try {

            const conversations = await ConversationAPI.getAll();

            document.getElementById("conversationCount").textContent =
                conversations.length;

            conversationList.innerHTML = "";

            if (conversations.length === 0) {

                conversationList.innerHTML = `
                    <p class="empty-conversations">
                        Your conversations will appear here.
                    </p>
                `;

                return;
            }

            conversations.forEach((conversation) => {

                const item = document.createElement("div");
                item.className = "conversation-item-wrapper";

                const conversationButton = document.createElement("button");

                conversationButton.type = "button";
                conversationButton.className = "conversation-item";

                if (String(conversation.id) === conversationId) {
                    conversationButton.classList.add("active");
                }

                const title = document.createElement("span");
                title.className = "conversation-title";
                title.textContent = conversation.title;

                const repository = document.createElement("small");
                repository.className = "conversation-repository";
                repository.textContent =
                    `📦 ${conversation.repository_name}`;

                conversationButton.append(title, repository);

                conversationButton.addEventListener("click", () => {

                    window.location.href =
                        `dashboard.html?repository_id=${conversation.repository_id}` +
                        `&conversation_id=${conversation.id}`;

                });


                // Delete conversation button
                const deleteButton = document.createElement("button");

                deleteButton.type = "button";
                deleteButton.className = "conversation-delete-btn";
                deleteButton.textContent = "×";
                deleteButton.title = "Delete conversation";
                deleteButton.setAttribute(
                    "aria-label",
                    `Delete conversation ${conversation.title}`
                );

                deleteButton.addEventListener("click", async (event) => {

                    event.stopPropagation();

                    const confirmed = window.confirm(
                        `Are you sure you want to delete "${conversation.title}"?\n\nAll messages in this conversation will also be permanently deleted.`
                    );

                    if (!confirmed) return;

                    try {

                        deleteButton.disabled = true;
                        deleteButton.textContent = "...";

                        await ConversationAPI.delete(conversation.id);

                        // If the deleted conversation is currently open,
                        // return to the repository dashboard.
                        if (String(conversation.id) === conversationId) {

                            window.location.href =
                                "dashboard.html";

                            return;

                        }

                        // Refresh conversation history
                        await loadConversationHistory();

                    } catch (error) {

                        console.error(
                            "Conversation deletion failed:",
                            error
                        );

                        alert(
                            `Unable to delete conversation: ${error.message}`
                        );

                        deleteButton.disabled = false;
                        deleteButton.textContent = "×";

                    }

                });

                item.append(conversationButton, deleteButton);

                conversationList.appendChild(item);

            });

        } catch (error) {

            conversationList.innerHTML = `
                <p class="empty-conversations">
                    Unable to load conversations.
                </p>
            `;

            console.error("Conversation history error:", error);

        }

    }


    /* =====================================
       3. INITIALIZE SIDEBAR HISTORY
    ===================================== */

    if (document.getElementById("conversationList")) {
        await loadConversationHistory();
    }


    /* =====================================
       4. NEW CHAT BUTTON
    ===================================== */

    const newChatBtn = document.getElementById("newChatBtn");

    if (newChatBtn) {

        newChatBtn.addEventListener("click", () => {

            window.location.href = "dashboard.html#repositories";

        });

    }


    /* =====================================
       5. CHECK SELECTED REPOSITORY
    ===================================== */

    if (!repositoryId || !dashboardContent) {
        return;
    }


    /* =====================================
       6. CREATE CHAT INTERFACE
    ===================================== */

    const chatSection = document.createElement("section");

    chatSection.className = "chat-section";
    chatSection.id = "chatSection";

    chatSection.innerHTML = `
        <div class="chat-header">
            <div>
                <span class="section-label">AI WORKSPACE</span>
                <h2 id="chatRepositoryName">Loading repository...</h2>
                <p>Your AI-powered repository assistant</p>
            </div>

            <button class="btn btn-outline" id="closeChatBtn">
                ← Back to Dashboard
            </button>
        </div>

        <div class="chat-messages" id="chatMessages">

            <div class="chat-welcome">
                <div class="chat-welcome-icon">✳</div>

                <h3>What would you like to know?</h3>

                <p>
                    Ask questions about project architecture,
                    functions, classes, dependencies or code implementation.
                </p>

                <div class="suggested-questions">

                    <button type="button">
                        What is this project about?
                    </button>

                    <button type="button">
                        Explain the project architecture.
                    </button>

                    <button type="button">
                        How does the ingestion process work?
                    </button>

                </div>

            </div>

        </div>

        <form class="chat-input-area" id="chatForm">

            <textarea
                id="chatQuestion"
                placeholder="Ask anything about your codebase..."
                rows="1"
                required
            ></textarea>

            <button type="submit" id="sendQuestionBtn">
                ↑
            </button>

        </form>

        <p class="chat-disclaimer">
            AI-generated answers may contain inaccuracies.
            Verify important details against the source code.
        </p>
    `;

    dashboardContent.appendChild(chatSection);

    requestAnimationFrame(() => {

        chatSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    });


    /* =====================================
       7. LOAD REPOSITORY AND CONVERSATION
    ===================================== */

    const repositoryNameElement =
        document.getElementById("chatRepositoryName");

    const messagesContainer =
        document.getElementById("chatMessages");

    try {

        const repository = await RepositoryAPI.getById(repositoryId);

        repositoryNameElement.textContent = repository.name;

        if (conversationId) {

            activeConversation =
                await ConversationAPI.getById(conversationId);

            if (String(activeConversation.repository_id) !== repositoryId) {
                throw new Error(
                    "Conversation does not belong to this repository."
                );
            }

            activeConversation.messages.forEach((message) => {

                if (message.role === "user") {
                    addUserMessage(message.content);
                } else {
                    addAIMessage({
                        answer: message.content,
                        sources: []
                    });
                }

            });

        } else {

            activeConversation = await ConversationAPI.create(
                repository.id
            );

            await loadConversationHistory();

        }

    } catch (error) {

        repositoryNameElement.textContent =
            "Unable to open conversation";

        messagesContainer.innerHTML = "";

        const errorMessage = document.createElement("p");
        errorMessage.className = "empty-conversations";
        errorMessage.textContent = error.message;

        messagesContainer.appendChild(errorMessage);

        return;

    }

    requestAnimationFrame(() => {

        chatSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;

    });


    /* =====================================
       8. DISPLAY USER MESSAGE
    ===================================== */

    function addUserMessage(message) {

        const messageElement = document.createElement("div");

        messageElement.className = "chat-message user-message";

        const text = document.createElement("p");
        text.textContent = message;

        messageElement.appendChild(text);

        messagesContainer.appendChild(messageElement);

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;

    }


    /* =====================================
       9. DISPLAY AI RESPONSE
    ===================================== */

    function addAIMessage(response) {

        const messageElement = document.createElement("div");

        messageElement.className = "chat-message ai-message";

        const label = document.createElement("div");
        label.className = "message-label";
        label.textContent = "✳ AI Assistant";

        const answer = document.createElement("p");
        answer.className = "ai-answer";
        answer.textContent = response.answer;

        messageElement.append(label, answer);

        if (response.sources && response.sources.length > 0) {

            const sourcesContainer = document.createElement("div");
            sourcesContainer.className = "message-sources";

            const sourceHeading = document.createElement("h4");
            sourceHeading.textContent = "Sources";

            sourcesContainer.appendChild(sourceHeading);

            response.sources.forEach((source) => {

                const sourceCard = document.createElement("div");
                sourceCard.className = "source-card";

                const fileName = document.createElement("strong");
                fileName.textContent =
                    source.file || source.path || "Repository source";

                const sourcePath = document.createElement("small");
                sourcePath.textContent =
                    source.path || source.file || "";

                sourceCard.append(fileName, sourcePath);

                sourcesContainer.appendChild(sourceCard);

            });

            messageElement.appendChild(sourcesContainer);

        }

        messagesContainer.appendChild(messageElement);

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;

    }


    /* =====================================
       10. LOADING INDICATOR
    ===================================== */

    function showLoadingMessage() {

        const loadingElement = document.createElement("div");

        loadingElement.className =
            "chat-message ai-message loading-message";

        loadingElement.id = "aiLoadingMessage";
        loadingElement.textContent = "AI is thinking...";

        messagesContainer.appendChild(loadingElement);

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;

    }


    /* =====================================
       11. SEND QUESTION TO FASTAPI
    ===================================== */

    async function sendQuestion(question) {

        addUserMessage(question);

        showLoadingMessage();

        const sendButton =
            document.getElementById("sendQuestionBtn");

        const questionInput =
            document.getElementById("chatQuestion");

        sendButton.disabled = true;
        questionInput.disabled = true;

        try {

            const response = await apiRequest(
                `/repositories/${repositoryId}/ask`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        conversation_id: activeConversation.id,
                        question: question
                    })
                }
            );

            document.getElementById("aiLoadingMessage")?.remove();

            addAIMessage(response);

            // Refresh sidebar in case the conversation title changed
            await loadConversationHistory();

        } catch (error) {

            document.getElementById("aiLoadingMessage")?.remove();

            const errorElement = document.createElement("div");

            errorElement.className = "chat-message ai-message";
            errorElement.textContent =
                `Unable to generate an answer: ${error.message}`;

            messagesContainer.appendChild(errorElement);

        } finally {

            sendButton.disabled = false;
            questionInput.disabled = false;
            questionInput.focus();

        }

    }


    /* =====================================
       12. CHAT FORM SUBMISSION
    ===================================== */

    const chatForm = document.getElementById("chatForm");

    chatForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        const questionInput =
            document.getElementById("chatQuestion");

        const question = questionInput.value.trim();

        if (!question) {
            return;
        }

        questionInput.value = "";

        await sendQuestion(question);

    });


    /* =====================================
       13. SUGGESTED QUESTIONS
    ===================================== */

    document.querySelectorAll(".suggested-questions button")
        .forEach((button) => {

            button.addEventListener("click", async () => {

                if (document.getElementById("sendQuestionBtn").disabled) {
                    return;
                }

                await sendQuestion(button.textContent.trim());

            });

        });


    /* =====================================
       14. BACK TO DASHBOARD
    ===================================== */

    document.getElementById("closeChatBtn")
        .addEventListener("click", () => {

            window.location.href = "dashboard.html";

        });

});
