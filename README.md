git-churn
=========

A churn extension for Git.

This command displays line change stats for each file as well as the entire
repository over the specified range of commits.

The range of commits can be specified using the same mechanism supported by
`git-log(1)`, including the `<revision range>` and `<path>` arguments, and
`git-log(1)`'s supported options under the "Commit Limiting" section. See
`git-log(1)`'s manpage for detailed descriptions.

Install
=======

Place the `git-churn` file anywhere in PATH, and make sure it has the `execute`
permission.

Usage
=====

```
git churn
```

Sample output:

```
35	0	.gitignore
20	0	LICENSE
4	0	README.md
153	0	git-churn
506	506	git-churn.py

5 files changed, 718 insertions(+), 506 deletions(-)
```

License
=======

MIT
