""" This script shows pylint for all Lambda Functions with ZipFile code in yaml

"""
import os
import glob
import subprocess

#import cfn_tools # pip install cfn-flip


FOLDER_PATH = '../infra/'
TMP_DIR  = '.tmp'
PYLINT_DISABLE = [
    'C0301', # Line too long
    'C0103', # Invalid name of module
    'C0114', # Missing module docstring
    'C0116', # Missing function or method docstring
    'C0303', # Trailing whitespace (trailing-whitespace)
    'W1203', # Use lazy % formatting in logging functions (logging-fstring-interpolation)
    'W1201', # Use lazy % formatting in logging functions (logging-not-lazy)
]
BANDIT_SKIP = [
    'B101', # Assert
    'B108', # Hardcoded_tmp_directory
]

def pylint(filename):
    """ call pylint """
    try:
        res = subprocess.check_output(
            f'pylint {filename} --disable {",".join(PYLINT_DISABLE)}'.split(),
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return res
    except subprocess.CalledProcessError as exc:
        return exc.stdout

def bandit(filename):
    """ call bandit """
    try:
        res = subprocess.check_output(
            f'bandit {filename} --skip {",".join(BANDIT_SKIP)}'.split(),
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if 'No issues identified.' in str(res):
            return 'Bandit: No issues identified.' # skip verbose
        return res
    except subprocess.CalledProcessError as exc:
        return exc.stdout

def tab(text, indent="\t"):
    """ returns text with a tab """
    return '\n'.join([indent + line for line in text.splitlines()])

def main():
    """ run pylint for all lambda functions """
    #file_list = glob.glob(os.path.join(FOLDER_PATH, "*.yaml"))
    file_list = glob.glob(os.path.join(FOLDER_PATH, "**/*.py"), recursive=True)
    file_list.sort(key=os.path.getmtime, reverse=True)
    for filename in file_list:
        print(f'Python File: {filename}')
        print(tab(pylint(filename)))
        print(tab(bandit(filename)))

if __name__ == '__main__':
    main()