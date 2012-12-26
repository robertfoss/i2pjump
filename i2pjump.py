from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from urllib2 import HTTPError
import json
import urllib2
import time
import threading
import os


# Configuration
LISTEN_PORT = 8081
PROXY = {"http" : "http://127.0.0.1:4444"}
HOSTS_FILES = ["http://www.i2p2.i2p/hosts.txt", "http://i2host.i2p/cgi-bin/i2hostetag"]
NEWHOSTS_FILES = ["http://stats.i2p/cgi-bin/newhosts.txt"]
MAX_RETRIES = 5
DB_FILE = os.path.dirname(os.path.realpath(__file__)) + "/hosts.db"

# Global variables
lookup_db = {}
## Stats
stats = {'jump_visited': 0, 'index_visited': 0, 'hosts_visited' : 0, 'jump_not_found' : 0,
        'stats_visited' : 0, 'invalid_query_visited' : 0}

def do_jump(self, path):
    global stats
    stats['jump_visited'] += 1
    dest = path[2].split('?')
    if dest[0] in lookup_db:
        self.send_response(301)
        if len(dest) == 1:
            self.send_header("Location", "http://"+dest[0]+"/"+"?i2paddresshelper="+lookup_db[dest[0]])
        else:
            self.send_header("Location", "http://"+dest[0]+"/"+"?"+dest[1]+"&i2paddresshelper="+lookup_db[dest[0]])
        self.wfile.write("Redirecting to %s..\n" % (dest[0]))
        self.end_headers()
    else:
        stats['jump_not_found'] += 1
        self.send_response(200)
        self.end_headers()
        self.wfile.write("%s was not found in index\n" % (path[2]))

def do_hosts(self):
    global stats
    stats['hosts_visited'] += 1
    self.send_response(200)
    self.end_headers()
    for key, value in lookup_db.iteritems():
        self.wfile.write(key + "=" + value + '\n')

