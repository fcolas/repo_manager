#!/usr/bin/env python3
# not compatible with Python2 as we're using exist_ok flag in os.makedirs
import argparse
import os
import os.path
import sys
from subprocess import call, check_output, CalledProcessError
import json


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
    def is_excluded(path, abs_excluded_dirs=[os.path.abspath(d) for d in
                                             excluded_dirs]):
        """Check that given path is not in excluded dirs."""
        abspath = os.path.abspath(path)
        return any(abspath.startswith(excluded_dir) for excluded_dir in
                   abs_excluded_dirs)
    for directory in directories:
        for dirpath, dirnames, filenames in os.walk(directory, topdown=True):
            if is_excluded(dirpath):
                # empty subdirectories as they would also be excluded
                dirnames[:] = []
                continue
            if '.git' in dirnames:
                try:
                    config = get_config(dirpath)
                    yield ('git', dirpath, config)
                except ValueError as e:
                    print(e)
            elif '.svn' in dirnames:
                try:
                    repo_root = get_svn_root(dirpath)
                    # exclude subdirectories
                    dirnames[:] = []
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
            print('No remote named origin: nothing done.')
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
    common_prefix = os.path.commonprefix(list(zip(*repo_list))[1])
    for repo_type, repo_name, config in repo_list:
        repo_name = os.path.relpath(repo_name, common_prefix)
        if repo_type == 'git':
            print("\033[1;97mInstalling \033[1;92m%s\033[1;97m...\033[0m" %
                  repo_name)
            install_git(repo_name, config)
        elif repo_type == 'svn':
            print("\033[1;97mInstalling \033[1;94m%s\033[1;97m...\033[0m" %
                  repo_name)
            install_svn(repo_name, config)
        else:
            print('Unknown repository type:', repo_type, 'for', repo_name)
    os.chdir(cwd)


def load_list(filename):
    """Load a saved list of repositories."""
    with open(filename) as repo_file:
        descr = json.load(repo_file)
    return descr['repo_list']


def save_list(search_dirs, filename, exclude_dirs):
    """Save list of repositories."""
    repo_list = list(list_repo(search_dirs, exclude_dirs))
    descr = {'search_dirs': search_dirs,
             'exclude_dirs': exclude_dirs,
             'repo_list': repo_list}
    with open(filename, 'w') as repo_file:
        json.dump(descr, repo_file, indent=2)


def echo_list(search_dirs, exclude_dirs):
    """Print list of directories."""
    for repo_type, repo_dir, config in list_repo(search_dirs, exclude_dirs):
        if repo_type == 'git':
            if 'remote.origin.url' in config:
                origin = config['remote.origin.url']
            else:
                origin = '\033[0;31mno remote origin'
            print('\033[0;32mgit\033[0m: %s (\033[0;35m%s\033[0m)' %
                  (repo_dir, origin))
        elif repo_type == 'svn':
            print('\033[0;34msvn\033[0m: %s (\033[0;35m%s\033[0m)' %
                  (repo_dir, config))
        else:
            print('Unknown repository type:', repo_type, 'for', repo_dir)


def update(repo_list):
    """Update repositories from the given list."""
    def update_git():
        """Update a git repository."""
        call(['git', 'pull'])

    def update_svn():
        """Update a svn repository."""
        call(['svn', 'update'])

    cwd = os.getcwd()
    for repo_type, repo_dir, _ in repo_list:
        os.chdir(repo_dir)
        if repo_type == 'git':
            print("\033[1;97mUpdating \033[1;92m%s\033[1;97m...\033[0m" %
                  repo_dir)
            update_git()
        elif repo_type == 'svn':
            print("\033[1;97mUpdating \033[1;94m%s\033[1;97m...\033[0m" %
                  repo_dir)
            update_svn()
        else:
            print('Unknown repository type:', repo_type, 'for', repo_dir)
    os.chdir(cwd)


def refresh_list(filename):
    """Refresh a list of repositories."""
    with open(filename) as repo_file:
        descr = json.load(repo_file)
    if not (('search_dirs' in descr) and ('exclude_dirs' in descr)):
        raise ValueError('Invalid repository list')
    repo_list = list(list_repo(descr['search_dirs'], descr['exclude_dirs']))
    descr['repo_list'] = repo_list
    with open(filename, 'w') as repo_file:
        json.dump(descr, repo_file, indent=2)


def main():
    # getting parameters
    usage = '''%(prog)s -h
       %(prog)s -l <SEARCH_DIRS> [-e <EXCLUDE_DIRS>] [-f FILENAME]
       %(prog)s -i [INSTALL_DIR] -f FILENAME
       %(prog)s -u {-f FILENAME | -l <SEARCH_DIRS> [-e <EXCLUDE_DIRS>]}
       %(prog)s -r -f FILENAME'''
    parser = argparse.ArgumentParser(description='Manage repositories.',
                                     usage=usage)
    parser.add_argument('-l', '--list', nargs='*',
                        help='the directories to search repositories in.')
    parser.add_argument('-e', '--exclude', nargs='+', default=[],
                        help='directories to exclude from search.')
    parser.add_argument('-f', '--repo_file', nargs=1,
                        help='file listing of a repository.')
    parser.add_argument('-i', '--install', nargs='?',
                        help='install repositories')
    parser.add_argument('-u', '--update', default=False, action='store_true',
                        help='update repositories.')
    parser.add_argument('-r', '--refresh', nargs=1,
                        help='refresh list of repositories in the file.')
    args = parser.parse_args()
    # exclude only used with list
    if args.exclude and (args.list is None):
        print('exclude option is only used with list.')
        sys.exit(4)
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
        if args.update:
            print('install and update commands are not compatible.')
            sys.exit(3)
        if args.refresh is not None:
            print('install and refresh commands are not compatible.')
            sys.exit(6)
        install(args.repo_file[0], install_dir)
    # updating
    elif args.update:
        if (args.repo_file is None) == (args.list is None):
            print('update command needs either list or repo_file.')
            sys.exit(5)
        if args.repo_file is not None:
            repo_list = load_list(args.repo_file[0])
        else:
            repo_list = list_repo(args.list, args.exclude)
        update(repo_list)
    # listing
    elif args.list is not None:
        if not args.list:
            args.list = ['.']
        if args.repo_file is not None:
            save_list(args.list, args.repo_file[0], args.exclude)
        else:
            echo_list(args.list, args.exclude)
    elif args.refresh is not None:
        refresh_list(args.refresh[0])
    else:
        # TODO better message
        print('Nothing to do.')


if __name__ == '__main__':
    main()
