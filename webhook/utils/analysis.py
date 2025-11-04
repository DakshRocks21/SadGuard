import re
import textwrap
from typing import List, Optional, Tuple


def extract_section(logs: str, section_title: str) -> str:
    """Extracts the content after a markdown header with the given title.

    Example input (markdown-style):

    ## Mitmproxy Log (HTTP/HTTPS flows)
    <content to extract>
    ## Tcpdump Log (All network traffic)

    Returns the section text (trimmed) or an empty string if not found.
    """
    pattern = re.compile(rf"## {re.escape(section_title)}\s*\n(.*?)(?=\n## |\Z)", re.DOTALL)
    match = pattern.search(logs)
    if match:
        return match.group(1).strip()
    return ""


### Reviewer-friendly helpers


def _first_nonempty_lines(text: str, max_lines: int) -> List[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[:max_lines]


def extract_key_findings(logs: str, max_items: int = 5) -> List[str]:
    """Return up to `max_items` log lines that look important (errors, warnings, tracebacks).

    This uses simple heuristics to produce terse, unique findings a human reviewer can act on.
    """
    if not logs:
        return []

    keywords = [r"\bERROR\b", r"\bException\b", r"Traceback", r"\bfailed\b", r"permission denied", r"segfault", r"panic", r"timeout", r"connection refused", r"CRITICAL", r"WARNING"]
    findings = []
    for line in logs.splitlines():
        low = line.lower()
        if any(re.search(k, line, re.IGNORECASE) for k in keywords):
            snippet = line.strip()
            if snippet and snippet not in findings:
                findings.append(snippet)
                if len(findings) >= max_items:
                    break

    # If no keyword lines found, fallback to first non-empty lines (short view)
    if not findings:
        findings = _first_nonempty_lines(logs, max_items)

    return findings


def infer_severity(logs: str) -> str:
    """Heuristically infer severity: High / Medium / Low.

    High: errors, tracebacks, segfaults, panics
    Medium: warnings, timeouts
    Low: otherwise
    """
    if not logs:
        return "Low"

    high_kw = [r"\bERROR\b", r"Traceback", r"segfault", r"panic", r"CRITICAL", r"unhandled exception"]
    medium_kw = [r"\bWARNING\b", r"timeout", r"connection refused", r"rate limit"]

    for k in high_kw:
        if re.search(k, logs, re.IGNORECASE):
            return "High"
    for k in medium_kw:
        if re.search(k, logs, re.IGNORECASE):
            return "Medium"
    return "Low"


def suggest_actions_from_findings(findings: List[str]) -> List[str]:
    """Return short actionable suggestions derived from findings.

    This maps common problem tokens to practical next steps a reviewer can follow.
    """
    suggestions = []
    for f in findings:
        lf = f.lower()
        if "permission denied" in lf or "permissionerror" in lf:
            suggestions.append("Check file and directory permissions and the user the container runs as.")
        elif "timeout" in lf:
            suggestions.append("Increase relevant timeouts or investigate network connectivity to external services.")
        elif "connection refused" in lf or "failed to connect" in lf:
            suggestions.append("Verify service endpoints and network access from inside the container.")
        elif "traceback" in lf or "exception" in lf:
            suggestions.append("Inspect the stack trace and attach the smallest failing repro if possible.")
        elif "segfault" in lf or "panic" in lf:
            suggestions.append("Consider running under a debugger or adding logging; check native deps and memory usage.")
        elif "warning" in lf:
            suggestions.append("Review the warning and determine if it can safely be ignored or needs fixing.")
        elif "error" in lf or "failed" in lf:
            suggestions.append("Re-run the failing step locally with verbose logging and capture full output for triage.")

    # Deduplicate while preserving order and keep at most 5 suggestions
    seen = set()
    deduped = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
        if len(deduped) >= 5:
            break

    # If no suggestions could be inferred, give a generic next step
    if not deduped:
        deduped.append("If unclear, re-run the failing command with increased logging and attach the output.")

    return deduped


def make_review_comment(title: str, findings_text: str, full_logs: Optional[str] = None, max_summary_lines: int = 3) -> str:
    """Build a markdown comment string tailored for reviewers.

    The output includes:
    - A concise 3-4 line summary at the top (designed to be read in the PR conversation)
    - Severity indicator
    - Top findings as short bullets (unique, value-adding)
    - Actionable suggestions
    - A collapsible debug/details block that shows `full_logs` (or `findings_text` if full_logs is None)

    Use this helper before posting to GitHub so the reviewer sees a compact summary with the ability
    to expand and inspect raw debug output.
    """
    # Prepare short summary lines using heuristics
    summary_lines = _first_nonempty_lines(findings_text or full_logs or "", max_summary_lines)
    if not summary_lines:
        # Fallback to taking first sentences
        text_src = findings_text or full_logs or "No findings"
        sentences = re.split(r"(?<=[.!?])\s+", text_src.strip())
        summary_lines = [s.strip() for s in sentences if s][:max_summary_lines]

    severity = infer_severity(findings_text or full_logs or "")
    findings = extract_key_findings(findings_text or full_logs or "", max_items=5)
    suggestions = suggest_actions_from_findings(findings)

    # Build markdown
    md_parts: List[str] = []
    md_parts.append(f"### {title}")

    # 3-4 line succinct summary
    md_parts.append("")
    md_parts.append("**Summary (top lines):**")
    for l in summary_lines:
        md_parts.append(f"> {l}")

    md_parts.append("")
    md_parts.append(f"**Severity:** **{severity}**")

    if findings:
        md_parts.append("")
        md_parts.append("**Top findings:**")
        for f in findings:
            # Keep findings short
            md_parts.append(f"- `{f}`")

    if suggestions:
        md_parts.append("")
        md_parts.append("**Suggested next steps:**")
        for s in suggestions:
            md_parts.append(f"- {s}")

    # Collapsible debug / full output
    md_parts.append("")
    debug_block = full_logs or findings_text or "(no debug output)"
    # Trim very large debug payload but provide a note
    max_debug_chars = 60_000
    truncated = False
    if len(debug_block) > max_debug_chars:
        debug_block = debug_block[:max_debug_chars]
        truncated = True

    md_parts.append("<details>")
    md_parts.append("<summary>Show debug output</summary>")
    md_parts.append("")
    md_parts.append("```text")
    md_parts.append(debug_block.rstrip())
    if truncated:
        md_parts.append("\n...[truncated output]...")
    md_parts.append("```")
    md_parts.append("</details>")

    # Small footer with provenance
    md_parts.append("")
    md_parts.append("*Generated by SadGuard automated analysis — provides a short summary and expandable debug output to aid human reviewers.*")

    return textwrap.dedent("\n".join(md_parts)).strip()


def build_consolidated_comment(title: str, sections: List[Tuple[str, str]], max_summary_lines: int = 3) -> str:
    """Build a consolidated review comment containing multiple titled sections.

    `sections` is a list of (section_title, section_text). Each section gets a short summary and collapsible debug.
    """
    parts: List[str] = []
    parts.append(f"## {title}")
    for sec_title, sec_text in sections:
        parts.append("")
        parts.append(make_review_comment(sec_title, sec_text, full_logs=sec_text, max_summary_lines=max_summary_lines))

    return "\n\n".join(parts)
