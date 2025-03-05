// frontend/app/dashboard/page.tsx
"use client";
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import SandboxCard from '@/components/SandboxCard';

interface Sandbox {
    id: number;
    name: string;
    status: string;
}

export default function Dashboard() {
    const [sandboxes, setSandboxes] = useState<Sandbox[]>([]);

    useEffect(() => {
        axios.get("http://localhost:5000/api/sandboxes")
            .then(response => {
                setSandboxes(response.data);
            })
            .catch(error => {
                console.error("Error fetching sandboxes:", error);
            });
    }, []);

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Sandbox Dashboard</h1>
            <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                {sandboxes.map(sandbox => (
                    <SandboxCard key={sandbox.id} sandbox={sandbox} />
                ))}
            </div>
        </div>
    );
}
