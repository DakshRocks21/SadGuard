import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React, { useEffect } from "react";
import { API_URL } from "@/lib/utils";

export const Route = createFileRoute('/github/callback')({
  component: RouteComponent,
})

function RouteComponent() {
  const navigate = useNavigate();

  useEffect(() => {
    // Extract "code" parameter from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");

    if (code) {
      // Send POST request to the backend with the "code"
      fetch(`${API_URL}/auth/github`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code }),
      })
        .then((response) => {
          if (response.ok) {
            return response.json();
          } else {
            throw new Error("Authentication failed");
          }
        })
        .then((data) => {
          // Save token or user data if required
          if (data.access_token) {
            document.cookie = `access_token=${data.access_token}; path=/;`;
            // localStorage.setItem("token", data.token);
          
            // Redirect to the dashboard page
            navigate({to: "/dashboard"});
          } else {
            throw new Error("No token received");
          }
        })
        .catch((error) => {
          console.error("Authentication error:", error);
          // Show an error message and redirect to the index page
          alert("Authentication failed. Redirecting to the home page.");
          navigate({to :"/"});
        });
    } else {
      // If no code parameter, redirect to the index page
      alert("No code found in the URL. Redirecting to the home page.");
      navigate({to: "/"});
    }
  }, []);

  return <div className="h-screen flex items-center justify-center bg-gray-100">
    <div className="text-center">
      <h1 className="text-2xl font-bold">Authenticating...</h1>
      <p className="text-gray-600 mt-2">Please wait while we log you in.</p>
    </div>
  </div>
}

// redirecting page to main dashboard
// get parameter in url "code" and send POST to backend 
// "/auth/github" code in json body
// successfull = redirect to main dashboard
// fail = login + error message