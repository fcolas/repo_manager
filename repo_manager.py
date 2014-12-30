import argparse
import os
import sys
from subprocess import call, check_output, CalledProcessError
from pprint import pformat


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
            elif k.startswith('gui.'):
                config.pop(k)   # remove gui parameters
        return config
    except CalledProcessError:
        raise ValueError('%s does not seem to be a proper git repository.' %
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
            raise ValueError('%s does not seem to be a proper svn repository.' %
                             svn_dir)
        except KeyError:
            raise ValueError('Could not deduce the address of the repository in'
                             ' %s.' % svn_dir)
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


def install(repo_file, directory):
    """Install repositories listed in repo_file into directory."""
    def install_git(name, config):
        """Install git repository with its config."""
        if 'remote.origin.url' in config:
            origin_url = config['remote.origin.url']
        else:
            print('No origin remote for', name)
            return
        config_str = ' '.join('-c %s=%s' % (k, v) for k, v in config.items())
        call(['git', 'clone', origin_url, config_str, name])

    def install_svn(name, root):
        """Checkout svn repository."""
        # TODO test!
        call(['svn', 'checkout', root, name])

    os.makedirs(directory, exist_ok=True)
    repo_list = load_list(repo_file)
    cwd = os.getcwd()
    os.chdir(directory)
    for repo_type, repo_name, config in repo_list:
        if repo_type == 'git':
            install_git(repo_name, config)
        elif repo_type == 'svn':
            install_svn(repo_name, config)
        else:
            print('Unknown repository type:', repo_type, 'for', repo_name)
    os.chdir(cwd)


def load_list(filename):
    """Load a saved list of repositories."""
    with open(filename) as repo_file:
        # TODO better deserialization
        repo_list = eval(repo_file.read())
    return repo_list


def save_list(search_dirs, filename, exclude_dirs):
    """Save list of repositories."""
    with open(filename, 'w') as repo_file:
        # TODO better serialization
        repo_file.write(pformat(list(list_repo(search_dirs, exclude_dirs)),
                                indent=2, width=1))
        repo_file.write('\n')


def echo_list(search_dirs, exclude_dirs):
    """Print list of directories."""
    for repo_type, repo_dir, config in list_repo(search_dirs, exclude_dirs):
        print('%s: %s' % (repo_type, repo_dir))


def main():
    # getting parameters
    parser = argparse.ArgumentParser(description='Manage repositories.')
    parser.add_argument('-l', '--list', nargs='*',
                        help='the directories to search repositories in.')
    parser.add_argument('-e', '--exclude', nargs='+', default=[],
                        help='directories to exclude from search.')
    parser.add_argument('-f', '--repo_file', nargs=1,
                        help='file listing of a repository.')
    parser.add_argument('-i', '--install', nargs='?',
                        help='install repositories')
    args = parser.parse_args()
    # installing
    if args.install is not None:
        if not args.install:
            install_dir = '.'
        else:
            install_dir = args.install
        if args.repo_file is None:
            print('install command requires a repo_file.')
            sys.exit(1)
        if args.list is not None:
            print('install and list commands are not compatible.')
            sys.exit(2)
        install(args.repo_file[0], install_dir)
    # listing
    elif args.list is not None:
        if not args.list:
            args.list = ['.']
        if args.repo_file is not None:
            save_list(args.list, args.repo_file[0], args.exclude)
        else:
            echo_list(args.list, args.exclude)


if __name__ == '__main__':
    main()
