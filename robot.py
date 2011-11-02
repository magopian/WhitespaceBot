#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Whitespace GitHub Bot

WhitespaceBot finds trailing whitespace and destroys it, then sends you a pull
request with the cleaned code.
It also gives you a .gitignore if you didn't have one already.

"""

from __future__ import with_statement
import argparse
import json
import os
import requests
import settings
import shutil
import simplejson
import subprocess
import sys
import time
import urllib2


DESCRIPTION = """Whitespace annihilating GitHub robot.
By Rich Jones - Gun.io - rich@gun.io"""


def main():
    """Main entry point

    - take user name from list (make sure it's a new one)
    - get most popular repository
    - fork it - POST /repos/:user/:repo/forks
    - clone it
    - switch to the "clean" branch
    - fix it
    - commit it!
    - push it
    - submit pull req
    - save user name to the "old users" list

    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-u',
                        '--users',
                        help='A text file with usernames.',
                        default='users.txt')
    parser.add_argument('-o',
                        '--old-users',
                        help='A text file with usernames.',
                        default='old_users.txt')
    parser.add_argument('-c',
                        '--count',
                        help='The maximum number of total requests to make.',
                        default=999999)
    parser.add_argument('-v',
                        '--verbose',
                        help='Make this sucker loud? (True/False)',
                        default=True)
    args = parser.parse_args()

    auth = (settings.username, settings.password)

    user = get_user(users_file=args.users, old_users_file=args.old_users)
    if user is None:
        print "Looks like all of the users have been done! Exiting."
        return

    repos = 'https://api.github.com/users/%s/repos' % user
    r = requests.get(repos)

    if r.status_code == 200:
        resp = simplejson.loads(r.content)
        # repositories, ordered by descending watchers
        repositories = sorted([(r['watchers'], r['name']) for r in resp],
                              reverse=True)
        watchers, repo = repositories[0]

        print "%s's most watched repo is %s with %s watchers. Forking" % (
                user,
                repo,
                watchers)

        print "GitHub Forking..."
        clone_url = fork_repo(user, repo)
        print "Waiting..."
        time.sleep(30)
        print "Cloning..."
        if not clone_repo(clone_url):
            return
        print "Changing branch..."
        branched = change_branch(repo)
        print "Fixing repo..."
        fixed = fix_repo(repo)
        print "Comitting..."
        commited = commit_repo(repo)
        print "Pushing..."
        pushed = push_commit(repo)
        print "Submitting pull request..."
        submitted = submit_pull_request(user, repo)
        print "Delting local repo..."
        deleted = delete_local_repo(repo)
        print "Olding user..."
        old = save_user(args.old_users, user)
    else:
        print "Error while requesting the repositories for %s, Exiting." % user
        print "Status code: %s" % r.status_code
        print "Error message: %s" % r.content


def save_user(old_users_file, user):
    """Save user as being already processed"""
    with open(old_users_file, "a") as f:
        f.write('%s\n' % user)
    return True


def load_user_list(users_file):
    """Return a set of users loaded from a user file

    User files must contain one user per line, whitespace will be striped.

    """
    with open(users_file, 'r') as f:
        users = f.readlines()
    return set([u.strip() for u in users])


def get_user(users_file, old_users_file):
    """Get the first user not already processed"""
    old_users = load_user_list(old_users_file)
    users = load_user_list(users_file)
    new_users = users.difference(old_users)
    return new_users.pop() if new_users else None


def fork_repo(user, repo):
    """Fork the repository on GitHub"""
    url = 'https://api.github.com/repos/%s/%s/forks' % (user, repo)
    auth = (settings.username, settings.password)
    r = requests.post(url, auth=auth)
    if r.status_code == 201:
        resp = simplejson.loads(r.content)
        return resp['ssh_url']
    else:
        raise Exception("GitHub fork failed, please check credentials")


def clone_repo(clone_url):
    try:
        args = ['/usr/bin/git', 'clone', clone_url]
        p = subprocess.Popen(args)
        p.wait()
        return True
    except Exception, e:
        return False


def change_branch(repo):
    #XXX fuck this
    gitdir = os.path.join(settings.pwd, repo, ".git")
    repo = os.path.join(settings.pwd, repo)

    try:
        args = ['/usr/bin/git',
                '--git-dir',
                gitdir,
                '--work-tree',
                repo,
                'branch',
                'clean']
        p = subprocess.Popen(args)
        p.wait()
        args = ['/usr/bin/git',
                '--git-dir',
                gitdir,
                '--work-tree',
                repo,
                'checkout',
                'clean']
        p = subprocess.Popen(args)
        p.wait()
        return True
    except Exception, e:
        return False


