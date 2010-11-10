#!/usr/bin/python
#
# no.py - Forbid installation of certain packages on yum systems
# Copyright (C) 2010  David Cantrell <david.l.cantrell@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys

from yum.plugins import TYPE_CORE
from yum.plugins import PluginYumExit

requires_api_version = '2.6'
plugin_type = (TYPE_CORE,)

def _checkPackage(pkg, property, author, forbid):
    if getattr(pkg, property) in forbid:
        return True

    if author is not None:
        found = filter(lambda x: getattr(pkg, property).find(x) != -1, forbid)
        if len(found) > 0:
            return True

    return False

def predownload_hook(conduit):
    yb = conduit._base

    # configuration options
    c = conduit.confString("exclude", "packages", default="")
    excludePackages = filter(lambda x: x != '', c.split())
    c = conduit.confString("exclude", "authors", default="")
    excludeAuthors = filter(lambda x: x != '', c.split())

    # look for forbidden packages
    triggers = [(excludePackages, 'name', None),
                (excludeAuthors, 'committer', 'committer')]
    downloadPackages = set(conduit.getDownloadPackages())
    forbidden = {}
    found = []

    for forbid, property, author in triggers:
        if len(downloadPackages) == 0:
            break

        found = filter(lambda x: _checkPackage(x, property, author, forbid),
                       downloadPackages)

        if len(found) > 0:
            for pkg in found:
                if author is not None:
                    forbidden[pkg] = getattr(pkg, author)
                else:
                    forbidden[pkg] = author

            downloadPackages = downloadPackages.difference(found)

    # exclude by author name appearing in changelog
    if len(downloadPackages) > 0:
        for pkg in downloadPackages:
            for logentry in pkg.changelog:
                if len(logentry) < 3:
                    continue

                try:
                    author = logentry[1][:logentry[1].index('>') + 1]
                except ValueError:
                    continue

                found = filter(lambda x: author.find(x) != -1, excludeAuthors)

                if len(found) > 0:
                    forbidden[pkg] = author

    # report existence of forbidden packages and reason, then force exit
    if forbidden != {}:
        for pkg in forbidden.keys():
            author = forbidden[pkg]
            if author is None:
                sys.stderr.write("*** This system forbids installation of %s.\n" % pkg.name)
            else:
                sys.stderr.write("*** %s touched by %s, installation forbidden.\n" % (pkg.name, author))

        raise PluginYumExit
