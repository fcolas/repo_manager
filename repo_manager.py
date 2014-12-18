import argparse
import os


def list_repo(directory):
    "Find recursively git and svn repositories."
    for dirpath, dirnames, filenames in os.walk(directory):
        if '.git' in dirnames:
            print('git repository:', dirpath)
        elif '.svn' in dirnames:
            print('svn repository:', dirpath)


def main():
    # getting parameters
    parser = argparse.ArgumentParser(description="Manage repositories.")
    parser.add_argument('directory',
                        help='the directory to start searching in.')
    args = parser.parse_args()
    # invoking main function
    list_repo(args.directory)


if __name__ == '__main__':
    main()
