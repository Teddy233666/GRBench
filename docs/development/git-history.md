# Git History Integration

Do not publish the inherited history as-is: it includes large data blobs and
unrelated legacy content. The selected publication candidate intentionally uses
one clean initial commit and does not share objects with that history.

Recommended publication sequence:

1. Tag or bundle the untouched legacy core branch as a private archival
   reference.
2. Confirm the clean candidate has no remote, no parent commit, and no hidden
   object alternates.
3. Record imported source aliases and authorization evidence outside Git.
4. Normalize text and regenerate manifests before staging the first commit.
5. Commit once, clone that commit into a temporary directory, and run every CI
   check against the clone before configuring a public remote.

If maintainers later choose to publish filtered legacy history, perform that
work in a disposable clone and repeat the complete object audit. No commit,
remote creation, or push should occur without explicit maintainer approval.
