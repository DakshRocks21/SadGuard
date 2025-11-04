import { createLazyFileRoute } from "@tanstack/react-router";
import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button";



export const Route = createLazyFileRoute("/")({
  component: Index,
});

function Index() {
  const handleLogin = () => {
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${import.meta.env.VITE_GITHUB_CLIENT_ID}`; // backend URL
  };

  return (
    <div className="h-screen flex items-center justify-center bg-gray-100">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <h1 className="text-xl font-bold text-center">Connect with GitHub</h1>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 text-center">
            Authorize with your GitHub account to get started.
          </p>
        </CardContent>
        <CardFooter>
          <Button
            onClick={handleLogin}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold"
          >
            Connect with GitHub
          </Button>
        </CardFooter>
      </Card>
    </div>
    
  );
}
