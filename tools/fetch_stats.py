#!/usr/bin/env python3
"""Pull the live numbers the profile shows into data/stats.json.

Standard library only, so the daily workflow needs no install step. Uses
GITHUB_TOKEN when it is set, otherwise `gh auth token`.
"""
import datetime
import json
import os
import pathlib
import subprocess
import urllib.request

USER = "MCDFsteve"
OWNERS = [("users", "MCDFsteve"), ("orgs", "AimesSoft")]
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "stats.json"

# Generated or markup languages say little about what is actually written.
SKIP_LANGUAGES = {"HTML", "CSS", "SCSS", "Makefile", "CMake", "Shell", "PowerShell", "Batchfile", "Nix",
                  "Inno Setup", "NSIS", "Roff", "Dockerfile", "GLSL", "Metal", "HLSL", "WGSL", "Objective-C++"}
RECENT_DAYS = 365


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


TOKEN = token()


def request(url, body=None):
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def public_repos(kind, owner):
    repos, page = [], 1
    while True:
        batch = request(f"https://api.github.com/{kind}/{owner}/repos?type=public&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def profile():
    query = """query($login:String!){user(login:$login){createdAt followers{totalCount}
      contributionsCollection{contributionCalendar{totalContributions
      weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {"login": USER}}).encode()
    user = request("https://api.github.com/graphql", body)["data"]["user"]
    calendar = user["contributionsCollection"]["contributionCalendar"]
    return {
        "since": user["createdAt"][:10],
        "followers": user["followers"]["totalCount"],
        "contributions": calendar["totalContributions"],
        "first_day": calendar["weeks"][0]["contributionDays"][0]["date"],
        "weeks": [[d["contributionCount"] for d in w["contributionDays"]] for w in calendar["weeks"]],
    }


def recent_languages(repos):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=RECENT_DAYS)
    totals = {}
    for repo in repos:
        if datetime.datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00")) < cutoff:
            continue
        for name, size in request(repo["languages_url"]).items():
            if name not in SKIP_LANGUAGES:
                totals[name] = totals.get(name, 0) + size
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]))


def main():
    repos = [r for kind, owner in OWNERS for r in public_repos(kind, owner) if not r["fork"]]
    stars = {r["full_name"]: r["stargazers_count"] for r in repos}
    stats = {
        "repos": len(repos),
        "stars_total": sum(stars.values()),
        "stars": stars,
        "languages": recent_languages(repos),
        **profile(),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{stats['repos']} repos, {stats['stars_total']} stars, {stats['contributions']} contributions")


if __name__ == "__main__":
    main()
