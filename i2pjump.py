#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.error import HTTPError

import argparse
import base64
import json
import time
import threading
import os
import urllib.request

# Configuration
parser = argparse.ArgumentParser()
parser.add_argument("-l", "--host", default='127.0.0.1', help="Host to run on")
parser.add_argument("-p", "--port", default=8081, type=int, help="Port to run on")
parser.add_argument("-m", "--max-retries", default=5, type=int, help="Number of tries to fetch from external hosts")
parser.add_argument("-x", "--http-proxy", default="http://127.0.0.1:4444", help="http proxy to use")
parser.add_argument("--new-hosts", default="http://www.i2p2.i2p/hosts.txt,http://i2host.i2p/cgi-bin/i2hostetag", help="http proxy to use")
parser.add_argument("--hosts-files", default="http://stats.i2p/cgi-bin/newhosts.txt", help="http proxy to use")
parser.add_argument("--db-update-time", default=2*3600, type=int, help="How often to dump memory db to hosts.db")
args = parser.parse_args()

LISTEN_PORT = args.port
LISTEN_HOST = args.host
PROXY = {"http" : args.http_proxy}
HOSTS_FILES = args.hosts_files.split(",")
NEWHOSTS_FILES = args.new_hosts.split(",")
MAX_RETRIES = args.max_retries
BASE64_ADDR_LEN = 516
DB_FILE = os.path.dirname(os.path.realpath(__file__)) + "/hosts.db"
FAVICON_ICO = "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"

# Global variables
lookupDb = {}
# Stats
stats = {'jump_visited': 0, 'index_visited': 0, 'hosts_visited' : 0, 'jump_not_found' : 0,
         'stats_visited' : 0, 'invalid_query_visited' : 0}

def doJump(self, path):
    global stats
    stats['jump_visited'] += 1
    dest = path[2].split('?')
    if dest[0] in lookupDb:
        self.send_response(301)
        self.send_header('Content-type', 'text/html')
        if len(dest) == 1:
            self.send_header("Location", "http://"+dest[0]+"/"+"?i2paddresshelper="+lookupDb[dest[0]])
        else:
            self.send_header("Location", "http://"+dest[0]+"/"+"?"+dest[1]+"&i2paddresshelper="+lookupDb[dest[0]])
        self.output("Redirecting to %s..\n" % (dest[0]))
        self.end_headers()
    else:
        stats['jump_not_found'] += 1
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.output("%s was not found in index\n" % (path[2]))

