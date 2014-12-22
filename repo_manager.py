import argparse
import os
from subprocess import check_output, CalledProcessError


def get_config(git_dir):
    """Find useful configuration of a git directory."""
    try:
        cwd = os.getcwd()
        os.chdir(git_dir)
        out = check_output(['git', 'config', '--local', '--list'],
                           universal_newlines=True)
        config = dict(line.split('=') for line in out.strip().split('\n')
                      if line)
        for k in list(config.keys()):
            if k.startswith('core.'):
                config.pop(k)   # remove core parameters
        return config
    except CalledProcessError:
        raise ValueError("%s does not seem to be a proper git repository." %
                         git_dir)
    finally:
        # executed before return
        os.chdir(cwd)


def list_repo(directory):
    """Find recursively git and svn repositories."""
    git_repos = []
    svn_repos = []
    for dirpath, dirnames, filenames in os.walk(directory):
        if '.git' in dirnames:
            try:
                config = get_config(dirpath)
                git_repos.append((dirpath, config))
            except ValueError as e:
                print(e)
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
