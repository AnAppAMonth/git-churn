#!/usr/bin/env python
import subprocess

# Each key is the SHA-1 hash of a processed commit. Before processing
# each commit we check this dictionary and only proceed if it's not
# already processed.
processed = {}


# This function takes the SHA-1 hash of a commit and returns a list of
# file paths and corresponding addition and deletion line counts, sorted
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
		parents = subprocess.check_output(
			'git show --summary --pretty="%P" ' + commit, shell=True).splitlines()[0].split()

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
			
			# Now do a diff between parent and commit to get the changes in this
			# commit
			diff = []
			stats = subprocess.check_output(
				'git diff-tree --numstat --no-commit-id -r %s %s' % (parent, commit), shell=True)
			stats = stats.splitlines()
			for stat in stats:
				items = stat.strip().split('\t')
				try:
					diff.append((items[2], int(items[0]), int(items[1])))
				except ValueError:
					# This is a binary file
					pass
			
			if len(diff) > 0:
				results.append(diff)
		
		else:
			# This is a root commit
			diff = []
			stats = subprocess.check_output(
				'git diff-tree --numstat --no-commit-id --root -r %s' % commit, shell=True)
			stats = stats.splitlines()
			for stat in stats:
				items = stat.strip().split('\t')
				try:
					diff.append((items[2], int(items[0]), int(items[1])))
				except ValueError:
					# This is a binary file
					pass

			return diff
		
		# Finally merge result arrays in results to get the result for this
		# commit.
		#
		# Note that we don't currently try to detect renames. So a rename
		# will cause N deletions and N additions, in total 2N line changes.
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
				(path, additions, deletions) = results[0][indices[0]]
				chosen = [0]
				for i in range(1, N):
					if results[i][indices[i]][0] < path:
						# This path is smaller, take this
						(path, additions, deletions) = results[i][indices[i]]
						chosen = [i]
					elif results[i][indices[i]][0] == path:
						# This is the same path, merge the line counts
						additions += results[i][indices[i]][1]
						deletions += results[i][indices[i]][2]
						chosen.append(i)

				# Add the new path into the result list
				retval.append((path, additions, deletions))

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
result = process_commit(head)

# Print the result
additions = 0
deletions = 0
for item in result:
	additions += item[1]
	deletions += item[2]
	print '%s\t%s\t%s' % (item[1], item[2], item[0])
print '\n%s lines added, %s lines deleted.\n' % (additions, deletions)



