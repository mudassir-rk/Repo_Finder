#!/usr/bin/env python3
import os
import re
import sys
import json
import datetime
import urllib.request
import urllib.error
import urllib.parse

import yaml  

GITHUB_API = "https://api.github.com"
STATE_FILE = ".repo_finder_seen.json"  

def env(name, required=True, default=None):
    val = os.environ.get(name, default)
    if required and not val:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return val


def gh_request(url, token, method="GET", body=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"GitHub API error {e.code} for {url}: {e.read().decode()}", file=sys.stderr)
        raise


def resolve_placeholders(query):
    """Replace {days_ago:N} with an actual ISO date N days before today."""
    def repl(match):
        n = int(match.group(1))
        d = datetime.date.today() - datetime.timedelta(days=n)
        return d.isoformat()
    return re.sub(r"\{days_ago:(\d+)\}", repl, query)


def search_repos(token, query, sort, order, per_page):
    q = resolve_placeholders(query)
    url = (
        f"{GITHUB_API}/search/repositories"
        f"?q={urllib.parse.quote(q)}&sort={sort}&order={order}&per_page={per_page}"
    )
    result = gh_request(url, token)
    return result.get("items", [])


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_state(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def format_repo(repo):
    name = repo["full_name"]
    url = repo["html_url"]
    stars = repo["stargazers_count"]
    desc = (repo.get("description") or "").strip()
    lang = repo.get("language") or "—"
    updated = repo["pushed_at"][:10]
    return f"- **[{name}]({url})** ⭐ {stars:,} · {lang} · updated {updated}\n  {desc}"


def build_digest(config, token):
    seen = load_state() if config.get("skip_previously_seen") else set()
    new_seen = set(seen)
    sections = []

    for basket in config["baskets"]:
        items = search_repos(
            token,
            basket["query"],
            basket.get("sort", "stars"),
            basket.get("order", "desc"),
            basket.get("max_results", 10),
        )
        filtered = [r for r in items if r["full_name"] not in seen]
        for r in filtered:
            new_seen.add(r["full_name"])

        if filtered:
            lines = [format_repo(r) for r in filtered]
            sections.append(f"### {basket['name']}\n" + "\n".join(lines))
        else:
            sections.append(f"### {basket['name']}\n_No new matches this run._")

    save_state(new_seen)

    date_str = datetime.date.today().isoformat()
    body = f"_Digest generated {date_str}_\n\n" + "\n\n".join(sections)
    return body


def find_existing_issue(token, repo_full_name, title):
    url = f"{GITHUB_API}/search/issues?q={urllib.parse.quote(f'repo:{repo_full_name} is:issue in:title {title}')}"
    result = gh_request(url, token)
    for item in result.get("items", []):
        if item["title"] == title:
            return item["number"]
    return None


def upsert_issue(token, repo_full_name, title, body):
    issue_number = find_existing_issue(token, repo_full_name, title)
    if issue_number:
        url = f"{GITHUB_API}/repos/{repo_full_name}/issues/{issue_number}"
        gh_request(url, token, method="PATCH", body={"body": body})
        print(f"Updated issue #{issue_number}")
    else:
        url = f"{GITHUB_API}/repos/{repo_full_name}/issues"
        result = gh_request(url, token, method="POST", body={"title": title, "body": body})
        print(f"Created issue #{result['number']}")


if __name__ == "__main__":
    token = env("GITHUB_TOKEN")
    repo_full_name = env("GITHUB_REPOSITORY")  

    with open("config.yml") as f:
        config = yaml.safe_load(f)

    body = build_digest(config, token)
    upsert_issue(token, repo_full_name, config["digest_title"], body)
