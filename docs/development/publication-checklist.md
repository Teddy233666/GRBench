# Publication Checklist

## Candidate Boundary

- Publish from the independent clean-history candidate, never from the 786 MiB
  inherited Git history.
- Keep all historical observations in `results/latest-observed/` and keep
  `results/comparable/` empty until live oracle validation is complete.
- Label the first release as statically validated, with live adapter validation
  deferred.

## Local Gate

1. Regenerate manifests and require a clean manifest diff.
2. Run semantic, repository, Python, shell, JavaScript, Kuzu unit, and OrientDB
   contract checks from the candidate directory.
3. Scan every publication file and prospective Git object for credentials,
   private addresses, absolute workstation paths, and files above 10 MiB.
   Verify result path aliases with `python3 tools/sanitize_result_paths.py`.
4. Review `git status`, the complete staged file list, licenses, and result
   provenance before authorizing a commit.
5. Commit in a disposable local simulation, clone that commit, and require the
   full validation workflow to pass with no manifest regeneration diff.
6. Obtain release-owner sign-off for
   `docs/development/provenance-and-licensing.md`.

Release-owner licensing sign-off was confirmed on 2026-08-18. Commit creation,
remote creation, and push still require explicit operational authorization.

## Authorization Boundary

Do not commit, create a GitHub repository, configure a remote, tag a release,
or push until the maintainer explicitly authorizes those actions. After that
authorization, create one clean publication commit on `main`, enable GitHub
private vulnerability reporting, run CI, and compare the remote tree hash to
the approved local candidate.
