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


def get_svn_root(svn_dir):
    """Find the root of a svn repository."""
    with open('/dev/null', 'a') as dev_null:
        try:
            cwd = os.getcwd()
            os.chdir(svn_dir)
            out = check_output(['svn', 'info'], universal_newlines=True,
                               stderr=dev_null)
            config = dict(line.split(': ', 1) for line in
                          out.strip().split('\n') if line)
            return config['Repository Root']
        except CalledProcessError:
            raise ValueError("%s does not seem to be a proper svn repository." %
                             svn_dir)
        except KeyError:
            raise ValueError("Could not deduce the address of the repository in"
                             " %s." % svn_dir)
        finally:
            # executed before return
            os.chdir(cwd)


def list_repo(directories, excluded_dirs):
    """Find recursively git and svn repositories."""
    svn_repos = []
    done_dirs = []
    for directory in directories:
        if any(directory.startswith(done_dir) for done_dir in done_dirs):
            continue
        for dirpath, dirnames, filenames in os.walk(directory):
            if any(dirpath.startswith(excluded) for excluded in excluded_dirs):
                continue
            if '.git' in dirnames:
                try:
                    config = get_config(dirpath)
                    yield ('git', dirpath, config)
                except ValueError as e:
                    print(e)
            elif '.svn' in dirnames:
                if any(dirpath.startswith(svn_repo) for svn_repo in svn_repos):
                    # don't allow svn repos inside others (externals assumed)
                    continue
                try:
                    repo_root = get_svn_root(dirpath)
                    svn_repos.append(dirpath)
                    yield ('svn', dirpath, repo_root)
                except ValueError as e:
                    print(e)


def main():
    # getting parameters
    parser = argparse.ArgumentParser(description='Manage repositories.')
    parser.add_argument('-l', '--list', nargs='*',
                        help='the directories to search repositories in.')
    parser.add_argument('-e', '--exclude', nargs='+', default=[],
                        help='directories to exclude from search.')
    args = parser.parse_args()
    # listing
    if args.list is not None:
        if not args.list:
            args.list = ['.']
        for repo_type, repo_dir, config in list_repo(args.list, args.exclude):
            print('%s: %s' % (repo_type, repo_dir))


if __name__ == '__main__':
    main()
