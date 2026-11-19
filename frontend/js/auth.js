
document.addEventListener("DOMContentLoaded", () => {

    /* =====================================
       LOGIN FUNCTIONALITY
    ===================================== */

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {

        loginForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;
            const message = document.getElementById("loginMessage");
            const submitButton = loginForm.querySelector('button[type="submit"]');

            message.textContent = "";
            submitButton.disabled = true;
            submitButton.textContent = "Logging in...";

            try {

                // Send login credentials to FastAPI
                const response = await AuthAPI.login({
                    email,
                    password
                });

                // Store the JWT token
                localStorage.setItem("access_token", response.access_token);

                // Verify the logged-in user
                // await AuthAPI.getCurrentUser();

                message.style.color = "#86efac";
                message.textContent = "Login successful! Redirecting...";

                // Open dashboard
                window.location.href = "dashboard.html";

            } catch (error) {

                localStorage.removeItem("access_token");

                message.style.color = "#fca5a5";
                message.textContent = error.message;

                submitButton.disabled = false;
                submitButton.innerHTML = 'Log in <span>→</span>';

            }

        });

    }


    /* =====================================
       SIGNUP FUNCTIONALITY
    ===================================== */

    const signupForm = document.getElementById("signupForm");

    if (signupForm) {

        signupForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            const username = document.getElementById("username").value.trim();
            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;
            const confirmPassword = document.getElementById("confirmPassword").value;

            const message = document.getElementById("signupMessage");
            const submitButton = signupForm.querySelector('button[type="submit"]');

            message.textContent = "";

            // Check password confirmation
            if (password !== confirmPassword) {

                message.style.color = "#fca5a5";
                message.textContent = "Passwords do not match.";

                return;
            }

            submitButton.disabled = true;
            submitButton.textContent = "Creating account...";

            try {

                // Send signup details to FastAPI
                await AuthAPI.signup({
                    username,
                    email,
                    password
                });

                message.style.color = "#86efac";
                message.textContent = "Account created successfully! Redirecting to login...";

                signupForm.reset();

                // Redirect to login page
                setTimeout(() => {
                    window.location.href = "login.html";
                }, 1500);

            } catch (error) {

                message.style.color = "#fca5a5";
                message.textContent = error.message;

                submitButton.disabled = false;
                submitButton.innerHTML = 'Create Account <span>→</span>';

            }

        });

    }

});
