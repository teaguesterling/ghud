Usage
=====

Dashboard
---------

.. code-block:: bash

   # Show your dashboard (default)
   ghud

   # Include low-priority notifications (subscribed, comment, etc.)
   ghud --all

   # Extend merged-PR lookback to 30 days
   ghud --days 30

The dashboard shows five sections (empty sections are hidden):

1. **Important Notifications** — review_requested, mention, assign, team_mention, security_alert
2. **New Issues From Others** — open issues on your portfolio repos, excluding your own
3. **Your Open PRs** — PRs you authored, with age and comment counts
4. **Recently Merged** — your PRs merged within the lookback window
5. **Other Activity** — notifications from repos not in your portfolio

On wide terminals (>=120 columns), sections are arranged in two columns:
attention-needed on the left, your activity on the right.

Discover
--------

.. code-block:: bash

   # See what repos are missing from your portfolio config
   ghud discover --dry-run

   # Add missing repos to the 'uncategorized' section
   ghud discover

The discover command queries your GitHub account for all repos and compares
against your ``projects.yaml``. New repos are added to an ``uncategorized``
section for you to organize later.

Configuration
-------------

ghud reads a ``projects.yaml`` file that lists your portfolio repos.
It checks these locations in order:

1. ``~/Projects/pages/src/_data/projects.yaml``
2. ``/mnt/aux-data/teague/Projects/pages/src/_data/projects.yaml``

The YAML uses a nested ``categories -> subcategories -> projects`` structure.
Repos in the ``ignored`` category are excluded from the dashboard.
