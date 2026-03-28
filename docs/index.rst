ghud — GitHub Heads-Up Display
==============================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   api
   changelog

ghud gives you a terminal-based overview of your GitHub activity across all your portfolio repos.

.. code-block:: bash

   $ ghud           # global dashboard
   $ ghud i 42      # view issue #42
   $ ghud pr 15     # view PR #15
   $ ghud r         # repo dashboard for current directory

Features
--------

- **Multi-view CLI** — browse issues, PRs, and repos from the terminal
- Important notifications (review requests, mentions, assignments)
- Your open PRs with age and comment counts
- Recently merged PRs
- Issues from others on your portfolio repos
- Detail levels: brief, summary, standard, full
- Check status indicators for PRs (✓/✗/●/—)
- Auto-detects repo from git remote
- Repo discovery to keep your portfolio config complete
- Responsive two-column layout on wide terminals
- MCP server for AI agent integration
- Fast: ~2 seconds using concurrent API calls and GraphQL batching
