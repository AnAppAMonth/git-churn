#!/usr/bin/env python
import subprocess

# Each key is the SHA-1 hash of a processed commit. Before processing
# each commit we check this dictionary and only proceed if it's not
# already processed.
processed = {}

# Each key is the SHA-1 hash of a commit. The value is the parent(s)
# of the commit.
parents_cache = {}
# Each key is the SHA-1 hash of a commit. The value is the diffstats
# of the commit (compared to its parent).
diffstats_cache = {}

# Repeatedly calling git-diff-tree to get the diffstats works but is
# too slow. So we have to use the "porcelain" git-log command and parse
# its output. This function does just that and stores the diffstats
# in a dictionary to be used later by process_commit().
def get_diffstats():
	logs = subprocess.check_output(
		'git log --numstat --format="format:%H%n%P"', shell=True).splitlines()
	
	# Parse a single commit from the logs, starting at line ln
	# Returns the starting line of the next commit, -1 if done.
	def parse_commit(ln):
		parents = []
		stats = []

		try:
			# First line is the hash of this commit
			commit = logs[ln]
	
			# Second line is the hash of its parents
			parents = logs[ln+1].split()
			parents_cache[commit] = parents
	
			# The third line is either the first line of this commit's
			# diffstats or the hash of the next commit (its parent).
			x = 2
			items = logs[ln+x].strip().split('\t')
			while len(items) > 1:
				try:
					stats.append((items[2], int(items[0]), int(items[1])))
				except ValueError:
					# This is a binary file, ignore it
					pass
				
				x += 1
				items = logs[ln+x].strip().split('\t')
				
			# Diffstats end with an empty line, jump past that
			if items[0] == '':
				x += 1
	
			# We have finished parsing the diffstats, job for this commit
			# is done.
			diffstats_cache[commit] = stats
			
			return ln + x

		except IndexError:
			# The parents line doesn't exist, this must be the root commit.
			parents_cache[commit] = parents
			diffstats_cache[commit] = stats
			return -1

	ln = 0
	while ln >= 0:
		ln = parse_commit(ln)


# This function takes the SHA-1 hash of a commit and returns a list of
# file paths and corresponding insertion and deletion line counts, sorted
# alphabetically by file paths, according to changes done by this commit
# AND all its ancestors.
#
# If this commit and its ancestors don't contain any change to text files
# (say they only change binary files), or this commit has already been
# processed before, this function returns an empty list.
def process_commit(commit):
	# Only proceed if the commit isn't already processed.
	if commit not in processed:
		processed[commit] = True

		# First get a list of parent hashes of the commit
		parents = parents_cache[commit]

		# This array contains a list of result arrays to be merged.
		results = []

		num_of_parents = len(parents)
		if num_of_parents > 1:
			# A merge commit. We ignore merge commits. This is probably
			# the most reasonable choice, and is also what "hg churn" does.
			# So only its parents are processed.
			for parent in parents:
				parent_result = process_commit(parent)
				if len(parent_result) > 0:
					results.append(parent_result)
		
		elif num_of_parents == 1:
			# This is a normal commit, process its only parent
			parent = parents[0]
			parent_result = process_commit(parent)
			if len(parent_result) > 0:
				results.append(parent_result)
			
			# Now get the diffstats of the commit (against its parent)
			stats = diffstats_cache[commit]
			if len(stats) > 0:
				results.append(stats)
		
		else:
			# This is a root commit
			return diffstats_cache[commit]
		
		# Finally merge result arrays in results to get the result for this
		# commit.
		#
		# Note that we don't currently try to detect renames. So a rename
		# will cause N deletions and N insertions, in total 2N line changes.
		# It also seems like "hg churn" works the same way.
		#
		# Also note that we utilize the fact that git sorts the output of
		# git-diff-tree by file paths in the alphabetical order to facilitate
		# the merge.
		
		# We only need to merge if there are more than one entries in results
		num_of_results = len(results)
		if num_of_results == 1:
			return results[0]
		elif num_of_results == 0:
			return []
		else:
			retval = []
	
			N = len(results)
			indices = []
			for i in range(N):
				indices.append(0)
				
			while True:
				# Do an N-way merge 
				(path, insertions, deletions) = results[0][indices[0]]
				chosen = [0]
				for i in range(1, N):
					if results[i][indices[i]][0] < path:
						# This path is smaller, take this
						(path, insertions, deletions) = results[i][indices[i]]
						chosen = [i]
					elif results[i][indices[i]][0] == path:
						# This is the same path, merge the line counts
						insertions += results[i][indices[i]][1]
						deletions += results[i][indices[i]][2]
						chosen.append(i)

				# Add the new path into the result list
				retval.append((path, insertions, deletions))

				# Finally increment the indices of the chosen arrays
				for i in range(len(chosen)-1, -1, -1):
					idx = chosen[i]
					indices[idx] += 1
					if indices[idx] >= len(results[idx]):
						# results[i] doesn't contain new entries, remove this list
						results.pop(idx)
						indices.pop(idx)
						N -= 1

				if N == 0:
					# We are done.
					break
			
			return retval

	else:
		# This commit is already processed, return an empty list
		return []



# First find the hash of the HEAD
head = subprocess.check_output('git rev-parse HEAD', shell=True).strip()

# Now process HEAD
get_diffstats()
result = process_commit(head)

# Print the result
changed = len(result)
insertions = 0
deletions = 0

if changed > 0:
	for item in result:
		insertions += item[1]
		deletions += item[2]
		print '%s\t%s\t%s' % (item[1], item[2], item[0])

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



