// frontend/app/repos/page.tsx
"use client";
import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Repository {
    id: number;
    name: string;
    full_name: string;
    html_url: string;
    // add more fields if necessary
}

export default function ReposPage() {
    const [repos, setRepos] = useState<Repository[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get("http://localhost:5000/api/repos", {
            withCredentials: true,
        })
            .then(response => {
                setRepos(response.data);
            })
            .catch(err => {
                console.error("Error fetching repositories:", err);
                setError("Could not load repositories.");
            });
    }, []);

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Repositories with the Bot</h1>
            {error && <p className="text-red-600">{error}</p>}
            {repos.length === 0 ? (
                <p>No repositories found. Ensure your bot is installed on at least one repo.</p>
            ) : (
                <ul className="space-y-2">
                    {repos.map(repo => (
                        <li key={repo.full_name}>
                            <a
                                href={repo.html_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline"
                            >
                                {repo.full_name}
                            </a>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
