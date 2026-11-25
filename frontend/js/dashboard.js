
document.addEventListener("DOMContentLoaded", async () => {

    // =====================================
    // 1. ELEMENT REFERENCES
    // =====================================

    const sidebar = document.getElementById("sidebar");
    const menuBtn = document.getElementById("menuBtn");
    const closeSidebar = document.getElementById("closeSidebar");

    const repositoryModal = document.getElementById("repositoryModal");
    const addRepositoryBtn = document.getElementById("addRepositoryBtn");
    const emptyAddRepositoryBtn = document.getElementById("emptyAddRepositoryBtn");
    const closeRepositoryModal = document.getElementById("closeRepositoryModal");

    const repositoryForm = document.getElementById("repositoryForm");
    const repositoryGrid = document.getElementById("repositoryGrid");
    const repositoryProgress = document.getElementById("repositoryProgress");
    const githubUrlInput = document.getElementById("githubUrl");

    const refreshRepositoriesBtn = document.getElementById("refreshRepositoriesBtn");
    const logoutBtn = document.getElementById("logoutBtn");
    const headerLogoutBtn = document.getElementById("headerLogoutBtn");

    const changePasswordModal = document.getElementById("changePasswordModal");
    const changePasswordBtn = document.getElementById("changePasswordBtn");
    const closeChangePasswordModal = document.getElementById("closeChangePasswordModal");
    const changePasswordForm = document.getElementById("changePasswordForm");
    const changePasswordMessage = document.getElementById("changePasswordMessage");
    const changePasswordSubmitBtn = document.getElementById("changePasswordSubmitBtn");
    const forgotCurrentPasswordBtn = document.getElementById("forgotCurrentPasswordBtn");

    const submitButton = repositoryForm.querySelector(
        'button[type="submit"]'
    );

    let isProcessing = false;
    let retryOperation = null;
    let currentUserEmail = "";


    // =====================================
    // 2. AUTHENTICATION CHECK
    // =====================================

    const token = localStorage.getItem("access_token");

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    const repositoriesPromise = loadRepositories();

    try {

        const currentUser = await AuthAPI.getCurrentUser();
        currentUserEmail = currentUser.email;

        document.getElementById("sidebarUsername").textContent =
            currentUser.username;

        document.getElementById("sidebarEmail").textContent =
            currentUser.email;

        document.getElementById("welcomeUsername").textContent =
            currentUser.username.split(" ")[0];

        document.getElementById("userAvatar").textContent =
            currentUser.username.charAt(0).toUpperCase();

    } catch (error) {

        if (error.status === 401 || error.status === 403) {
            localStorage.removeItem("access_token");
            window.location.href = "login.html";
            return;
        }

        console.error("Unable to verify user:", error);

        alert(
            "Unable to verify your session. Please check your backend connection and try again."
        );

        return;
    }


    // =====================================
    // 3. SIDEBAR CONTROLS
    // =====================================

    menuBtn.addEventListener("click", () => {
        sidebar.classList.add("open");
    });

    closeSidebar.addEventListener("click", () => {
        sidebar.classList.remove("open");
    });


    // =====================================
    // 4. REPOSITORY MODAL CONTROLS
    // =====================================

    function openRepositoryModal() {

        if (isProcessing) return;

        repositoryModal.classList.add("active");

        repositoryProgress.textContent = "";
        repositoryProgress.style.color = "";

        retryOperation = null;

        repositoryForm.reset();

        submitButton.disabled = false;
        submitButton.textContent = "Connect & Index Repository";
    }

    function closeModal() {

        if (isProcessing) return;

        repositoryModal.classList.remove("active");

        repositoryProgress.textContent = "";
        retryOperation = null;
    }

    addRepositoryBtn.addEventListener("click", openRepositoryModal);

    emptyAddRepositoryBtn.addEventListener("click", openRepositoryModal);

    closeRepositoryModal.addEventListener("click", closeModal);

    repositoryModal.addEventListener("click", (event) => {

        if (event.target === repositoryModal) {
            closeModal();
        }
    });


    // =====================================
    // 5. PROGRESS AND PROCESSING HELPERS
    // =====================================

    function showProgress(message, color = "#93c5fd") {

        repositoryProgress.style.color = color;
        repositoryProgress.textContent = message;
    }

    function setProcessing(processing) {

        isProcessing = processing;

        submitButton.disabled = processing;
        githubUrlInput.disabled = processing;
        closeRepositoryModal.disabled = processing;

        if (processing) {
            submitButton.textContent = "Please wait...";
        }
    }

    async function waitForIndexingCompletion(repositoryId, onProgress) {

        const pollIntervalMs = 2000;
        const maxWaitMs = 15 * 60 * 1000;
        const startedAt = Date.now();

        while (Date.now() - startedAt < maxWaitMs) {
            await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));

            const statusData = await RepositoryAPI.getStatus(repositoryId);

            if (typeof onProgress === "function") {
                onProgress(statusData);
            }

            if (statusData.status === "completed") {
                return statusData;
            }

            if (statusData.status === "failed") {
                throw new Error(
                    statusData.error || statusData.message || "Indexing failed."
                );
            }

            if (statusData.status === "idle") {
                throw new Error(
                    "Indexing was interrupted (backend restarted). " +
                    "Start uvicorn with --reload-dir backend --reload-dir core (or python run.py) and try again."
                );
            }
        }

        throw new Error(
            "Indexing is taking longer than expected. Please refresh and check repository status."
        );
    }


    // =====================================
    // 6. EXTRACT REPOSITORY NAME
    // =====================================

    function getRepositoryDetails(githubUrl) {

        let url;

        try {
            url = new URL(githubUrl);
        } catch {
            throw new Error("Please enter a valid GitHub repository URL.");
        }

        if (
            url.hostname.toLowerCase() !== "github.com" ||
            url.protocol !== "https:"
        ) {
            throw new Error(
                "Please enter a valid public GitHub repository URL."
            );
        }

        const parts = url.pathname.split("/").filter(Boolean);

        if (parts.length !== 2) {
            throw new Error(
                "Please enter a repository URL in owner/repository format."
            );
        }

        const username = parts[0];
        const repositoryName = parts[1].replace(/\.git$/i, "");

        if (!username || !repositoryName) {
            throw new Error("Invalid GitHub repository URL.");
        }

        return {
            name: repositoryName,
            github_url: `https://github.com/${username}/${repositoryName}`
        };
    }


    // =====================================
    // 7. REPOSITORY CARD TEMPLATE
    // =====================================

    function createRepositoryCard(repository) {

        const card = document.createElement("article");
        card.className = "repository-card";

        const heading = document.createElement("div");
        heading.className = "repository-card-header";

        const icon = document.createElement("div");
        icon.className = "repository-card-icon";
        icon.textContent = "▣";

        const title = document.createElement("h3");
        title.textContent = repository.name;

        const statusBadge = document.createElement("span");
        statusBadge.className = repository.indexed
            ? "repo-status-badge indexed"
            : "repo-status-badge not-indexed";
        statusBadge.textContent = repository.indexed
            ? "Indexed"
            : "Not Indexed";

        const description = document.createElement("p");
        description.textContent = repository.github_url;

        const actions = document.createElement("div");
        actions.className = "repository-actions";


        // Open Chat button
        const askButton = document.createElement("button");
        askButton.className = "btn btn-primary";
        askButton.textContent = "Open Chat";
        askButton.type = "button";


        // Re-index button
        const reindexButton = document.createElement("button");
        reindexButton.className = "btn btn-outline";
        reindexButton.textContent = repository.indexed ? "Re-index" : "Index";
        reindexButton.type = "button";


        // Delete Repository button
        const deleteButton = document.createElement("button");
        deleteButton.className = "btn btn-outline";
        deleteButton.textContent = "Delete";
        deleteButton.type = "button";


        heading.append(icon, title, statusBadge);

        actions.append(
            askButton,
            reindexButton,
            deleteButton
        );

        card.append(heading, description, actions);


        // ---------------------------------
        // OPEN CHAT
        // ---------------------------------

        askButton.addEventListener("click", () => {

            window.location.href =
                `dashboard.html?repository_id=${repository.id}`;

        });


        // ---------------------------------
        // RE-INDEX REPOSITORY
        // ---------------------------------

        reindexButton.addEventListener("click", async () => {

            const confirmed = window.confirm(
                `Re-index "${repository.name}"?\n\n` +
                "This will clone the latest GitHub version and recreate its FAISS index. " +
                "Existing conversations and messages will be preserved."
            );

            if (!confirmed) return;

            try {

                reindexButton.disabled = true;
                askButton.disabled = true;
                deleteButton.disabled = true;

                reindexButton.textContent = "Starting...";

                const initialResult = await RepositoryAPI.reindex(repository.id);

                let finalResult = initialResult;

                if (initialResult.status === "processing") {
                    reindexButton.textContent = "Cloning...";

                    finalResult = await waitForIndexingCompletion(
                        repository.id,
                        (statusData) => {
                            if (statusData.stage === "cloning") {
                                reindexButton.textContent = "Cloning...";
                            } else if (statusData.stage === "indexing") {
                                reindexButton.textContent = "Indexing...";
                            }
                        }
                    );
                }

                alert(
                    `Repository re-indexed successfully!\n\n` +
                    `Documents: ${finalResult.documents_processed ?? "N/A"}\n` +
                    `Chunks: ${finalResult.chunks_created ?? "N/A"}`
                );

                await loadRepositories();

            } catch (error) {

                console.error("Repository re-indexing failed:", error);

                alert(
                    `Unable to re-index repository: ${error.message}`
                );

                reindexButton.disabled = false;
                askButton.disabled = false;
                deleteButton.disabled = false;

                reindexButton.textContent = repository.indexed ? "Re-index" : "Index";
            }
        });


        // ---------------------------------
        // DELETE REPOSITORY
        // ---------------------------------

        deleteButton.addEventListener("click", async () => {

            const confirmed = window.confirm(
                `Are you sure you want to delete "${repository.name}"?\n\n` +
                "This will permanently delete the repository, its conversations, messages and indexed files."
            );

            if (!confirmed) return;

            try {

                deleteButton.disabled = true;
                askButton.disabled = true;
                reindexButton.disabled = true;

                deleteButton.textContent = "Deleting...";

                await RepositoryAPI.delete(repository.id);

                await loadRepositories();

            } catch (error) {

                console.error("Repository deletion failed:", error);

                alert(
                    `Unable to delete repository: ${error.message}`
                );

                deleteButton.disabled = false;
                askButton.disabled = false;
                reindexButton.disabled = false;

                deleteButton.textContent = "Delete";
            }
        });

        return card;
    }


    // =====================================
    // 8. LOAD REPOSITORIES
    // =====================================

    async function loadRepositories() {

        repositoryGrid.innerHTML = `
            <div class="empty-state">
                <p>Loading repositories...</p>
            </div>
        `;

        try {

            const repositories = await RepositoryAPI.getAll();

            document.getElementById("repositoryCount").textContent =
                repositories.length;

            repositoryGrid.innerHTML = "";

            if (repositories.length === 0) {

                repositoryGrid.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">▣</div>
                        <h3>No repositories yet</h3>
                        <p>
                            Add your first GitHub repository to start
                            exploring your codebase with AI.
                        </p>
                        <button class="btn btn-primary" id="firstRepositoryBtn">
                            Add Your First Repository
                        </button>
                    </div>
                `;

                document.getElementById("firstRepositoryBtn")
                    .addEventListener("click", openRepositoryModal);

                return;
            }

            repositories.forEach((repository) => {

                repositoryGrid.appendChild(
                    createRepositoryCard(repository)
                );

            });

        } catch (error) {

            repositoryGrid.innerHTML = `
                <div class="empty-state">
                    <h3>Unable to load repositories</h3>
                    <p></p>
                    <button class="btn btn-outline" id="retryRepositoriesBtn">
                        Try Again
                    </button>
                </div>
            `;

            repositoryGrid.querySelector(".empty-state p").textContent =
                error.message;

            document.getElementById("retryRepositoriesBtn")
                .addEventListener("click", loadRepositories);
        }
    }


    // =====================================
    // 9. AUTOMATIC CLONE AND INDEX PIPELINE
    // =====================================

    async function cloneAndIndex(repositoryId) {

        try {

            // STEP 1: CLONE

            showProgress(
                "Step 1 of 2: Cloning your GitHub repository..."
            );

            submitButton.textContent = "Cloning Repository...";

            await RepositoryAPI.clone(repositoryId);

            showProgress(
                "Repository cloned successfully! Starting indexing..."
            );


            // STEP 2: INDEX

            retryOperation = {
                repositoryId,
                stage: "index"
            };

            submitButton.disabled = true;
            submitButton.textContent = "Indexing Repository...";

            showProgress(
                "Step 2 of 2: Analyzing files and creating FAISS embeddings..."
            );

            const initialResult = await RepositoryAPI.index(repositoryId, true);

            const result = initialResult.status === "processing"
                ? await waitForIndexingCompletion(repositoryId, (statusData) => {
                    if (statusData.message) {
                        showProgress(`Step 2 of 2: ${statusData.message}`);
                    }
                })
                : initialResult;

            retryOperation = null;

            showProgress(
                `Repository indexed successfully! Documents: ${result.documents_processed ?? "N/A"} | Chunks: ${result.chunks_created ?? "N/A"}`,
                "#86efac"
            );

            submitButton.textContent = "Repository Ready ✓";
            submitButton.disabled = true;

            await loadRepositories();

            setTimeout(() => {

                repositoryModal.classList.remove("active");

                repositoryForm.reset();

                repositoryProgress.textContent = "";

                submitButton.disabled = false;
                submitButton.textContent = "Connect & Index Repository";

            }, 2000);

        } catch (error) {

            console.error("Repository processing error:", error);

            showProgress(
                `Processing failed: ${error.message}`,
                "#fca5a5"
            );

            submitButton.disabled = false;

            if (retryOperation) {
                submitButton.textContent = "Retry Indexing";
            } else {
                submitButton.textContent = "Retry Cloning";
            }

            await loadRepositories();
        }
    }


    // =====================================
    // 10. RETRY INDEXING
    // =====================================

    async function retryIndexing(repositoryId) {

        try {

            setProcessing(true);

            showProgress("Retrying repository indexing...");

            submitButton.textContent = "Indexing Repository...";

            const initialResult = await RepositoryAPI.index(repositoryId, true);

            const result = initialResult.status === "processing"
                ? await waitForIndexingCompletion(repositoryId, (statusData) => {
                    if (statusData.message) {
                        showProgress(statusData.message);
                    }
                })
                : initialResult;

            retryOperation = null;

            showProgress(
                `Repository indexed successfully! Documents: ${result.documents_processed ?? "N/A"} | Chunks: ${result.chunks_created ?? "N/A"}`,
                "#86efac"
            );

            submitButton.textContent = "Repository Ready ✓";

            await loadRepositories();

            setTimeout(() => {

                repositoryModal.classList.remove("active");

                repositoryForm.reset();

                repositoryProgress.textContent = "";

                submitButton.disabled = false;
                submitButton.textContent = "Connect & Index Repository";

            }, 2000);

        } catch (error) {

            showProgress(
                `Indexing failed: ${error.message}`,
                "#fca5a5"
            );

            submitButton.disabled = false;
            submitButton.textContent = "Retry Indexing";

        } finally {

            isProcessing = false;
            githubUrlInput.disabled = false;
        }
    }


    // =====================================
    // 11. ADD REPOSITORY
    // =====================================

    repositoryForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        if (isProcessing) return;

        // Retry an operation without creating a duplicate record.

        if (retryOperation) {

            if (retryOperation.stage === "index") {

                await retryIndexing(retryOperation.repositoryId);

            } else {

                setProcessing(true);

                await cloneAndIndex(retryOperation.repositoryId);

                isProcessing = false;
                githubUrlInput.disabled = false;
            }

            return;
        }

        const githubUrl = githubUrlInput.value.trim();

        try {

            setProcessing(true);

            showProgress("Validating GitHub repository URL...");

            const repositoryData = getRepositoryDetails(githubUrl);

            showProgress("Adding repository to your workspace...");

            submitButton.textContent = "Adding Repository...";

            const repository = await RepositoryAPI.create(repositoryData);

            if (!repository || !repository.id) {
                throw new Error(
                    "Repository was created, but its ID was not returned by the server."
                );
            }

            retryOperation = {
                repositoryId: repository.id,
                stage: "clone"
            };

            await cloneAndIndex(repository.id);

        } catch (error) {

            console.error("Repository connection error:", error);

            showProgress(
                error.message,
                "#fca5a5"
            );

            submitButton.disabled = false;
            submitButton.textContent = "Connect & Index Repository";

        } finally {

            isProcessing = false;
            githubUrlInput.disabled = false;
        }
    });


    // =====================================
    // 12. REFRESH REPOSITORIES
    // =====================================

    refreshRepositoriesBtn.addEventListener("click", loadRepositories);


    // =====================================
    // 13. CHANGE PASSWORD & SIGN OUT
    // =====================================

    function openChangePasswordModal() {
        changePasswordModal.classList.add("active");
        changePasswordForm.reset();
        changePasswordMessage.textContent = "";
        changePasswordMessage.style.color = "";
        changePasswordSubmitBtn.disabled = false;
        changePasswordSubmitBtn.textContent = "Update Password";
    }

    function closePasswordModal() {
        changePasswordModal.classList.remove("active");
        changePasswordMessage.textContent = "";
    }

    if (changePasswordBtn) {
        changePasswordBtn.addEventListener("click", openChangePasswordModal);
    }

    if (closeChangePasswordModal) {
        closeChangePasswordModal.addEventListener("click", closePasswordModal);
    }

    if (changePasswordModal) {
        changePasswordModal.addEventListener("click", (event) => {
            if (event.target === changePasswordModal) {
                closePasswordModal();
            }
        });
    }

    if (forgotCurrentPasswordBtn) {
        forgotCurrentPasswordBtn.addEventListener("click", async () => {
            if (!currentUserEmail) {
                changePasswordMessage.style.color = "#fca5a5";
                changePasswordMessage.textContent = "Unable to detect your account email. Please refresh and try again.";
                return;
            }

            forgotCurrentPasswordBtn.disabled = true;
            forgotCurrentPasswordBtn.textContent = "Sending...";
            changePasswordMessage.style.color = "#93c5fd";
            changePasswordMessage.textContent = `Sending reset link to ${currentUserEmail}...`;

            try {
                await AuthAPI.forgotPassword({ email: currentUserEmail });

                changePasswordMessage.style.color = "#86efac";
                changePasswordMessage.textContent =
                    `Password reset link sent to ${currentUserEmail}. Check your email (Inbox, All Mail, or Spam).`;
            } catch (error) {
                changePasswordMessage.style.color = "#fca5a5";
                changePasswordMessage.textContent = error.message;
            } finally {
                forgotCurrentPasswordBtn.disabled = false;
                forgotCurrentPasswordBtn.textContent = "Forgot password?";
            }
        });
    }

    if (changePasswordForm) {
        changePasswordForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const currentPassword = document.getElementById("currentPassword").value;
            const newPassword = document.getElementById("newPassword").value;
            const confirmNewPassword = document.getElementById("confirmNewPassword").value;

            changePasswordMessage.textContent = "";

            if (newPassword.length < 8) {
                changePasswordMessage.style.color = "#fca5a5";
                changePasswordMessage.textContent = "New password must be at least 8 characters.";
                return;
            }

            if (newPassword !== confirmNewPassword) {
                changePasswordMessage.style.color = "#fca5a5";
                changePasswordMessage.textContent = "New passwords do not match.";
                return;
            }

            if (newPassword === currentPassword) {
                changePasswordMessage.style.color = "#fca5a5";
                changePasswordMessage.textContent = "New password must be different from your current password.";
                return;
            }

            changePasswordSubmitBtn.disabled = true;
            changePasswordSubmitBtn.textContent = "Updating...";

            try {
                const result = await AuthAPI.changePassword({
                    current_password: currentPassword,
                    new_password: newPassword
                });

                changePasswordMessage.style.color = "#86efac";
                changePasswordMessage.textContent = result.message || "Password changed successfully!";
                changePasswordForm.reset();

                setTimeout(() => {
                    closePasswordModal();
                }, 1500);
            } catch (error) {
                changePasswordMessage.style.color = "#fca5a5";
                changePasswordMessage.textContent = error.message;
            } finally {
                changePasswordSubmitBtn.disabled = false;
                changePasswordSubmitBtn.textContent = "Update Password";
            }
        });
    }

    async function signOutUser() {
        try {
            await AuthAPI.logout();
        } catch {
            // Clear local session even if backend is unreachable.
        }
        localStorage.removeItem("access_token");
        window.location.href = "login.html";
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", signOutUser);
    }

    if (headerLogoutBtn) {
        headerLogoutBtn.addEventListener("click", signOutUser);
    }


    // Wait for initial repository loading to finish.
    await repositoriesPromise;

});
