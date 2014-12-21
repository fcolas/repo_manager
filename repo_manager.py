import argparse
import os


def list_repo(directory):
    "Find recursively git and svn repositories."
    git_repos = []
    svn_repos = []
    for dirpath, dirnames, filenames in os.walk(directory):
        if '.git' in dirnames:
            git_repos.append(dirpath)
        elif '.svn' in dirnames:
            if any(dirpath.startswith(svn_repo) for svn_repo in svn_repos):
                # don't allow svn repos inside others (assumed to be externals)
                continue
            svn_repos.append(dirpath)
    return git_repos, svn_repos


def main():
    # getting parameters
    parser = argparse.ArgumentParser(description="Manage repositories.")
    parser.add_argument('directory',
                        help='the directory to start searching in.')
    args = parser.parse_args()
    # invoking main function
    git_repos, svn_repos = list_repo(args.directory)
    for r in git_repos:
        print('git', r)
    for r in svn_repos:
        print('svn', r)


if __name__ == '__main__':
    main()
