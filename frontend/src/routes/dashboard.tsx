import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
// import Image from "next/image";
// import { API_URL } from "@/lib/utils";
import { getCommits, getRepos, getUser, runScan, getPullRequests } from "@/lib/api";
import { ModeToggle } from "@/components/mode-toggle";

export const Route = createFileRoute("/dashboard")({
  component: RouteComponent,
});

function RouteComponent() {
  const [user, setUser] = useState({});
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [selectedBranch, setSelectedBranch] = useState("");
  const [commits, setCommits] = useState([]);
  const [scans, setScans] = useState([]);
  const [pullRequests, setPullRequests] = useState([]);
  const [tableLoading, setTableLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      const data = await getUser();
      setUser(data);
    }
    fetchUser();
    async function fetchRepo() {
      const data = await getRepos();
      setRepos(data);
    }
    fetchRepo();
    async function getLoader() {
      const { bouncy } = await import("ldrs");
      bouncy.register();
    }
    getLoader();
  }, []);

  async function retrieveCommits(repo, branch) {
    setTableLoading(true);
    async function fetchCommits() {
      const data = await getCommits(repo, branch);
      setCommits(data.commits);
      setScans(data.scans);
      setTableLoading(false);
    }
    fetchCommits();
  }

  async function retrievePullRequests(repo) {

    try {
      const data = await getPullRequests(repo);
      console.log(data);
      setPullRequests(data);
    } catch (error) {
      console.error("Error fetching pull requests:", error);
    }
  }

  return (
    <div className="flex">
      {/* nav bar */}
      <div className="py-7 px-4 flex flex-col justify-between dark:bg-neutral-950 max-h-screen h-screen w-64">
        <div className="flex flex-col gap-4 text-wrap">
          {user.username ? (
            <div className="flex gap-4 items-center">
              <img
                src={`${user.avatar_url}`}
                alt="User Avatar"
                className="object-cover w-10 h-10 rounded-full"
              />
              <h1 className="text-wrap dark:text-white">{user.username}</h1>
              <ModeToggle />
            </div>
          ) : null}
          <div>
            <h1 className="text-stone-400">Repositories</h1>

            <Accordion
              type="single"
              collapsible
              className="max-h-[calc(80vh-8rem)] overflow-y-auto"
            >
              {repos.map((repo) => {
                return (
                  <AccordionItem value={repo.name} key={repo.name}>
                    <AccordionTrigger className="dark:text-white">
                      {repo.name}
                    </AccordionTrigger>
                    <AccordionContent className="max-h-96 overflow-y-auto overflow-x-hidden">
                      <div className="flex flex-col gap-1">
                        {repo.branches.map((branch) => {
                          return (
                            <Button
                              key={branch.name}
                              className="w-full px-2 text-left overflow-ellipsis whitespace-nowrap bg-slate-200 dark:bg-zinc-800 text-black dark:text-white hover:text-white hover:bg-slate-500 dark:hover:bg-zinc-900"
                              onClick={() => {
                                setSelectedRepo(repo.name);
                                setSelectedBranch(branch.name);
                                retrieveCommits(repo.name, branch.name);
                                retrievePullRequests(repo.name);
                              }}
                            >
                              {branch.name}
                            </Button>
                          );
                        })}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                );
              })}
            </Accordion>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <p className="dark:text-white">Selected Repo: {selectedRepo}</p>
          <p className="dark:text-white">Selected Branch: {selectedBranch}</p>
          <Button asChild variant="destructive">
            <Link href="/">Logout</Link>
          </Button>
        </div>
      </div>
      {/* body content */}
      <div className="bg-slate-100 dark:bg-zinc-950 max-w-screen h-screen flex-grow p-4">
        {tableLoading ? (
          <div className="flex justify-center items-center h-full w-full">
            <l-bouncy size="30" speed="1.75" color="#595cff"></l-bouncy>
          </div>
        ) : (
          <Table className="w-full h-96 border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
            <TableCaption className="text-lg font-semibold text-gray-600 dark:text-gray-300">Pull Requests</TableCaption>
            <TableHeader className="bg-gray-200 dark:bg-gray-800">
              <TableRow className="w-full">
                <TableHead className="text-left p-4 font-semibold">Title</TableHead>
                <TableHead className="text-left p-4 font-semibold">Author</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="dark:text-white">
              {pullRequests.map((pr) => (
                <TableRow key={pr.id}>
                  <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">{pr.title}</TableCell>
                  <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">{pr.user.login}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}