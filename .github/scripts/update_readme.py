#!/usr/bin/env python3
"""
Dynamic README updater for ShresthaSailesh GitHub profile.
Fetches private + public repositories and updates the profile README
with current project activity.
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


def github_api_request(url, token):
    """Make an authenticated GitHub API request."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "ShresthaSailesh-Profile-Updater")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} for {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_all_repos(token):
    """Fetch all repositories (public + private) for the authenticated user."""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/user/repos?per_page=100&page={page}&sort=pushed&type=all"
        data = github_api_request(url, token)
        if not data or len(data) == 0:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def get_user_info(token):
    """Fetch authenticated user info."""
    return github_api_request("https://api.github.com/user", token)


def days_since(date_str):
    """Return number of days since a date string."""
    if not date_str:
        return 9999
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return 9999


def get_language_emoji(lang):
    """Return an emoji for a programming language."""
    mapping = {
        "Java": "☕",
        "JavaScript": "🟨",
        "TypeScript": "🔷",
        "Python": "🐍",
        "HTML": "🌐",
        "CSS": "🎨",
        "Shell": "🐚",
        "Go": "🐹",
        "Rust": "🦀",
        "C++": "⚙️",
        "C": "⚙️",
        "Ruby": "💎",
        "PHP": "🐘",
        "Swift": "🍎",
        "Kotlin": "🟣",
    }
    return mapping.get(lang, "📦")


def get_visibility_badge(is_private):
    """Return a badge string for repo visibility."""
    if is_private:
        return "🔒 Private"
    return "🌐 Public"


def format_repo_row(repo, show_private_badge=True):
    """Format a repository as a markdown table row."""
    name = repo.get("name", "")
    description = repo.get("description") or "_No description_"
    lang = repo.get("language") or "N/A"
    lang_emoji = get_language_emoji(lang)
    is_private = repo.get("private", False)
    html_url = repo.get("html_url", "")
    pushed_at = repo.get("pushed_at", "")
    days = days_since(pushed_at)

    # Build activity indicator
    if days <= 7:
        activity = "🟢 Active"
    elif days <= 30:
        activity = "🟡 Recent"
    elif days <= 90:
        activity = "🟠 Paused"
    else:
        activity = "⚫ Archived"

    visibility = get_visibility_badge(is_private) if show_private_badge else ""

    if is_private:
        # For private repos, don't link to them but show the name
        repo_cell = f"🔒 **{name}**"
    else:
        repo_cell = f"[**{name}**]({html_url})"

    row = f"| {repo_cell} | {description} | {lang_emoji} {lang} | {activity} |"
    return row


def build_currently_working_on(repos):
    """Build the 'Currently Working On' section."""
    active_repos = [r for r in repos if days_since(r.get("pushed_at")) <= 30]
    active_repos.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)
    active_repos = active_repos[:6]  # Top 6 most recently active

    if not active_repos:
        return "_No recent activity detected._"

    lines = [
        "| Project | Description | Language | Status |",
        "|---------|-------------|----------|--------|",
    ]
    for repo in active_repos:
        lines.append(format_repo_row(repo))

    return "\n".join(lines)


def build_private_projects(repos):
    """Build the 'Private Projects' section."""
    private_repos = [r for r in repos if r.get("private", False)]
    private_repos.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)

    if not private_repos:
        return "_No private repositories found. Add a `GH_PAT` secret with `repo` scope to display private projects._"

    lines = [
        "| Project | Description | Language | Status |",
        "|---------|-------------|----------|--------|",
    ]
    for repo in private_repos:
        lines.append(format_repo_row(repo))

    return "\n".join(lines)


def build_all_projects(repos, profile_repo_name=None):
    """Build the 'All Projects' section with public repos."""
    public_repos = [r for r in repos if not r.get("private", False)]
    # Exclude the profile repo itself (the repo whose name matches the owner login)
    if profile_repo_name:
        public_repos = [r for r in public_repos if r.get("name") != profile_repo_name]
    public_repos.sort(key=lambda r: r.get("pushed_at", ""), reverse=True)

    if not public_repos:
        return "_No public repositories found._"

    lines = [
        "| Project | Description | Language | Status |",
        "|---------|-------------|----------|--------|",
    ]
    for repo in public_repos:
        lines.append(format_repo_row(repo, show_private_badge=False))

    return "\n".join(lines)


def update_readme_section(readme_content, start_marker, end_marker, new_content):
    """Replace content between markers in the README."""
    pattern = re.compile(
        rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL
    )
    replacement = f"{start_marker}\n{new_content}\n{end_marker}"
    if pattern.search(readme_content):
        return pattern.sub(replacement, readme_content)
    else:
        print(f"Warning: Could not find markers '{start_marker}' and '{end_marker}'")
        return readme_content


def main():
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: No GitHub token found. Set GH_PAT or GITHUB_TOKEN environment variable.")
        return 1

    print("Fetching user info...")
    user_info = get_user_info(token)
    profile_repo_name = user_info.get("login") if user_info else None
    if profile_repo_name:
        print(f"Authenticated as: {profile_repo_name}")

    print("Fetching repositories...")
    repos = get_all_repos(token)
    print(f"Found {len(repos)} repositories total")

    private_count = sum(1 for r in repos if r.get("private"))
    public_count = len(repos) - private_count
    print(f"  Public: {public_count}, Private: {private_count}")

    # Build dynamic sections
    currently_working = build_currently_working_on(repos)
    private_projects = build_private_projects(repos)
    all_projects = build_all_projects(repos, profile_repo_name=profile_repo_name)

    # Timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Resolve README path: the script lives at .github/scripts/, README is at repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    readme_path = os.path.join(repo_root, "README.md")
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    # Update sections
    readme_content = update_readme_section(
        readme_content,
        "<!-- CURRENTLY_WORKING_ON_START -->",
        "<!-- CURRENTLY_WORKING_ON_END -->",
        currently_working,
    )
    readme_content = update_readme_section(
        readme_content,
        "<!-- PRIVATE_PROJECTS_START -->",
        "<!-- PRIVATE_PROJECTS_END -->",
        private_projects,
    )
    readme_content = update_readme_section(
        readme_content,
        "<!-- ALL_PROJECTS_START -->",
        "<!-- ALL_PROJECTS_END -->",
        all_projects,
    )
    readme_content = update_readme_section(
        readme_content,
        "<!-- LAST_UPDATED_START -->",
        "<!-- LAST_UPDATED_END -->",
        f"_🤖 Auto-updated by GitHub Actions on **{timestamp}**_",
    )

    # Write the updated README
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"README updated successfully at {timestamp}")
    return 0


if __name__ == "__main__":
    exit(main())
