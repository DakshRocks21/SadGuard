import { API_URL } from "@/lib/utils"


export function getCookie(name: string) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(";").shift();
}

export function deleteCookie(name: string) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

export function setCookie(name: string, value: string, days: number) {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value}; expires=${date.toUTCString()}; path=/;`;
}

export async function getRepos() {
    // use access_token cookie

    const response = await fetch(`${API_URL}/repos`, {
        headers: {
            Authorization: `Bearer ${getCookie("access_token")}`,
        },
    });

    if (response.ok) {
        return response.json();
    } else {
        throw new Error("Failed to fetch repositories");
    }
}

export async function getCommits(repo: string, branch: string) {
    // use access_token cookie
    const response = await fetch(`${API_URL}/commits`, {
        headers: {
            Authorization: `Bearer ${getCookie("access_token")}`,
            "Content-Type": "application/json",
        },
        method: "POST",
        body: JSON.stringify({ repo, branch }),
    });

    if (response.ok) {
        return response.json();
    } else {
        throw new Error("Failed to fetch commits");
    }
}

export async function getPullRequests(repo: string) {
    // use access_token cookie

    const response = await fetch(`${API_URL}/pulls`, {
        headers: {
            Authorization: `Bearer ${getCookie("access_token")}`,
            "Content-Type": "application/json",
        },
        method: "POST",
        body: JSON.stringify({ repo }),
    });

    if (response.ok) {
        console.log(response.json());
        return response.json();
    } else {
        console.log(response);
        throw new Error("Failed to fetch pull requests");
    }
}

export async function getEvents(repo: string) {
    // use access_token cookie

    const response = await fetch(`${API_URL}/events`, {
        headers: {
            Authorization: `Bearer ${getCookie("access_token")}`,
            "Content-Type": "application/json",
        },
        method: "POST",
        body: JSON.stringify({ repo }),
    });

    if (response.ok) {
        return response.json();
    } else {
        throw new Error("Failed to fetch events");
    }
}

export async function getUser() {
    try {
        const response = await fetch(`${API_URL}/users/me`, {
            headers: {
                Authorization: `Bearer ${getCookie("access_token")}`,
            },
        });
        // Check if the response is ok (status code 2xx)
        if (!response.ok) {
            throw new Error("Failed to get user");
        }
        // Parse the JSON response if necessary
        const result = await response.json();
        return result;
    } catch (error) {
        console.error("Error getting user:", error);
        return [];
    }
}

export async function runScan(repo: string, sha: string) {
    const response = await fetch(`${API_URL}/scan`, {
        headers: {
            Authorization: `Bearer ${getCookie("access_token")}`,
            "Content-Type": "application/json",
        },
        method: "POST",
        body: JSON.stringify({ repo, sha }),
    });

    if (response.ok) {
        return response.json();
    } else {
        throw new Error("Failed to run scan");
    }
}

