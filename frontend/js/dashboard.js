
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
    const repositoryMessage = document.getElementById("repositoryMessage");

    const refreshRepositoriesBtn = document.getElementById("refreshRepositoriesBtn");
    const logoutBtn = document.getElementById("logoutBtn");


    /* =====================================
       2. AUTHENTICATION CHECK
    ===================================== */

    const token = localStorage.getItem("access_token");

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    /*
       Start repository loading immediately.
       This runs alongside the current-user request.
    */

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

        localStorage.removeItem("access_token");
        window.location.href = "login.html";
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
        repositoryModal.classList.add("active");
        repositoryMessage.textContent = "";
    }

    function closeModal() {
        repositoryModal.classList.remove("active");
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
       5. REPOSITORY CARD TEMPLATE
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

        const cloneButton = document.createElement("button");
        cloneButton.className = "btn btn-outline";
        cloneButton.textContent = "Clone";

        const indexButton = document.createElement("button");
        indexButton.className = "btn btn-primary";
        indexButton.textContent = "Index";

        const askButton = document.createElement("button");
        askButton.className = "btn btn-outline";
        askButton.textContent = "Open Chat";

        heading.append(icon, title);
        actions.append(cloneButton, indexButton, askButton);
        card.append(heading, description, actions);


        cloneButton.addEventListener("click", async () => {

            cloneButton.disabled = true;
            cloneButton.textContent = "Cloning...";

            try {

                await RepositoryAPI.clone(repository.id);

                cloneButton.textContent = "Cloned ✓";

            } catch (error) {

                alert(error.message);
                cloneButton.disabled = false;
                cloneButton.textContent = "Clone";

            }

        });


        indexButton.addEventListener("click", async () => {

            indexButton.disabled = true;
            indexButton.textContent = "Indexing...";

            try {

                const result = await RepositoryAPI.index(repository.id);

                indexButton.textContent = "Indexed ✓";

                alert(
                    `Indexing completed!\n\n` +
                    `Documents: ${result.documents_processed}\n` +
                    `Chunks: ${result.chunks_created}`
                );

            } catch (error) {

                alert(error.message);
                indexButton.disabled = false;
                indexButton.textContent = "Index";

            }

        });


        askButton.addEventListener("click", () => {

            window.location.href =
                `dashboard.html?repository_id=${repository.id}`;

        });

        return card;

    }


    /* =====================================
       6. LOAD REPOSITORIES
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
                repositoryGrid.appendChild(createRepositoryCard(repository));
            });

        } catch (error) {

            repositoryGrid.innerHTML = `
                <div class="empty-state">
                    <h3>Unable to load repositories</h3>
                    <p>${error.message}</p>
                    <button class="btn btn-outline" id="retryRepositoriesBtn">
                        Try Again
                    </button>
                </div>
            `;

            document.getElementById("retryRepositoriesBtn")
                .addEventListener("click", loadRepositories);

        }

    }


    /* =====================================
       7. ADD REPOSITORY
    ===================================== */

    repositoryForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        const name = document.getElementById("repositoryName").value.trim();
        const github_url = document.getElementById("githubUrl").value.trim();

        const submitButton = repositoryForm.querySelector(
            'button[type="submit"]'
        );

        repositoryMessage.textContent = "";

        submitButton.disabled = true;
        submitButton.textContent = "Connecting...";

        try {

            await RepositoryAPI.create({
                name,
                github_url
            });

            repositoryMessage.style.color = "#86efac";
            repositoryMessage.textContent = "Repository added successfully!";

            repositoryForm.reset();

            await loadRepositories();

            setTimeout(() => {
                closeModal();
            }, 1000);

        } catch (error) {

            repositoryMessage.style.color = "#fca5a5";
            repositoryMessage.textContent = error.message;

        } finally {

            submitButton.disabled = false;
            submitButton.textContent = "Connect Repository";

        }

    });


    /* =====================================
       8. REFRESH REPOSITORIES
    ===================================== */

    refreshRepositoriesBtn.addEventListener("click", loadRepositories);


    /* =====================================
       9. LOGOUT
    ===================================== */

    logoutBtn.addEventListener("click", () => {

        localStorage.removeItem("access_token");

        window.location.href = "login.html";

    });

});
