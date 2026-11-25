
// =========================================
// API BASE URL
// =========================================

const PRODUCTION_API_BASE_URL = "https://codebase-qa-assistant-r80e.onrender.com/api/v1";
const LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api/v1";

let resolvedApiBaseUrlPromise = null;

function isLocalFrontendHost() {
    const host = window.location.hostname;
    return (
        host === "localhost" ||
        host === "127.0.0.1" ||
        host === "::1" ||
        host === ""
    );
}

async function resolveApiBaseUrl() {
    if (resolvedApiBaseUrlPromise) {
        return resolvedApiBaseUrlPromise;
    }

    resolvedApiBaseUrlPromise = (async () => {
        const customUrl = localStorage.getItem("api_base_url");
        if (customUrl) {
            return customUrl.replace(/\/+$/, "");
        }

        if (isLocalFrontendHost()) {
            return LOCAL_API_BASE_URL;
        }

        return PRODUCTION_API_BASE_URL;
    })();

    return resolvedApiBaseUrlPromise;
}

async function warmupServer() {
    try {
        const baseUrl = await resolveApiBaseUrl();
        const rootUrl = baseUrl.replace(/\/api\/v1\/?$/, "");
        await fetch(`${rootUrl}/health`, { method: "GET" });
    } catch {
        // Ignore warmup failures; actual requests will handle errors.
    }
}


// =========================================
// COMMON API REQUEST HANDLER
// =========================================

async function apiRequest(endpoint, options = {}) {

    const baseUrl = await resolveApiBaseUrl();
    const token = localStorage.getItem("access_token");
    const timeoutMs = options.timeoutMs ?? 150000;

    const headers = {
        "Content-Type": "application/json",
        ...options.headers
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {

        const { timeoutMs: _ignored, ...fetchOptions } = options;

        const response = await fetch(
            `${baseUrl}${endpoint}`,
            {
                ...fetchOptions,
                headers,
                signal: options.signal || controller.signal
            }
        );

        const contentType = response.headers.get("content-type");

        let data = {};

        if (contentType && contentType.includes("application/json")) {
            data = await response.json();
        }

        if (!response.ok) {

            const errorMessage =
                data?.detail || "Something went wrong. Please try again.";

            const error = new Error(errorMessage);
            error.status = response.status;

            throw error;
        }

        return data;

    } catch (error) {

        if (error.name === "AbortError") {
            throw new Error(
                "Request timed out while waiting for the server. Please try again."
            );
        }

        if (error instanceof TypeError) {
            if (isLocalFrontendHost() && !localStorage.getItem("api_base_url")) {
                throw new Error(
                    "Unable to connect to local backend (http://127.0.0.1:8000). Make sure the FastAPI server is running (python run.py)."
                );
            }
            throw new Error(
                "Unable to connect to the server. Please check your internet connection."
            );
        }

        throw error;
    } finally {
        clearTimeout(timer);
    }
}


// =========================================
// AUTHENTICATION API
// =========================================

const AuthAPI = {

    signup: async (userData) => {

        return await apiRequest("/auth/signup", {
            method: "POST",
            body: JSON.stringify(userData)
        });

    },

    register: async (userData) => {

        return await apiRequest("/auth/signup", {
            method: "POST",
            body: JSON.stringify(userData)
        });

    },

    login: async (credentials) => {

        return await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify(credentials)
        });

    },

    getCurrentUser: async () => {

        return await apiRequest("/auth/me", {
            method: "GET"
        });

    },

    changePassword: async (passwordData) => {

        return await apiRequest("/auth/change-password", {
            method: "POST",
            body: JSON.stringify(passwordData)
        });

    },

    logout: async () => {

        return await apiRequest("/auth/logout", {
            method: "POST",
            timeoutMs: 3000
        });

    },

    forgotPassword: async (payload) => {

        return await apiRequest("/auth/forgot-password", {
            method: "POST",
            body: JSON.stringify(payload)
        });

    },

    resetPassword: async (payload) => {

        return await apiRequest("/auth/reset-password", {
            method: "POST",
            body: JSON.stringify(payload)
        });

    }

};


// =========================================
// REPOSITORY API
// =========================================

const RepositoryAPI = {

    // Add new repository
    create: async (repositoryData) => {

        return await apiRequest("/repositories/", {
            method: "POST",
            body: JSON.stringify(repositoryData)
        });

    },

    // Get all repositories
    getAll: async () => {

        return await apiRequest("/repositories/", {
            method: "GET"
        });

    },

    // Get one repository
    getById: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}`, {
            method: "GET"
        });

    },

    // Clone repository
    clone: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/clone`, {
            method: "POST"
        });

    },

    // Index repository
    index: async (repositoryId, background = false) => {

        const query = background ? "?background=true" : "";
        return await apiRequest(`/repositories/${repositoryId}/index${query}`, {
            method: "POST"
        });

    },

    // Re-index existing repository
    reindex: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/reindex`, {
            method: "POST"
        });

    },

    // Get indexing / re-indexing job status
    getStatus: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/status`, {
            method: "GET"
        });

    },

    // Delete repository
    delete: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}`, {
            method: "DELETE"
        });

    }

};


// =========================================
// CONVERSATION API
// =========================================

const ConversationAPI = {

    // Create conversation
    create: async (repositoryId, title = "New Conversation") => {

        return await apiRequest("/conversations/", {
            method: "POST",
            body: JSON.stringify({
                repository_id: repositoryId,
                title: title
            })
        });

    },

    // Get all conversations
    getAll: async () => {

        return await apiRequest("/conversations/", {
            method: "GET"
        });

    },

    // Get conversation details
    getById: async (conversationId) => {

        return await apiRequest(`/conversations/${conversationId}`, {
            method: "GET"
        });

    },

    // Delete conversation
    delete: async (conversationId) => {

        return await apiRequest(`/conversations/${conversationId}`, {
            method: "DELETE"
        });

    }

};


// =========================================
// CHAT API
// =========================================

const ChatAPI = {

    // Ask question about repository
    ask: async (repositoryId, question, conversationId) => {

        return await apiRequest(`/repositories/${repositoryId}/ask`, {
            method: "POST",
            body: JSON.stringify({
                question: question,
                conversation_id: conversationId
            })
        });

    }

};
