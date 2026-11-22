
document.addEventListener("DOMContentLoaded", async () => {

    /* =====================================
       1. ELEMENT REFERENCES
    ===================================== */

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

    const submitButton = repositoryForm.querySelector(
        'button[type="submit"]'
    );

    let isProcessing = false;
    let retryOperation = null;


    /* =====================================
       2. AUTHENTICATION CHECK
    ===================================== */

    const token = localStorage.getItem("access_token");

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    const repositoriesPromise = loadRepositories();

    try {

        const currentUser = await AuthAPI.getCurrentUser();

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


    /* =====================================
       3. SIDEBAR CONTROLS
    ===================================== */

    menuBtn.addEventListener("click", () => {
        sidebar.classList.add("open");
    });

    closeSidebar.addEventListener("click", () => {
        sidebar.classList.remove("open");
    });


    /* =====================================
       4. REPOSITORY MODAL CONTROLS
    ===================================== */

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


    /* =====================================
       5. PROGRESS AND PROCESSING HELPERS
    ===================================== */

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


    /* =====================================
       6. EXTRACT REPOSITORY NAME
    ===================================== */

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

        const parts = url.pathname
            .split("/")
            .filter(Boolean);

        if (parts.length !== 2) {
            throw new Error(
                "Please enter a repository URL in this format: https://github.com/username/repository"
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


    /* =====================================
       7. REPOSITORY CARD TEMPLATE
    ===================================== */

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

        const description = document.createElement("p");
        description.textContent = repository.github_url;

        const actions = document.createElement("div");
        actions.className = "repository-actions";

        // Open Chat button
        const askButton = document.createElement("button");
        askButton.className = "btn btn-primary";
        askButton.textContent = "Open Chat";

        // Delete Repository button
        const deleteButton = document.createElement("button");
        deleteButton.className = "btn btn-outline";
        deleteButton.textContent = "Delete";
        deleteButton.type = "button";

        heading.append(icon, title);
        actions.append(askButton, deleteButton);

        card.append(heading, description, actions);

        // Open repository chat
        askButton.addEventListener("click", () => {

            window.location.href =
                `dashboard.html?repository_id=${repository.id}`;

        });

        // Delete repository
        deleteButton.addEventListener("click", async () => {

            const confirmed = window.confirm(
                `Are you sure you want to delete "${repository.name}"?\n\nThis will permanently delete the repository, its conversations, messages and indexed files.`
            );

            if (!confirmed) return;

            try {

                deleteButton.disabled = true;
                askButton.disabled = true;
                deleteButton.textContent = "Deleting...";

                await RepositoryAPI.delete(repository.id);

                // Refresh repository cards and count
                await loadRepositories();

            } catch (error) {

                console.error("Repository deletion failed:", error);

                alert(
                    `Unable to delete repository: ${error.message}`
                );

                deleteButton.disabled = false;
                askButton.disabled = false;
                deleteButton.textContent = "Delete";

            }

        });

        return card;

    }


    /* =====================================
       8. LOAD REPOSITORIES
    ===================================== */

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


    /* =====================================
       9. AUTOMATIC CLONE AND INDEX PIPELINE
    ===================================== */

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
                "Step 2 of 2: Analyzing files and creating embeddings. This may take a few minutes..."
            );

            const result = await RepositoryAPI.index(repositoryId);

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


    /* =====================================
       10. RETRY INDEXING
    ===================================== */

    async function retryIndexing(repositoryId) {

        try {

            setProcessing(true);

            showProgress(
                "Retrying repository indexing..."
            );

            submitButton.textContent = "Indexing Repository...";

            const result = await RepositoryAPI.index(repositoryId);

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


    /* =====================================
       11. ADD REPOSITORY
    ===================================== */

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


    /* =====================================
       12. REFRESH REPOSITORIES
    ===================================== */

    refreshRepositoriesBtn.addEventListener("click", loadRepositories);


    /* =====================================
       13. LOGOUT
    ===================================== */

    logoutBtn.addEventListener("click", () => {

        localStorage.removeItem("access_token");

        window.location.href = "login.html";

    });


    // Wait for initial repository loading to finish.
    await repositoriesPromise;

});
