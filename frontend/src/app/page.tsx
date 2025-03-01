import Link from 'next/link';
import React from 'react';

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
      <h1 className="text-4xl font-bold mb-4">
        Welcome to Sandbox Manager
      </h1>
      <p className="mb-8 text-lg text-gray-700">
        Manage your development sandboxes and track your GitHub pull requests with ease.
      </p>
      <Link
        href="/auth/signin"
        className="px-6 py-3 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition duration-200">
        
          Get Started
        
      </Link>
    </main>
  );
}
