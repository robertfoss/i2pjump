from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from urllib2 import HTTPError
import base64
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
BASE64_ADDR_LEN = 516
DB_FILE = os.path.dirname(os.path.realpath(__file__)) + "/hosts.db"
FAVICON_ICO = "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAD///8A////AP///wD///8AhISEeSYmJtkkJCTbKCgo1jY2Nsg6OjrEREREu1ZWVqj///8A////AP///wD///8A////AP///wD///8A////AKqqqlQhKSH/UWdS/zhGOP8kLiT/T2NP/ys2K/9cXlym////AP///wD///8A////AP///wD///8A////AP///wBRUlKufp5+/5/Hn/+Do4P/NUM1/5S6lP+Co4L/GiEa//T09An///8A////AP///wD///8A////AP///wD///8AVFdUuJO5k/+cxJz/eZd5/1NpU/+Vu5X/kLWR/xgfGf3y8vIK////AP///wD///8A////AP///wD///8A+Pj4Bjs8QctPVnf/FRcd/yILdf8tDp//STmo/0BHXP82O1L/kpKSa////wD///8A////AP///wD///8A7u7uD0pEXboXCUz/FjpD/xMre/88Af7/PQH//z0B/v8xIHz/JyFR/3BwcI7///8A////AP///wD///8A////AFhYWKYlAJv/JwCl/wshTv8ElaL/OwH3/z0B//89Af//MgHS/ykAqv8lIDXe////AP///wD///8A////AP///wDo6OgVVFJbrCIAjf8zANL/AKCd/xcYcv8fFJX/LgC9/zwB/v88Afn/DQgg9ujo6BX///8A////AP///wD///8A////AP///wB0dHSKAyMw/wDOzv8B////Af7+/wDJyP8TNIH/Fgo89ba2tkj///8A////AP///wD///8A////AP///wD///8ALDg40gHb2/8B////Af///wH///8B////Ae3t/xw8POL29vYH////AP///wD///8A////AP///wD///8AxsbGOABoaP8A/v7/AP7+/wD+/v8B/v7/Af///wH+/v8AiYn/rKysUv///wD///8A////AP///wD///8A////ALKyskwBjIz/KaOj/w8PD/8JkZH/B7S0/xQsLP8lq6v/AK+u/5eXl2f///8A////AP///wD///8A////AP///wDQ0NAuAGxs/2Ghof/R0dH/TKSk/0mpqf/Z2dn/b6Cg/wCRkf+2trZH////AP///wD///8A////AP///wD///8A////ADpISMQAtbX/JZmZ/wDZ2f8A0dH/QZ6e/wawsP8kS0vb+vr6A////wD///8A////AP///wD///8A////AP///wDY2NgmHkhI4AHHx/8B/v7/Af7+/wHU1P8UT0/qyMjINf///wD///8A////AP///wD///8A////AP///wD///8A////AOzs7BGAgIB+SGlptkZra7h4eHiG4uLiGv///wD///8A////AP///wD///8A+A8AAPgPAADwDwAA8A8AAPAPAADgBwAAwAcAAOAHAADwDwAA8A8AAPAPAADwDwAA8A8AAPAPAAD4HwAA/j8AAA=="

# Global variables
lookupDb = {}
## Stats
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
        self.wfile.write("Redirecting to %s..\n" % (dest[0]))
        self.end_headers()
    else:
        stats['jump_not_found'] += 1
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("%s was not found in index\n" % (path[2]))

