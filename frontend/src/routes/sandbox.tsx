import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import Markdown from "react-markdown";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { API_URL } from "@/lib/utils";

export const Route = createFileRoute("/sandbox")({
  component: RouteComponent,
});

function RouteComponent() {
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setLoading(true);
    const formData = new FormData();
    const file = (document.querySelector('input[type="file"]') as any).files[0];
    const script = document.querySelector('textarea[name="script"]') as any;
    const data = new FormData();
    data.append("script", script.value);
    data.append("file", file);
    const response = await fetch(`${API_URL}/sandbox`, {
      method: "POST",
      body: data,
    });

    const res = await response.json();
    setOutput(res.output);
    setLoading(false);
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Sandbox</h1>
      <p>
        Upload and run compiled binaries to benchmark them to diff with previous
        versions
      </p>
      <form className="flex flex-col gap-4 mt-4">
        {/* submit files and textarea for command script to run*/}
        <Input type="file" name="file" />
        <Textarea
          name="script"
          placeholder="#!/bin/sh
./testbin"
          className="h-64"
        />
        {/* <Button type="button" variant="secondary" onClick={onSubmit}>
          Run
        </Button> */}
        <Dialog>
          <DialogTrigger asChild>
            <Button type="button" variant="secondary" onClick={onSubmit}>
              Run
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="dark:text-white">
                Sandbox Output
              </DialogTitle>
              <DialogDescription>
                {loading ? (
                  "Loading..."
                ) : (
                  // <p dangerouslySetInnerHTML={{ __html: output }}></p>
                  <p>{output}</p>
                )}
              </DialogDescription>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      </form>
    </div>
  );
}
