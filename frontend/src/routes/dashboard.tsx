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
import { getCommits, getRepos, getUser, runScan } from "@/lib/api";
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
            <h1 className="text-stone-400">Sandbox</h1>
            <Button asChild variant="primary">
              <Link href="/sandbox">Go to Sandbox</Link>
            </Button>

            <h1 className="text-stone-400">Repositories</h1>

            <Accordion
              type="single"
              collapsible
              className="max-h-[calc(100vh-8rem)] overflow-y-auto"
            >
              {repos.map((repo) => {
                return (
                  <AccordionItem value={repo.name}>
                    <AccordionTrigger className="dark:text-white">
                      {repo.name}
                    </AccordionTrigger>
                    <AccordionContent className="max-h-96 overflow-y-auto overflow-x-hidden">
                      <div className="flex flex-col gap-1">
                        {repo.branches.map((branch) => {
                          return (
                            <Button
                              className="w-full px-2 text-left overflow-ellipsis whitespace-nowrap bg-slate-200 dark:bg-zinc-800 text-black dark:text-white hover:text-white hover:bg-slate-500 dark:hover:bg-zinc-900"
                              onClick={() => {
                                setSelectedRepo(repo.name);
                                setSelectedBranch(branch.name);
                                retrieveCommits(repo.name, branch.name);
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
          <Table className="w-full h-96">
            <TableCaption>Commits</TableCaption>
            <TableHeader>
              <TableRow className="w-full">
                <TableHead className="w-[100px]">Commit</TableHead>
                <TableHead>Author</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Suspicious Files</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="dark:text-white">
              {commits.map((commit) => {
                return (
                  <TableRow key={commit.sha}>
                    <TableCell>{commit.commit.message}</TableCell>
                    <TableCell>{commit.commit.author.name}</TableCell>
                    <TableCell>{commit.commit.author.date}</TableCell>
                    <TableCell>
                      {scans[commit.sha]
                        ? Object.keys(scans[commit.sha]).length
                        : "Run scan...."}
                    </TableCell>
                    <TableCell>
                      {scans[commit.sha] ? (
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="secondary">View</Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>
                                Suspicious Files in Commit {commit.sha}
                              </DialogTitle>
                              <DialogDescription>
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      <TableHead>File</TableHead>
                                      <TableHead>Reason</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {scans[commit.sha].map((file) => {
                                      return (
                                        <TableRow>
                                          <TableCell>
                                            {Object.keys(file)[0]}
                                          </TableCell>
                                          <TableCell>
                                            {file[Object.keys(file)[0]]}
                                          </TableCell>
                                        </TableRow>
                                      );
                                    })}
                                  </TableBody>
                                </Table>
                              </DialogDescription>
                            </DialogHeader>
                          </DialogContent>
                        </Dialog>
                      ) : (
                        <Button
                          variant="secondary"
                          onClick={() => runScan(selectedRepo, commit.sha)}
                        >
                          Scan
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
