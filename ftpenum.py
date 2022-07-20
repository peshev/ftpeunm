import sys
from ftplib import FTP
import re
from calendar import month_abbr
import argparse

entry_regex = re.compile(
    r"(?P<type>[ld-])(?P<permissions>(?:[r-][w-][xs-]){3})\s+"
    r"(?P<asd>\d+)\s+"
    r"(?P<owner>\d+)\s+"
    r"(?P<group>\d+)\s+"
    r"(?P<size>\d+)\s+"
    rf"(?P<date>(?:{'|'.join(month_abbr[1:])})\s+\d+\s+(\d+|\d+:\d+))\s+"
    r"(?P<entry>.+)")
link_regex = re.compile(r"(?P<source>.+)\s+->\s+(?P<target>.+)")
entry_types = ['l', 'd', '-']

ftp = FTP()
links = {}


def recurse(dir):
    print(f"Entering {dir}", file=sys.stderr)
    entries = []
    ftp.retrlines(f"LIST -a {dir}", entries.append)  # list directory contents
    entries = [entry_regex.match(e).groupdict() for e in entries]
    directories = []
    for e in entries:
        assert e["type"] in entry_types
        if e["type"] == "l":
            link = link_regex.match(e["entry"]).groupdict()
            links[dir.rstrip("/") + "/" + link["source"]] = link["target"]
        else:
            if e["entry"] == "..":
                assert e["type"] == "d"
            else:
                e["path"] = dir
                if e["entry"] == ".":
                    assert e["type"] == "d"
                else:
                    e["path"] = e["path"].rstrip("/") + "/" + e["entry"]
                    if e["type"] == "d":
                        directories.append(e)
                    else:
                        yield e
    for d in directories:  # In order to do breadth-first
        yield from recurse(d["path"])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", "--host", help="The hostname or IP address of the FTP server to connect to",
                        required=True)
    parser.add_argument("-P", "--port", help="The port the FTP server is listening on",
                        type=int, default=21)
    parser.add_argument("-u", "--username", help="Username for FTP server login ",
                        default=None)
    parser.add_argument("-p", "--password", help="Password for FTP server login",
                        default=None)
    parser.add_argument("-d", "--basedir", help="Base directory to start the enumeration from",
                        default="/")
    parser.add_argument("-U", "--uid", help="Check whether any files are writable by a user with that UID",
                        type=int, default=None)
    parser.add_argument("-G", "--gid", help="Check whether any files are writable by a group with that GID",
                        type=int, default=None)

    args = parser.parse_args()
    ftp.connect(args.host, args.port)
    ftp.login(args.username, args.password)

    for e in recurse(args.basedir):
        writable = False
        if args.uid is not None and int(e["owner"]) == args.uid and e["permissions"][0 + 1] == "w":
            writable = True
        if args.gid is not None and int(e["group"]) == args.gid and e["permissions"][1 + 1] == "w":
            writable = True
        if e["permissions"][2 + 1] == "w":
            writable = True
        if writable:
            print(e["path"] + ("/" if e["type"] == "d" else ""))
    ftp.quit()
