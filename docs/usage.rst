Usage
=====

Overview Dashboard
------------------

.. code-block:: bash

   # Show your dashboard (default)
   ghud

   # Explicit overview command
   ghud overview

   # Include low-priority notifications (subscribed, comment, etc.)
   ghud overview --all

   # Extend merged-PR lookback to 30 days
   ghud overview --days 30

The dashboard shows five sections (empty sections are hidden):

1. **Important Notifications** — review_requested, mention, assign, team_mention, security_alert
2. **New Issues From Others** — open issues on your portfolio repos, excluding your own
3. **Your Open PRs** — PRs you authored, with age and comment counts
4. **Recently Merged** — your PRs merged within the lookback window
5. **Other Activity** — notifications from repos not in your portfolio

On wide terminals (>=120 columns), sections are arranged in two columns:
attention-needed on the left, your activity on the right.

Issues
------

.. code-block:: bash

   # List open issues for the current repo (detected from git remote)
   ghud issue
   ghud i

   # List issues for a specific repo
   ghud i --repo owner/repo

   # List issues across all portfolio repos
   ghud i --repo all

   # View issue detail
   ghud i 42

   # View with different detail levels
   ghud i 42 --detail brief      # Header + comment count only
   ghud i 42 --detail summary    # Header + all comment headers (no bodies)
   ghud i 42 --detail standard   # Header + body + last 3 comments (default)
   ghud i 42 --detail full       # Everything including timeline events

   # Control comment display
   ghud i 42 --comments 10       # Show last 10 comments
   ghud i 42 --comments all      # Show all comments

   # Filter and limit list view
   ghud i --state closed
   ghud i --limit 50

Pull Requests
-------------

.. code-block:: bash

   # List open PRs for the current repo
   ghud pr

   # List PRs for a specific repo
   ghud pr --repo owner/repo

   # View PR detail
   ghud pr 15

   # View with different detail levels
   ghud pr 15 --detail brief      # Header only
   ghud pr 15 --detail standard   # Header + body + comments + check indicator
   ghud pr 15 --detail full       # All of the above + expanded checks + reviews

PR list views show check status indicators:

- ``✓`` — all checks passing
- ``✗`` — one or more checks failing
- ``●`` — checks pending
- ``—`` — no checks configured

Repo Dashboard
--------------

.. code-block:: bash

   # Dashboard for the current repo
   ghud repo
   ghud r

   # Dashboard for a specific repo
   ghud r --repo owner/repo

Shows open issues and pull requests for a single repo in a combined view.

Discover
--------

.. code-block:: bash

   # See what repos are missing from your portfolio config
   ghud discover --dry-run

   # Add missing repos to the 'uncategorized' section
   ghud discover

The discover command queries your GitHub account for all repos and compares
against your portfolio. With a ``projects.yaml`` portfolio, new repos are added
to an ``uncategorized`` section for you to organize later. When your portfolio
comes from ``~/.mrconfig``, discover instead prints ``mr register`` hints
(myrepos owns that file) rather than writing.

MCP Server
----------

.. code-block:: bash

   ghud serve

Starts an MCP (Model Context Protocol) server over stdio, exposing dashboard
tools for AI agents. Available tools include ``get_dashboard``,
``get_notifications_tool``, ``get_open_prs_tool``, ``get_merged_prs_tool``,
``get_issues_from_others``, ``get_portfolio_repos``, and ``discover_repos``.

Common Options
--------------

``--repo`` / ``-r``
   Specify a repository as ``owner/repo``. Use ``--repo all`` to operate across
   all portfolio repos. If omitted, ghud detects the repo from your current
   git directory's remote.

``--no-pager``
   Disable piping output through a pager. By default, detail views use a pager
   when output exceeds the terminal height.

Subcommand Aliases
------------------

For quick access:

- ``ghud i`` → ``ghud issue``
- ``ghud o`` → ``ghud overview``
- ``ghud r`` → ``ghud repo``

Configuration
-------------

ghud determines your portfolio repos from one of two sources, in order:

1. ``~/.mrconfig`` — if you manage your repos with `myrepos
   <https://myrepos.branchable.com/>`_ (``mr``), ghud reads its manifest
   directly, deriving each ``owner/repo`` from the stanza's ``checkout`` clone
   URL. No separate config to maintain (honors ``$MR_CONFIG``).
2. ``projects.yaml`` — fallback when no ``.mrconfig`` is found. Checked at:

   - ``$XDG_CONFIG_HOME/ghud/projects.yaml`` (default: ``~/.config/ghud/projects.yaml``)
   - ``~/Projects/pages/src/_data/projects.yaml``

   The YAML uses a nested ``categories -> subcategories -> projects`` structure.
   Repos in the ``ignored`` category are excluded from the dashboard.
