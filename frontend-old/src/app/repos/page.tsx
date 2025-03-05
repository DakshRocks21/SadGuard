// frontend/app/repos/page.tsx
"use client";
import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface Repository {
    full_name: string;
    html_url: string;
    sandbox_output?: string;
    llm_review_output?: string;
}

export default function ReposPage() {
    const [repos, setRepos] = useState<Repository[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        axios.get("http://localhost:5000/api/repos", { withCredentials: true })
            .then(response => {
                setRepos(response.data);
            })
            .catch(err => {
                console.error("Error fetching repositories:", err);
                setError("Could not load repositories.");
            });
    }, []);

    const triggerAnalysis = async (repoName: string, prNumber: number) => {
        try {
            const res = await axios.post("http://localhost:5000/api/trigger-analysis", {
                repo_name: repoName,
                pr_number: prNumber,
            }, { withCredentials: true });
            alert("Analysis triggered:\n" + res.data.analysis_result);
        } catch (err) {
            console.error("Error triggering analysis:", err);
            alert("Error triggering analysis");
        }
    };

    const fetchSandboxOutput = async (repoName: string, prNumber: number) => {
        try {
            const res = await axios.get("http://localhost:5000/api/sandbox-output", {
                params: { repo_name: repoName, pr_number: prNumber },
                withCredentials: true,
            });
            alert("Sandbox Output:\n" + JSON.stringify(res.data, null, 2));
        } catch (err) {
            console.error("Error fetching sandbox output:", err);
            alert("Error fetching sandbox output");
        }
    };

    const fetchLLMReviewOutput = async (repoName: string, prNumber: number) => {
        try {
            const res = await axios.get("http://localhost:5000/api/llm-review-output", {
                params: { repo_name: repoName, pr_number: prNumber },
                withCredentials: true,
            });
            alert("LLM Review Output:\n" + JSON.stringify(res.data, null, 2));
        } catch (err) {
            console.error("Error fetching LLM review output:", err);
            alert("Error fetching LLM review output");
        }
    };

    return (
        <div className="mx-auto p-4">
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
                            <div className="flex flex-wrap gap-2 mt-1">
                                <button onClick={() => triggerAnalysis(repo.full_name, 8)} className="bg-blue-500 text-white px-2 py-1 rounded">
                                    Re-run Analysis
                                </button>
                                <button onClick={() => fetchSandboxOutput(repo.full_name, 8)} className="bg-green-500 text-white px-2 py-1 rounded">
                                    View Sandbox Output
                                </button>
                                <button onClick={() => fetchLLMReviewOutput(repo.full_name, 8)} className="bg-purple-500 text-white px-2 py-1 rounded">
                                    View LLM Review
                                </button>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
