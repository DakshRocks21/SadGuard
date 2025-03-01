"use client";
import React from 'react';

export default function SignIn() {
    const handleLogin = () => {
        window.location.href = "http://localhost:5000/auth/github/login";
    };

    return (
        <div className="flex flex-col items-center justify-center h-screen">
            <h1 className="text-3xl mb-6">Sign in to manage your sandboxes</h1>
            <button
                onClick={handleLogin}
                className="bg-blue-600 text-white px-6 py-3 rounded shadow hover:bg-blue-700"
            >
                Sign in with GitHub
            </button>
        </div>
    );
}
