
/* =========================================
   API CONFIGURATION
========================================= */

// FastAPI production server
const API_BASE_URL = "https://codebase-qa-assistant-r80e.onrender.com/api/v1";


/* =========================================
   API REQUEST HANDLER
========================================= */

async function apiRequest(endpoint, options = {}) {

    const token = localStorage.getItem("access_token");

    const headers = {
        ...options.headers
    };

    // Add JSON content type when sending a request body
    if (options.body && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    // Attach authentication token when available
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {

        const response = await fetch(
            `${API_BASE_URL}${endpoint}`,
            {
                ...options,
                headers
            }
        );

        // Handle responses without a body
        if (response.status === 204) {
            return null;
        }

        const data = await response.json().catch(() => null);

        if (!response.ok) {

            const errorMessage =
                data?.detail || "Something went wrong. Please try again.";

            throw new Error(errorMessage);
        }

        return data;

    } catch (error) {

        if (error instanceof TypeError) {
            throw new Error(
                "Unable to connect to the server. Please check whether the backend is running."
            );
        }

        throw error;
    }
}


/* =========================================
   AUTHENTICATION APIs
========================================= */

const AuthAPI = {

    signup: async (userData) => {

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

    }

};


/* =========================================
   REPOSITORY APIs
========================================= */

const RepositoryAPI = {

    getAll: async () => {

        return await apiRequest("/repositories/", {
            method: "GET"
        });

    },

    getById: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}`, {
            method: "GET"
        });

    },

    create: async (repositoryData) => {

        return await apiRequest("/repositories/", {
            method: "POST",
            body: JSON.stringify(repositoryData)
        });

    },

    delete: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}`, {
            method: "DELETE"
        });

    },

    clone: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/clone`, {
            method: "POST"
        });

    },

    index: async (repositoryId) => {

        return await apiRequest(`/repositories/${repositoryId}/index`, {
            method: "POST"
        });

    },

    ask: async (repositoryId, question) => {

        return await apiRequest(`/repositories/${repositoryId}/ask`, {
            method: "POST",
            body: JSON.stringify({ question })
        });

    }

};



/* =========================================
   CONVERSATION APIs
========================================= */

const ConversationAPI = {

    // Create a new conversation
    create: async (repositoryId, title = "New Conversation") => {

        return await apiRequest("/conversations/", {
            method: "POST",
            body: JSON.stringify({
                repository_id: repositoryId,
                title: title
            })
        });

    },

    // Get all conversations belonging to the logged-in user
    getAll: async () => {

        return await apiRequest("/conversations/", {
            method: "GET"
        });

    },

    // Get one conversation with its saved messages
    getById: async (conversationId) => {

        return await apiRequest(`/conversations/${conversationId}`, {
            method: "GET"
        });

    }

};