def do_stats(self):
    global stats
    stats['stats_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write("<!DOCTYPE html>\n<html>\n<body>\n")
    self.wfile.write("<p>%d host(s) indexed</p>\n" % (len(lookup_db)))
    self.wfile.write("<p>index visited %d times</p>\n" % (stats['index_visited']))
    self.wfile.write("<p>/stats visited %d times</p>\n" % (stats['stats_visited']))
    self.wfile.write("<p>/hosts visited %d times</p>\n" % (stats['hosts_visited']))
    pct_failure = 0 if (stats['jump_not_found'] == 0) else (100*stats['jump_not_found'] / stats['jump_visited'])
    self.wfile.write("<p>/jump/ visited %d times, not found %d%s </p>\n" % (stats['jump_visited'], pct_failure, "%"))
    self.wfile.write("<p>invalid query requested %d times</p>\n" % (stats['invalid_query_visited']))
    self.wfile.write("</body>\n</html>\n")
    
def do_index(self):
    global stats
    stats['index_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write("Hosts fetched from: %s\n" % (str(HOSTS_FILES + NEWHOSTS_FILES)))
    self.wfile.write("<br>\n<br>\n<p>Use jump service by visiting 'i2pjump.i2p/jump/JUMP_DESTINATION'</p>\n")
    self.wfile.write("\n<p>Full list of hosts available at <a href=\"/hosts\">i2pjump.i2p/hosts</a>\n")
    self.wfile.write("\n<p>Stats available at <a href=\"/stats\">i2pjump.i2p/stats</a>\n")
    self.wfile.write("<br>\n<br>\n<p>Source available at <a href=https://github.com/robertfoss/i2pjump>i2pjump@github</a></p>\n")
    self.wfile.write("</body>\n</html>\n")

def do_invalid_query(self):
    global stats
    stats['invalid_query_visited'] += 1
    self.send_response(200)
    self.end_headers()
    self.wfile.write("%s is an invalid query\n" % (self.path))

class Handler(BaseHTTPRequestHandler):
    """Handle requests in accordance with I2P jumpservices."""
    
    def do_GET(self):        
        path = self.path.split('/')
        if len(path) == 2 and path[1] == '':
            do_index(self)
        elif len(path) >=2 and path[1] == "hosts":
            do_hosts(self) 
        elif len(path) >=2 and path[1] == "stats":
            do_stats(self)
        elif len(path) >= 3 and path[1] == "jump" and path[2] != '':
            do_jump(self, path)
        else:
            do_invalid_query(self)
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class Updater(threading.Thread):
    """Periodically updates the host db."""

    def run(self):
        while(True):
            time.sleep(2*3600)
            update_db()


def load_db():
    """Load host db from DB_FILE"""
    try:    
        fp = open(DB_FILE, 'r+')
    except IOError: print "Unable to open file: %s" % (DB_FILE)
    else:
        with fp:
            try:
                global lookup_db
                lookup_db = json.load(fp)
            except ValueError: print "Unable to parse %s as json." % (DB_FILE)

def save_db():
    """Save host db to DB_FILE"""
    try:    
        fp = open(DB_FILE, 'w+')
    except IOError: print "Unable to open file: %s" % (DB_FILE)
    else:
        with fp:
            json.dump(lookup_db, fp)

def setup_config():
    proxy = urllib2.ProxyHandler(PROXY)
    opener = urllib2.build_opener(proxy)
    urllib2.install_opener(opener)

def fetch_data(url):
    """Fetch host data from I2P jump service and interpret failure modes."""
    try:
        hosts_file = urllib2.urlopen(url)
        data = hosts_file.read()
        hosts_file.close()
        if "Banned<" in data:   ## Throttled by stats.i2p
            print "%s through proxy %s returned \'Banned\'" % (url, PROXY['http'])
            return False
        if len(data) == 0:      ## Connection failed
            print "%s through proxy %s returned no data" % (url, PROXY['http'])
            return False
    except HTTPError, e:
        print "HTTP error-code #%d" % (e.code)
        return False
    except IOError, e:
        print "Proxy %s failed while fetching %s" % (PROXY['http'], url)
        return False
    return data

def fetch_hosts(hosts_files):
    """Fetch {"domain.i2p" : base64-addr} pairs from I2P jump service."""
    prev_db_size = len(lookup_db)
    for host in hosts_files:
        print "Fetching hosts from: %s" % (host)
        data = False
        retries = 0
        while(data == False and retries < MAX_RETRIES):
            data = fetch_data(host)
            retries += 1
        if(data == False): continue # All retries failed

        lines = data.split('\n')

        for line in lines:
            if "=" in line:
                key_val = line.split('=')
                lookup_db[key_val[0]] = key_val[1]
            else:
                print "A non-address line was downloaded: \"%s\"" % (line)

    new_db_size = len(lookup_db)
    if (new_db_size != prev_db_size):
        print("%d host(s) added to the db, totaling %d host(s)\nSaving db...") % (new_db_size - prev_db_size, new_db_size)
        save_db()


def init_db():
    """Populate the host db."""
    fetch_hosts(HOSTS_FILES+NEWHOSTS_FILES)


def update_db():
    """Update the host db."""
    fetch_hosts(NEWHOSTS_FILES)


if __name__ == '__main__':
    setup_config()

    try:
        with open(DB_FILE) as f: pass
        load_db()
        print "Loaded %d host(s) from %s" % (len(lookup_db), DB_FILE)
        if (len(lookup_db) == 0):
            raise IOError("No hosts parsed")
    except IOError as e:
        print "Fetching initial set of host"
        init_db()
    
    upd = Updater()
    server = ThreadedHTTPServer(('localhost', LISTEN_PORT), Handler)
    upd.start()
    try:
        print 'i2pjump started, use <Ctrl-C> to stop'
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print 'Main thread received keyboard interrupt, quitting threads.\n'
        try:
            upd._Thread__stop()
        except:
            print('Update thread could not be terminated')

