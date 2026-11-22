
// =========================================
// API BASE URL
// =========================================

// Production FastAPI server
const API_BASE_URL = "https://codebase-qa-assistant-r80e.onrender.com/api/v1";

// Local FastAPI server
// const API_BASE_URL = "http://127.0.0.1:8000/api/v1";


// =========================================
// COMMON API REQUEST HANDLER
// =========================================

async function apiRequest(endpoint, options = {}) {

    const token = localStorage.getItem("access_token");

    const headers = {
        "Content-Type": "application/json",
        ...options.headers
    };

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    try {

        const response = await fetch(
            `${API_BASE_URL}${endpoint}`,
            {
                ...options,
                headers
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

        if (error instanceof TypeError) {
            throw new Error(
                "Unable to connect to the server. Please check your internet connection."
            );
        }

        throw error;
    }
}


// =========================================
// AUTHENTICATION API
// =========================================

const AuthAPI = {

    register: async (userData) => {

        return await apiRequest("/auth/register", {
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
    index: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/index`, {
            method: "POST"
        });

    },

    // Re-index existing repository
    reindex: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/reindex`, {
            method: "POST"
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