def fix_repo(repo):
    gitdir = os.path.join(settings.pwd, repo, ".git")
    repo = os.path.join(settings.pwd, repo)
    for root, dirs, files in os.walk(repo):
        for f in files:
            path = os.path.join(root, f)

            # gotta be a way more pythonic way of doing this
            banned = ['.git',
                      '.py',
                      '.yaml',
                      '.patch',
                      '.hs',
                      '.occ',
                      '.md',
                      '.markdown',
                      '.mdown']
            cont = False
            for b in banned:
                if b in path:
                    cont = True
            if cont:
                continue

            p = subprocess.Popen(['file', '-bi', path], stdout=subprocess.PIPE)

            while True:
                o = p.stdout.readline()
                if o == '':
                    break
                #XXX: Motherfucking OSX is a super shitty and not real OS
                #XXX: and doesn't do file -bi properly
                if 'text' in o:
                    q = subprocess.Popen(['sed', '-i', 's/[ \\t]*$//', path])
                    q.wait()
                    args = ['/usr/bin/git',
                            '--git-dir',
                            gitdir,
                            '--work-tree',
                            repo,
                            'add',
                            path]
                    pee = subprocess.Popen(args)
                    pee.wait()
                if o == '' and p.poll() != None:
                    break

    git_ignore = os.path.join(repo, '.gitignore')
    if not os.path.exists(git_ignore):
        ignorefile = open(git_ignore, 'w')
        ignore = '# Compiled source #\n' + \
            '###################\n' + \
            '*.com\n' + \
            '*.class\n' + \
            '*.dll\n' + \
            '*.exe\n' + \
            '*.o\n' + \
            '*.so\n' + \
            '*.pyc\n\n' + \
            '# Numerous always-ignore extensions\n' + \
            '###################\n' + \
            '*.diff\n' + \
            '*.err\n' + \
            '*.orig\n' + \
            '*.log\n' + \
            '*.rej\n' + \
            '*.swo\n' + \
            '*.swp\n' + \
            '*.vi\n' + \
            '*~\n\n' + \
            '*.sass-cache\n' + \
            '# Folders to ignore\n' + \
            '###################\n' + \
            '.hg\n' + \
            '.svn\n' + \
            '.CVS\n' + \
            '# OS or Editor folders\n' + \
            '###################\n' + \
            '.DS_Store\n' + \
            'Icon?\n' + \
            'Thumbs.db\n' + \
            'ehthumbs.db\n' + \
            'nbproject\n' + \
            '.cache\n' + \
            '.project\n' + \
            '.settings\n' + \
            '.tmproj\n' + \
            '*.esproj\n' + \
            '*.sublime-project\n' + \
            '*.sublime-workspace\n' + \
            '# Dreamweaver added files\n' + \
            '###################\n' + \
            '_notes\n' + \
            'dwsync.xml\n' + \
            '# Komodo\n' + \
            '###################\n' + \
            '*.komodoproject\n' + \
            '.komodotools\n'
        ignorefile.write(ignore)
        ignorefile.close()
        try:
            args = ['/usr/bin/git',
                    '--git-dir',
                    gitdir,
                    '--work-tree',
                    repo,
                    'add',
                    git_ignore]
            p = subprocess.Popen(args)
            p.wait()
            return True
        except Exception, e:
            return False

    return True


def commit_repo(repo):
    gitdir = os.path.join(settings.pwd, repo, ".git")
    repo = os.path.join(settings.pwd, repo)

    try:
        message = "Remove whitespace [Gun.io WhitespaceBot]"
        args = ['/usr/bin/git',
                '--git-dir',
                gitdir,
                '--work-tree',
                repo,
                'commit',
                '-m',
                message]
        p = subprocess.Popen(args)
        p.wait()
        return True
    except Exception, e:
        print e
        return False


def push_commit(repo):
    gitdir = os.path.join(settings.pwd, repo, ".git")
    repo = os.path.join(settings.pwd, repo)
    try:
        args = ['/usr/bin/git',
                '--git-dir',
                gitdir,
                '--work-tree',
                repo,
                'push',
                'origin',
                'clean']
        p = subprocess.Popen(args)
        p.wait()
        return True
    except Exception, e:
        print e
    return False


def basic_authorization(user, password):
    s = user + ":" + password
    return "Basic " + s.encode("base64").rstrip()


def submit_pull_request(user, repo):
    auth = (settings.username, settings.password)
    url = 'https://api.github.com/repos/' + user + '/' + repo + '/pulls'
    with open('message.txt', 'r') as f:
        message = f.read()
    params = {'title': 'Hi! I cleaned up your code for you!',
              'body': message,
              'base': 'master',
              'head': 'GunioRobot:clean'}

    basic_auth = basic_authorization(settings.username, settings.password)
    req = urllib2.Request(url,
                          headers={
                              "Authorization": basic_auth,
                              "Content-Type": "application/json",
                              "Accept": "*/*",
                              "User-Agent": "WhitespaceRobot/Gunio",
                          },
                          data=json.dumps(params))
    f = urllib2.urlopen(req)
    return True


def delete_local_repo(repo):
    repo = os.path.join(settings.pwd, repo)
    try:
        shutil.rmtree(repo)
        return True
    except Exception, e:
        return False


if __name__ == '__main__':
        sys.exit(main())
