from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import json
import urllib
import time
import threading


# configuration
PROXY = {"http" : "http://127.0.0.1:4444"}
HOSTS_FILES = ["http://www.i2p2.i2p/hosts.txt"]
NEWHOSTS_FILES = ["http://stats.i2p/cgi-bin/newhosts.txt"]
MAX_RETRIES = 6
DB_FILE = "hosts.db"

lookup_db = {}


class Handler(BaseHTTPRequestHandler):
    """Handle requests in accordance with I2P jumpservices."""
    
    def do_GET(self):        
        path = self.path.split('/')

        if(len(path) == 2 and path[1] == ''):
            self.send_response(200)
            self.end_headers()
            self.wfile.write("%d host(s) indexed\n" % (len(lookup_db)))
        elif(len(path) == 3 and path[1] == "jump" and path[2] != ''):
            if path[2] in lookup_db:
                self.send_response(301)
                self.send_header("Location", "http://" + path[2] + "/" + "?i2paddresshelper=" + lookup_db[path[2]])
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write("%s was not found in index\n" % (path[2]))
        else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write("Invalid query\n")
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


def fetch_data(url):
    """Fetch host data from I2P jump service and interpret failure modes."""
    try:
        hosts_file = urllib.urlopen(url, proxies=PROXY)
        data = hosts_file.read()
        hosts_file.close()
        if "Eepsite unknown" in data:
            print "%s through proxy %s returned \'Eepsite unknown\'" % (url, PROXY['http'])
            return False
        if "not reachable" in data:
            print "%s through proxy %s returned \'Eepsite unreachable\'" % (url, PROXY['http'])
            return False
        if "404<" in data:
            print "%s through proxy %s returned \'404\'" % (url, PROXY['http'])
            return False
        if "Banned<" in data:
            print "%s through proxy %s returned \'Banned\'" % (url, PROXY['http'])
            return False
        if data == "":
            print "%s through proxy %s returned \'""\'" % (url, PROXY['http'])
            return False
    except IOError:
        print "Proxy %s failed" % (PROXY['http'])
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
    server = ThreadedHTTPServer(('localhost', 8080), Handler)
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