def doHosts(self):
    global stats
    stats['hosts_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.end_headers()
    for key, value in lookupDb.items():
        self.output(key + "=" + value + '\n')

def doStats(self):
    global stats
    stats['stats_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.output("<!DOCTYPE html>\n<html>\n<body>\n")
    self.output("<p>%d host(s) indexed</p>\n" % (len(lookupDb)))
    self.output("<p>index visited %d times</p>\n" % (stats['index_visited']))
    self.output("<p>/stats visited %d times</p>\n" % (stats['stats_visited']))
    self.output("<p>/hosts visited %d times</p>\n" % (stats['hosts_visited']))
    pct_failure = 0 if (stats['jump_not_found'] == 0) else (100*stats['jump_not_found'] / stats['jump_visited'])
    self.output("<p>/jump/ visited %d times, not found %d%s </p>\n" % (stats['jump_visited'], pct_failure, "%"))
    self.output("<p>invalid query requested %d times</p>\n" % (stats['invalid_query_visited']))
    self.output("</body>\n</html>\n")
    
def doIndex(self):
    global stats
    stats['index_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.output("<!DOCTYPE html>\n<html>\n<body>\n")
    self.output("Hosts fetched from: %s\n" % (str(HOSTS_FILES + NEWHOSTS_FILES)))
    self.output("<br>\n<br>\n<p>Use jump service by visiting 'i2pjump.i2p/jump/JUMP_DESTINATION'</p>\n")
    self.output("\n<p>Full list of hosts available at <a href=\"/hosts\">i2pjump.i2p/hosts</a>\n")
    self.output("\n<p>Stats available at <a href=\"/stats\">i2pjump.i2p/stats</a>\n")
    self.output("<br>\n<br>\n<p>Source available at <a href=https://github.com/robertfoss/i2pjump>i2pjump@github</a></p>\n")
    self.output("</body>\n</html>\n")

def doFavicon(self):
    self.send_response(200)
    self.send_header('Content-type', 'image/png')
    self.end_headers()
    self.output(base64.decodestring(FAVICON_ICO))

def doInvalidQuery(self):
    global stats
    stats['invalid_query_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.output("%s is an invalid query\n" % (self.path))

class Handler(BaseHTTPRequestHandler):
    """Handle requests in accordance with I2P jumpservices."""
    
    def do_GET(self):        
        path = self.path.split('/')
        if len(path) == 2 and path[1] == '':
            doIndex(self)
        elif len(path) >=2 and path[1] == "hosts":
            doHosts(self) 
        elif len(path) >=2 and path[1] == "stats":
            doStats(self)
        elif len(path) >= 3 and path[1] == "jump" and path[2] != '':
            doJump(self, path)
        elif len(path) == 2 and path[1] == 'favicon.ico':
            doFavicon(self)
        else:
            doInvalidQuery(self)
        return

    def output(self, data):
        # Assume data is a string
        byte_arr = bytes(data, "utf8")
        self.wfile.write(byte_arr)
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class DBUpdater(threading.Thread):
    """Periodically updates the host db."""

    def run(self):
        print("[%s] Starting" % (threading.current_thread().__class__.__name__))
        while(True):
            time.sleep(args.db_update_time)
            print("[%s] Waking up.." % (threading.current_thread().__class__.__name__))
            update_db()

class DBInitializer(threading.Thread):
    """Initialize the host db."""

    def run(self):
        print("[%s] Starting" % (threading.current_thread().__class__.__name__))
        init_db()
        print("[%s] Done" % (threading.current_thread().__class__.__name__))

def loadDb():
    """Load host db from DB_FILE"""
    try:    
        fp = open(DB_FILE, 'r+')
    except IOError: print("Unable to open file: %s" % (DB_FILE))
    else:
        with fp:
            try:
                global lookupDb
                lookupDb = json.load(fp)
            except ValueError: print("Unable to parse %s as json." % (DB_FILE))

def saveDb():
    """Save host db to DB_FILE"""
    try:    
        fp = open(DB_FILE, 'w+')
    except IOError: print("Unable to open file: %s" % (DB_FILE))
    else:
        with fp:
            json.dump(lookupDb, fp)

def setupConfig():
    proxy = urllib.request.ProxyHandler(PROXY)
    opener = urllib.request.build_opener(proxy)
    urllib.request.install_opener(opener)

def fetchData(url):
    """Fetch host data from I2P jump service and interpret failure modes."""
    try:
        hosts_file = urllib.request.urlopen(url)
        data = hosts_file.read()
        hosts_file.close()
        if "Banned<" in str(data):   ## Throttled by stats.i2p
            print("%s through proxy %s returned \'Banned\'" % (url, PROXY['http']))
            return False
        if len(data) == 0:      ## Connection failed
            print("%s through proxy %s returned no data" % (url, PROXY['http']))
            return False
    except HTTPError as e:
        print("HTTP Error #%d: %s" % (e.code, url))
        return False
    except IOError as e:
        print("Proxy %s failed while fetching %s" % (PROXY['http'], url))
        return False
    return data.strip()
    
def verifyDestination(destination):
    """Verify that a destination could be valid"""
    if len(destination) < 10:
        return False
    
    if destination[-4:len(destination)] == "AAAA" or destination[-8:len(destination)] == "AEAAEAAA" or destination[-10:len(destination)] == "AEAAEAAA==":
        return True

    return False

    
def parseEntries(data):
    """Parse a blob of data as lines of key-value pairs"""
    lines = str(data).split('\n')
    
    for line in lines:
        if line[0:1] == "#":
            continue

        if "=" in line:
            key_val = line.strip().split('=', 1)

            if not verifyDestination(key_val[1]):
                print("[%s] Invalid line found: \"%s\"" % (threading.current_thread().__class__.__name__, line))
                continue

            if key_val[0] not in lookupDb:
                lookupDb[key_val[0]] = key_val[1]
        else:
            print("[%s] Invalid line found: \"%s\"" % (threading.current_thread().__class__.__name__, line))
    

def fetchHosts(hosts_files):
    """Fetch {"domain.i2p" : base64-addr} pairs from I2P jump service."""
    prev_db_size = len(lookupDb)
    for host in hosts_files:
        print("[%s] Fetching hosts from: %s" % (threading.current_thread().__class__.__name__, str(host)))
        data = False
        retries = 0
        while(data == False and retries < MAX_RETRIES):
            data = fetchData(host)
            retries += 1
        if(data == False): continue # All retries failed

        parseEntries(data)

        if (len(lookupDb) != prev_db_size):
            print("[%s] %d host(s) added to the db, totaling %d host(s). Saving db..." % (
                threading.current_thread().__class__.__name__, len(lookupDb) - prev_db_size, len(lookupDb)))
            saveDb()
        else:
            print("[%s] No new host(s) found at %s" % (threading.current_thread().__class__.__name__, host))

def fetchHostsWithoutFail(hosts_files):
    """Fetch {"domain.i2p" : base64-addr} pairs from I2P jump service, and retry failed hosts indefinitely."""
    unvisited_hosts_files = hosts_files
    while len(unvisited_hosts_files) > 0:
        unvisited_hosts_files = hosts_files
        for host in unvisited_hosts_files:
            time.sleep(5)
            prev_db_size = len(lookupDb)
            print("[%s] Fetching hosts from: %s" % (threading.current_thread().__class__.__name__, str(host)))
            data = False
            success = True
            retries = 0
            while(data == False and retries < MAX_RETRIES):
                data = fetchData(host)
                retries += 1
            if(data == False): # All retries failed
                success = False
                continue

            parseEntries(data)

            if success:
                hosts_files.remove(host)

            if (len(lookupDb) != prev_db_size):
                print("[%s] %d host(s) added to the db, totaling %d host(s). Saving db..." % (
                threading.current_thread().__class__.__name__, len(lookupDb) - prev_db_size, len(lookupDb)))
                saveDb()
            else:
                print("[%s] No new host(s) found at %s" % (threading.current_thread().__class__.__name__, host))


def init_db():
    """Populate the host db."""
    fetchHostsWithoutFail(HOSTS_FILES+NEWHOSTS_FILES)

def update_db():
    """Update the host db."""
    fetchHosts(NEWHOSTS_FILES)

if __name__ == '__main__':
    setupConfig()
    server = ThreadedHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print("[INFO] Listening on: " + LISTEN_HOST + ":" + str(LISTEN_PORT))
    
    try:
        with open(DB_FILE) as f: pass
        loadDb()
        print("[INFO] Loaded %d host(s) from %s" % (len(lookupDb), DB_FILE))
    except IOError as e:
        print("DB_FILE is not accessible")
    
    upd = DBUpdater()
    upd.start()
    init = DBInitializer()
    init.start()

    try:
        server.serve_forever()
        print("i2pjump started, use <Ctrl-C> to stop")
    except (KeyboardInterrupt, SystemExit):
        print("")
        for thread in [init,upd]:
            if thread.isAlive():
                try:
                    thread._Thread__stop()
                except:
                    print(str(thread.__class__.__name__) + ' thread could not be terminated')
                else:
                    print(str(thread.__class__.__name__) + ' thread was terminated')
