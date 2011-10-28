#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Whitespace GitHub Bot

WhitespaceBot finds trailing whitespace and destroys it, then sends you a pull
request with the cleaned code.
It also gives you a .gitignore if you didn't have one already.

"""

from __future__ import with_statement
from random import choice
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

    old_users_file = args.old_users
    old_users = load_user_list(old_users_file)

    users = args.users
    new_users = load_user_list(users)
    user = get_user(users)

    #XXX: Potential deal breaker in here!
    count = 0
    while user in old_users:
        print "We've already done that user!"
        user = get_user(users)
        count = count + 1
    if count > len(new_users):
        return

    repos = 'https://api.github.com/users/' + user + '/repos'
    r = requests.get(repos, auth=auth)

    if (r.status_code == 200):
        resp = simplejson.loads(r.content)
        topwatch = 0
        top_repo = ''
        for repo in resp:
            if repo['watchers'] > topwatch:
                top_repo = repo['name']
                topwatch = repo['watchers']
        print dir(repo)

        print "%s's most watched repo is %s with %s watchers. Forking" % (
                user,
                top_repo,
                str(topwatch))

        repo = top_repo
        print "GitHub Forking.."
        clone_url = fork_repo(user, repo)
        print "Waiting.."
        time.sleep(30)
        print "Cloning.."
        if not clone_repo(clone_url):
            return
        print "Changing branch.."
        branched = change_branch(repo)
        print "Fixing repo.."
        fixed = fix_repo(repo)
        print "Comitting.."
        commited = commit_repo(repo)
        print "Pushing.."
        pushed = push_commit(repo)
        print "Submitting pull request.."
        submitted = submit_pull_request(user, repo)
        print "Delting local repo.."
        deleted = delete_local_repo(repo)
        print "Olding user.."
        old = save_user(old_users_file, user)


def save_user(old_users_file, user):
    with open(old_users_file, "a") as f:
        f.write(user + '\n')
    return True


def load_user_list(old_users):
    text_file = open(old_users, "r")
    old = text_file.readlines()
    text_file.close()
    x = 0
    for hid in old:
        old[x] = hid.rstrip()
        x = x + 1
    return old


def get_user(users):
    text_file = open(users, "r")
    u = text_file.readlines()
    text_file.close()
    return choice(u).rstrip()


def fork_repo(user, repo):
    url = 'https://api.github.com/repos/' + user + '/' + repo + '/forks'
    auth = (settings.username, settings.password)
    r = requests.post(url, auth=auth)
    if (r.status_code == 201):
        resp = simplejson.loads(r.content)
        return resp['ssh_url']
    else:
        return None


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
            banned = ['.git', '.py', '.yaml', '.patch', '.hs', '.occ', '.md']
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
            '# Logs and databases #\n' + \
            '######################\n' + \
            '*.log\n\n' + \
            '# OS generated files #\n' + \
            '######################\n' + \
            '.DS_Store*\n' + \
            'ehthumbs.db\n' + \
            'Icon?\n' + \
            'Thumbs.db\n'
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
