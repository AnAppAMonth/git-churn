#!/usr/bin/env python

VERSION = '0.0.1'

import subprocess
import argparse

needs_author = False
needs_date = False

# Repeatedly calling git-diff-tree to get the diffstats works but is
# too slow. So we have to use the "porcelain" git-log command and parse
# its output. This function does just that and merges the diffstats to
# compute the final result.
def process_diffstats(remaining):
	# First produce the format string to use according to options
	if needs_author and needs_date:
		format_str = '%aN%n%aE%n%at'
	elif needs_author:
		format_str = '%aN%n%aE'
	elif needs_date:
		format_str = '%at'
	else:
		format_str = ''

	cmd_str = 'git log --numstat --format="format:%s" %s' % (format_str, ' '.join(remaining))
	logs = subprocess.check_output(cmd_str, shell=True).splitlines()

	# This dictionary holds the merge result so far. Each key is a file
	# path, and its value is the total insertions and deletions currently
	# discovered.
	result = {}

	# Parse a single commit from the logs, starting at line ln
	# Returns the starting line of the next commit, -1 if done.
	def parse_commit(ln):
		try:
			x = 0

			if needs_author:
				# TODO: verify these two lines are indeed author name and email
				author_name = logs[ln]
				author_email = logs[ln + 1]
				x += 2

			if needs_date:
				# TODO: verify this line is indeed author date
				author_date = logs[ln + x]
				x += 1

			# The next line is either the first line of this commit's
			# diffstats or the first line of the next commit (its parent).
			items = logs[ln + x].strip().split('\t')
			while len(items) == 3:
				try:
					insertions = int(items[0])
					deletions = int(items[1])
					path = items[2]
				except ValueError:
					if (items[0] == '-' and items[1] == '-'):
						# This is a binary file, ignore it
						pass
					else:
						# Unexpected line, this commit's numstats session
						# must be over.
						break
				else:
					# Merge this entry into result
					if path in result:
						entry = result[path]
						entry[0] += insertions
						entry[1] += deletions
					else:
						result[path] = [insertions, deletions]

				x += 1
				items = logs[ln + x].strip().split('\t')

			# Diffstats end with an empty line, jump past that
			if items[0] == '':
				x += 1

			# Unexpected line encountered, jump over it
			if x == 0:
				x = 1

			return ln + x

		except IndexError:
			# No more lines left in logs, we are done.
			return -1

	ln = 0
	while ln >= 0:
		ln = parse_commit(ln)

	return result


if __name__ == "__main__":
	usage = 'git churn [<options>] [<revision range>] [[--] <path>...]'
	description = """\
    This command displays line change stats for each file as well
    as the entire repository over the specified range of commits.

    The range of commits can be specified using the same mechanism
    supported by git-log(1), including the <revision range> and
    <path> arguments, and git-log(1)'s supported options under the
    "Commit Limiting" section. See git-log(1)'s manpage for detailed
    descriptions.

    Don't use other options of git-log(1), especially those that
    affect how its output is formatted! This command may fail to
    work as expected if you do so.
"""
	parser = argparse.ArgumentParser(usage=usage, description=description,
									 formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument('-v', '--version', action='version', version="%(prog)s version " + VERSION)
	ns, remaining = parser.parse_known_args()

	# First call git-log and process all the diffstats
	result = process_diffstats(remaining)

	# The final result is already in result but in the form of a dictionary.
	# We need to sort the results by file path and print them.
	keys = result.keys()
	keys.sort()

	changed = len(keys)
	insertions = 0
	deletions = 0

	if changed > 0:
		for key in keys:
			value = result[key]
			insertions += value[0]
			deletions += value[1]
			print '%s\t%s\t%s' % (value[0], value[1], key)

		changed_text = '%s file%s changed' % (changed, changed>1 and 's' or '')
		if insertions > 0:
			insertions_text = ', %s insertion%s(+)' % (insertions, insertions>1 and 's' or '')
		else:
			insertions_text = ''
		if deletions > 0:
			deletions_text = ', %s deletion%s(-)' % (deletions, deletions>1 and 's' or '')
		else:
			deletions_text = ''

		print '\n%s%s%s\n' % (changed_text, insertions_text, deletions_text)
