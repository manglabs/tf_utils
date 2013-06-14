#!/usr/bin/env python

"""
Compile our app's less files into CSS. Very strictly only does:
  <app>/static/less/<app>.less -> cached/css/<app>.css
"""


import subprocess
from os.path import join, exists
from optparse import OptionParser
import webstart


def _less2css(less_fn, css_fn, include_path=None):
    print "Compiling '%s' to '%s'" % (less_fn, css_fn)
    args = ["lessc", "-x", less_fn, css_fn]
    if include_path:
        args.insert(1, "--include-path=%s" % include_path)
    subprocess.call(args)

def _get_less_files(root_dir, include_path=None):
    for app_name, app in webstart.app.blueprints.items():
        less_fn = "%(root_dir)s/%(app_name)s/static/%(app_name)s.less" \
            % (dict(root_dir=root_dir, app_name=app_name))
        if exists(less_fn):
            css_fn = "%s/cache/css/%s.css" % (root_dir, app_name)
            _less2css(less_fn, css_fn, include_path=include_path)
        else:
            print "No less file for app '%s' exists at '%s'" % (app_name, less_fn)

def main():
    parser = OptionParser("%prog [--out_dir cached] [--root_dir .] [--include_path static/less/")
    parser.add_option("--out_dir", action="store", default="cache")
    parser.add_option("--root_dir", action="store", default=".")
    parser.add_option("--include_path", action="store", default="static/less")
    (options, args) = parser.parse_args()
    _get_less_files(options.root_dir, options.include_path)

if __name__ == '__main__':
    main()