def doHosts(self):
    global stats
    stats['hosts_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.end_headers()
    for key, value in lookupDb.iteritems():
        self.wfile.write(key + "=" + value + '\n')

def doStats(self):
    global stats
    stats['stats_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write("<!DOCTYPE html>\n<html>\n<body>\n")
    self.wfile.write("<p>%d host(s) indexed</p>\n" % (len(lookupDb)))
    self.wfile.write("<p>index visited %d times</p>\n" % (stats['index_visited']))
    self.wfile.write("<p>/stats visited %d times</p>\n" % (stats['stats_visited']))
    self.wfile.write("<p>/hosts visited %d times</p>\n" % (stats['hosts_visited']))
    pct_failure = 0 if (stats['jump_not_found'] == 0) else (100*stats['jump_not_found'] / stats['jump_visited'])
    self.wfile.write("<p>/jump/ visited %d times, not found %d%s </p>\n" % (stats['jump_visited'], pct_failure, "%"))
    self.wfile.write("<p>invalid query requested %d times</p>\n" % (stats['invalid_query_visited']))
    self.wfile.write("</body>\n</html>\n")
    
def doIndex(self):
    global stats
    stats['index_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write("<!DOCTYPE html>\n<html>\n<body>\n")
    self.wfile.write("Hosts fetched from: %s\n" % (str(HOSTS_FILES + NEWHOSTS_FILES)))
    self.wfile.write("<br>\n<br>\n<p>Use jump service by visiting 'i2pjump.i2p/jump/JUMP_DESTINATION'</p>\n")
    self.wfile.write("\n<p>Full list of hosts available at <a href=\"/hosts\">i2pjump.i2p/hosts</a>\n")
    self.wfile.write("\n<p>Stats available at <a href=\"/stats\">i2pjump.i2p/stats</a>\n")
    self.wfile.write("<br>\n<br>\n<p>Source available at <a href=https://github.com/robertfoss/i2pjump>i2pjump@github</a></p>\n")
    self.wfile.write("</body>\n</html>\n")

def doFavicon(self):
    self.send_response(200)
    self.send_header('Content-type', 'image/x-icon')
    self.end_headers()
    self.wfile.write(base64.decodestring(FAVICON_ICO))

def doInvalidQuery(self):
    global stats
    stats['invalid_query_visited'] += 1
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write("%s is an invalid query\n" % (self.path))

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

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class DBUpdater(threading.Thread):
    """Periodically updates the host db."""

    def run(self):
        print "[%s] Starting" % (threading.current_thread().__class__.__name__)
        while(True):
            time.sleep(2*3600)
            print "[%s] Waking up.." % (threading.current_thread().__class__.__name__)
            update_db()

class DBInitializer(threading.Thread):
    """Initialize the host db."""

    def run(self):
        print "[%s] Starting" % (threading.current_thread().__class__.__name__)
        init_db()
        print "[%s] Done" % (threading.current_thread().__class__.__name__)

def loadDb():
    """Load host db from DB_FILE"""
    try:    
        fp = open(DB_FILE, 'r+')
    except IOError: print "Unable to open file: %s" % (DB_FILE)
    else:
        with fp:
            try:
                global lookupDb
                lookupDb = json.load(fp)
            except ValueError: print "Unable to parse %s as json." % (DB_FILE)

def saveDb():
    """Save host db to DB_FILE"""
    try:    
        fp = open(DB_FILE, 'w+')
    except IOError: print "Unable to open file: %s" % (DB_FILE)
    else:
        with fp:
            json.dump(lookupDb, fp)

def setupConfig():
    proxy = urllib2.ProxyHandler(PROXY)
    opener = urllib2.build_opener(proxy)
    urllib2.install_opener(opener)

def fetchData(url):
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
        print "HTTP Error #%d: %s" % (e.code, url)
        return False
    except IOError, e:
        print "Proxy %s failed while fetching %s" % (PROXY['http'], url)
        return False
    return data.strip()
    
def verifyDestination(destination):
    """Verify that a destination could be valid"""
    if len(destination) < 10:
        return False
    
    if destination[-4:len(destination)] == "AAAA":
        return True
       
    if destination[-10:len(destination)] == "AEAAEAAA==":
        return True

    return False

    
def parseEntries(data):
    """Parse a blob of data as lines of key-value pairs"""
    lines = data.split('\n')
    
    for line in lines:
        if line[0:1] == "#":
            continue

        if "=" in line:
            key_val = line.strip().split('=', 1)

            if not verifyDestination(key_val[1]):
                print "[%s] Invalid line found: \"%s\"" % (threading.current_thread().__class__.__name__, line)
                continue

            if key_val[0] not in lookupDb:
                lookupDb[key_val[0]] = key_val[1]
        else:
            print "[%s] Invalid line found: \"%s\"" % (threading.current_thread().__class__.__name__, line)
    

def fetchHosts(hosts_files):
    """Fetch {"domain.i2p" : base64-addr} pairs from I2P jump service."""
    prev_db_size = len(lookupDb)
    for host in hosts_files:
        print "[%s] Fetching hosts from: %s" % (threading.current_thread().__class__.__name__, str(host))
        data = False
        retries = 0
        while(data == False and retries < MAX_RETRIES):
            data = fetchData(host)
            retries += 1
        if(data == False): continue # All retries failed

        parseEntries(data)

        if (len(lookupDb) != prev_db_size):
            print "[%s] %d host(s) added to the db, totaling %d host(s). Saving db..." % (
                threading.current_thread().__class__.__name__, len(lookupDb) - prev_db_size, len(lookupDb))
            saveDb()
        else:
            print "[%s] No new host(s) found at %s" % (threading.current_thread().__class__.__name__, host)

def fetchHostsWithoutFail(hosts_files):
    """Fetch {"domain.i2p" : base64-addr} pairs from I2P jump service, and retry failed hosts indefinitely."""
    unvisited_hosts_files = hosts_files
    while len(unvisited_hosts_files) > 0:
        unvisited_hosts_files = hosts_files
        for host in unvisited_hosts_files:
            prev_db_size = len(lookupDb)
            print "[%s] Fetching hosts from: %s" % (threading.current_thread().__class__.__name__, str(host))
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
                print "[%s] %d host(s) added to the db, totaling %d host(s). Saving db..." % (
                threading.current_thread().__class__.__name__, len(lookupDb) - prev_db_size, len(lookupDb))
                saveDb()
            else:
                print "[%s] No new host(s) found at %s" % (threading.current_thread().__class__.__name__, host)

def init_db():
    """Populate the host db."""
    fetchHostsWithoutFail(HOSTS_FILES+NEWHOSTS_FILES)

def update_db():
    """Update the host db."""
    fetchHosts(NEWHOSTS_FILES)

if __name__ == '__main__':
    setupConfig()
    server = ThreadedHTTPServer(('localhost', LISTEN_PORT), Handler)
    
    try:
        with open(DB_FILE) as f: pass
        loadDb()
        print "Loaded %d host(s) from %s" % (len(lookupDb), DB_FILE)
    except IOError as e:
        print "DB_FILE is not accessible"
    
    upd = DBUpdater()
    upd.start()
    init = DBInitializer()
    init.start()

    try:
        server.serve_forever()
        print "i2pjump started, use <Ctrl-C> to stop"
    except (KeyboardInterrupt, SystemExit):
        print ""
        for thread in [init,upd]:
            if thread.isAlive():
                try:
                    thread._Thread__stop()
                except:
                    print(str(thread.__class__.__name__) + ' thread could not be terminated')
                else:
                    print(str(thread.__class__.__name__) + ' thread was terminated')
