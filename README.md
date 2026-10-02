[Uploading README.md…]()
# Repo Finder

Finds good GitHub repos on a weekly schedule and posts them as a single,
auto-updating GitHub Issue in this repo. 100% free — runs on GitHub Actions'
free tier and uses only the built-in `GITHUB_TOKEN`, so there's nothing to
sign up for.

## Setup (5 minutes)

1. Create a new **public** GitHub repo (or reuse an existing one) — public
   repos get unlimited free Actions minutes.
2. Copy these files into it, keeping the folder structure:
   ```
   config.yml
   scripts/find_repos.py
   .github/workflows/repo-finder.yml
   ```
3. Commit and push.
4. Go to the **Actions** tab → "Repo Finder Digest" → **Run workflow** to
   trigger it immediately (don't wait for Monday).
5. Check the **Issues** tab — you'll see a new issue titled
   "📦 Repo Finder Digest" with your results. It updates in place every run.

## Customizing what it looks for

Edit `config.yml` — no code changes needed:
- Change/add/remove "baskets" (each is one GitHub search query)
- Adjust `stars:`, `language:`, `topic:`, `pushed:`, `license:` filters
- Change `max_results` per basket
- Change the cron schedule in the workflow file (default: every Monday)

See the comments in `config.yml` for query syntax examples, or the
[GitHub search qualifiers docs](https://docs.github.com/search-github/searching-on-github/searching-for-repositories).

## How it avoids repeats

The script keeps a small `.repo_finder_seen.json` file (committed back to
the repo automatically) so repos already shown in a past digest aren't
shown again. Delete that file if you ever want a fresh start, or set
`skip_previously_seen: false` in the config to always show full results.

## Rate limits

The Search API allows 30 requests/minute when authenticated — this script
makes 4 (one per basket), so you're nowhere near the limit even running
this hourly.
