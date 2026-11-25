
document.addEventListener("DOMContentLoaded", () => {

    // Wake up the backend early while the user fills the form
    if (typeof warmupServer === "function") {
        warmupServer();
    }

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

            const slowHintTimer = setTimeout(() => {
                message.style.color = "#93c5fd";
                message.textContent =
                    "Waking up backend server... First request after inactivity can take 1–2 minutes.";
            }, 3500);

            try {

                // Send login credentials to FastAPI
                const response = await AuthAPI.login({
                    email,
                    password
                });

                clearTimeout(slowHintTimer);

                // Store the JWT token
                localStorage.setItem("access_token", response.access_token);

                // Verify the logged-in user
                // await AuthAPI.getCurrentUser();

                message.style.color = "#86efac";
                message.textContent = "Login successful! Redirecting...";

                // Open dashboard
                window.location.href = "dashboard.html";

            } catch (error) {

                clearTimeout(slowHintTimer);
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

            const slowHintTimer = setTimeout(() => {
                message.style.color = "#93c5fd";
                message.textContent =
                    "Waking up backend server... First request after inactivity can take 1–2 minutes.";
            }, 3500);

            try {

                // Send signup details to FastAPI
                await AuthAPI.signup({
                    username,
                    email,
                    password
                });

                clearTimeout(slowHintTimer);

                message.style.color = "#86efac";
                message.textContent = "Account created successfully! Redirecting to login...";

                signupForm.reset();

                // Redirect to login page
                setTimeout(() => {
                    window.location.href = "login.html";
                }, 1500);

            } catch (error) {

                clearTimeout(slowHintTimer);

                message.style.color = "#fca5a5";
                message.textContent = error.message;

                submitButton.disabled = false;
                submitButton.innerHTML = 'Create Account <span>→</span>';

            }

        });

    }


    /* =====================================
       FORGOT / RESET PASSWORD FUNCTIONALITY
    ===================================== */

    const forgotPasswordSection = document.getElementById("forgotPasswordSection");
    const resetPasswordSection = document.getElementById("resetPasswordSection");
    const forgotPasswordForm = document.getElementById("forgotPasswordForm");
    const resetPasswordForm = document.getElementById("resetPasswordForm");

    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get("token");

    if (resetToken && forgotPasswordSection && resetPasswordSection) {
        forgotPasswordSection.style.display = "none";
        resetPasswordSection.style.display = "block";
    }

    if (forgotPasswordForm) {

        forgotPasswordForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            const email = document.getElementById("resetEmail").value.trim();
            const message = document.getElementById("forgotMessage");
            const submitButton = forgotPasswordForm.querySelector('button[type="submit"]');

            message.textContent = "";
            submitButton.disabled = true;
            submitButton.textContent = "Sending...";

            try {

                const response = await AuthAPI.forgotPassword({ email });

                message.style.color = "#86efac";
                message.textContent = response.message;
                forgotPasswordForm.reset();

            } catch (error) {

                message.style.color = "#fca5a5";
                message.textContent = error.message;

            } finally {

                submitButton.disabled = false;
                submitButton.innerHTML = 'Send Reset Link <span>→</span>';

            }

        });

    }

    if (resetPasswordForm) {

        resetPasswordForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            const newPassword = document.getElementById("newResetPassword").value;
            const confirmPassword = document.getElementById("confirmNewResetPassword").value;
            const message = document.getElementById("resetMessage");
            const submitButton = resetPasswordForm.querySelector('button[type="submit"]');

            message.textContent = "";

            if (!resetToken) {
                message.style.color = "#fca5a5";
                message.textContent = "Missing reset token. Please request a new reset link.";
                return;
            }

            if (newPassword !== confirmPassword) {
                message.style.color = "#fca5a5";
                message.textContent = "Passwords do not match.";
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent = "Resetting...";

            try {

                const response = await AuthAPI.resetPassword({
                    token: resetToken,
                    new_password: newPassword
                });

                message.style.color = "#86efac";
                message.textContent = `${response.message} Redirecting to login...`;
                resetPasswordForm.reset();

                setTimeout(() => {
                    window.location.href = "login.html";
                }, 1500);

            } catch (error) {

                message.style.color = "#fca5a5";
                message.textContent = error.message;
                submitButton.disabled = false;
                submitButton.innerHTML = 'Reset Password <span>→</span>';

            }

        });

    }

});
