// Example snippet in your Navbar.tsx (frontend/components/Navbar.tsx)
import Link from 'next/link';
import React from 'react';

export default function Navbar() {
    return (
        <nav className="p-4 bg-gray-100 flex justify-between items-center">
            <Link href="/">
                <a className="text-xl font-bold">Sandbox Manager</a>
            </Link>
            <div className="space-x-4">
                <Link href="/dashboard">
                    <a>Dashboard</a>
                </Link>
                <Link href="/repos">
                    <a>Repositories</a>
                </Link>
                <Link href="/auth/signin">
                    <a>Sign In</a>
                </Link>
            </div>
        </nav>
    );
}
