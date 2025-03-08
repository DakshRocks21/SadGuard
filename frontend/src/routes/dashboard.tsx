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
import { ModeToggle } from "@/components/mode-toggle";
import { getCommits, getRepos, getUser, runScan, getPullRequests, getEvents } from "@/lib/api";

export const Route = createFileRoute("/dashboard")({
  component: RouteComponent,
});

function RouteComponent() {
  const [user, setUser] = useState({});
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [selectedBranch, setSelectedBranch] = useState("");
  const [commits, setCommits] = useState([]);
  const [scans, setScans] = useState({});
  const [pullRequests, setPullRequests] = useState([]);
  const [commitsLoading, setCommitsLoading] = useState(false);
  const [prsLoading, setPrsLoading] = useState(false);

  // New state for PR events
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  useEffect(() => {
    async function fetchUser() {
      const data = await getUser();
      setUser(data);
    }
    fetchUser();

    async function fetchRepos() {
      const data = await getRepos();
      console.log(data);
      setRepos(data);
    }
    fetchRepos();

    async function getLoader() {
      const { bouncy } = await import("ldrs");
      bouncy.register();
    }
    getLoader();

  }, []);

  // Fetch events from FastAPI backend
  async function fetchEvents(repo) {
    setEventsLoading(true);
    try {
      const data = await getEvents(repo);

      setEvents(data);
    } catch (error) {
      console.error("Error fetching events:", error);
    }
    setEventsLoading(false);
  }

  async function retrieveCommits(repo, branch) {
    setCommitsLoading(true);
    try {
      const data = await getCommits(repo, branch);
      setCommits(data.commits);
      setScans(data.scans);
    } catch (error) {
      console.error("Error fetching commits:", error);
    }
    setCommitsLoading(false);
  }

  async function loadPullRequests(repo) {
    setPrsLoading(true);
    try {
      const data = await getPullRequests(repo);
      setPullRequests(data);
    } catch (error) {
      console.error("Error fetching pull requests:", error);
    }
    setPrsLoading(false);
  }

  async function handleRunScanPR(pr) {
    try {
      await runScan(selectedRepo, pr.id);
      // Refresh pull requests after scanning
      loadPullRequests(selectedRepo);
    } catch (error) {
      console.error("Error running scan for PR:", error);
    }
  }

  // Filter events by selected repo if one is chosen
  const filteredEvents = selectedRepo
    ? events.filter((event) => event.repo_name === selectedRepo)
    : events;

  return (
    <div className="flex">
      {/* Sidebar: Repository and Branch Selection */}
      <div className="py-7 px-4 flex flex-col justify-between dark:bg-neutral-950 max-h-screen h-screen w-64">
        <div className="flex flex-col gap-4">
          {user.username && (
            <div className="flex gap-4 items-center">
              <img
                src={user.avatar_url}
                alt="User Avatar"
                className="object-cover w-10 h-10 rounded-full"
              />
              <h1 className="dark:text-white">{user.username}</h1>
              <ModeToggle />
            </div>
          )}
          <div>
            <h1 className="text-stone-400">Repositories</h1>
            <Accordion type="single" collapsible className="max-h-[calc(80vh-8rem)] overflow-y-auto">
              {repos.map((repo) => (
                <AccordionItem value={repo.name} key={repo.name}>
                  <AccordionTrigger className="dark:text-white">
                    {repo.name}
                  </AccordionTrigger>
                  <AccordionContent className="max-h-96 overflow-y-auto">
                    <div className="flex flex-col gap-1">
                      {repo.branches.map((branch) => (
                        <Button
                          key={branch.name}
                          className="w-full px-2 text-left overflow-ellipsis whitespace-nowrap bg-slate-200 dark:bg-zinc-800 text-black dark:text-white hover:text-white hover:bg-slate-500 dark:hover:bg-zinc-900"
                          onClick={() => {
                            setSelectedRepo(repo.name);
                            setSelectedBranch(branch.name);
                            retrieveCommits(repo.name, branch.name);
                            loadPullRequests(repo.name);
                            fetchEvents(repo.name);
                          }}
                        >
                          {branch.name}
                        </Button>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
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

      {/* Main Content Area: Events, PRs & Commits */}
      <div className="bg-slate-100 dark:bg-zinc-950 flex-grow h-screen p-4 overflow-y-auto">
        {/* New: PR Events Section */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold dark:text-white mb-2">
            Pull Request Events {selectedRepo && `for ${selectedRepo}`}
          </h2>
          {eventsLoading ? (
            <div className="flex justify-center items-center h-32">
              <l-bouncy size="30" speed="1.75" color="#595cff" />
            </div>
          ) : (
            <Table className="w-full border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
              <TableCaption className="text-lg font-semibold text-gray-600 dark:text-gray-300">
                PR Events
              </TableCaption>
              <TableHeader className="bg-gray-200 dark:bg-gray-800">
                <TableRow>
                  <TableHead className="p-4 font-semibold">Repo</TableHead>
                  <TableHead className="p-4 font-semibold">Event</TableHead>
                  <TableHead className="p-4 font-semibold">PR Number</TableHead>
                  <TableHead className="p-4 font-semibold">Extra</TableHead>
                  <TableHead className="p-4 font-semibold">Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="dark:text-white">
                {filteredEvents.map((event) => (
                  <TableRow key={event.id} className="hover:bg-gray-100 dark:hover:bg-gray-700 transition duration-200">
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">{event.repo_name}</TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">{event.event}</TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">{event.pr_number}</TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      <pre className="whitespace-pre-wrap text-xs">
                        {JSON.stringify(event.extra, null, 2)}
                      </pre>
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {new Date(event.timestamp).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {/* Pull Requests Table */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold dark:text-white mb-2">
            Pull Requests {selectedRepo && `for ${selectedRepo}`}
          </h2>
          {prsLoading ? (
            <div className="flex justify-center items-center h-32">
              <l-bouncy size="30" speed="1.75" color="#595cff" />
            </div>
          ) : (
            <Table className="w-full border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
              <TableCaption className="text-lg font-semibold text-gray-600 dark:text-gray-300">
                PRs for {selectedRepo || "selected repository"}
              </TableCaption>
              <TableHeader className="bg-gray-200 dark:bg-gray-800">
                <TableRow>
                  <TableHead className="p-4 font-semibold">Title</TableHead>
                  <TableHead className="p-4 font-semibold">Author</TableHead>
                  <TableHead className="p-4 font-semibold">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="dark:text-white">
                {pullRequests.map((pr) => (
                  <TableRow key={pr.id} className="hover:bg-gray-100 dark:hover:bg-gray-700 transition duration-200">
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {pr.title}
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {pr.user.login}
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      <Button variant="secondary" onClick={() => handleRunScanPR(pr)}>
                        Run Scan
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {/* Commits Table */}
        <div>
          <h2 className="text-xl font-semibold dark:text-white mb-2">
            {selectedBranch ? `Commits for ${selectedBranch}` : "Commits"}
          </h2>
          {commitsLoading ? (
            <div className="flex justify-center items-center h-32">
              <l-bouncy size="30" speed="1.75" color="#595cff" />
            </div>
          ) : (
            <Table className="w-full border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
              <TableCaption className="text-lg font-semibold text-gray-600 dark:text-gray-300">
                Commit History for {selectedRepo} - {selectedBranch}
              </TableCaption>
              <TableHeader className="bg-gray-200 dark:bg-gray-800">
                <TableRow>
                  <TableHead className="w-[200px] p-4 font-semibold">
                    Commit Message
                  </TableHead>
                  <TableHead className="p-4 font-semibold">Author</TableHead>
                  <TableHead className="p-4 font-semibold">Date</TableHead>
                  <TableHead className="p-4 font-semibold">Suspicious Files</TableHead>
                  <TableHead className="p-4 font-semibold">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="dark:text-white">
                {commits.map((commit) => (
                  <TableRow key={commit.sha} className="hover:bg-gray-100 dark:hover:bg-gray-700 transition duration-200">
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {commit.commit.message}
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {commit.commit.author.name}
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {commit.commit.author.date}
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
                      {scans[commit.sha]
                        ? Object.keys(scans[commit.sha]).length
                        : "Not scanned"}
                    </TableCell>
                    <TableCell className="p-4 border-b border-gray-200 dark:border-gray-700">
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
                                  <TableHeader className="bg-gray-200 dark:bg-gray-800">
                                    <TableRow>
                                      <TableHead className="p-2 font-semibold">File</TableHead>
                                      <TableHead className="p-2 font-semibold">Reason</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {scans[commit.sha].map((file, index) => (
                                      <TableRow key={index} className="border-b border-gray-200 dark:border-gray-700">
                                        <TableCell className="p-2">
                                          {Object.keys(file)[0]}
                                        </TableCell>
                                        <TableCell className="p-2">
                                          {file[Object.keys(file)[0]]}
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </DialogDescription>
                            </DialogHeader>
                          </DialogContent>
                        </Dialog>
                      ) : (
                        <Button variant="secondary" onClick={() => runScan(selectedRepo, commit.sha)}>
                          Scan
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  );
}

export default RouteComponent;
