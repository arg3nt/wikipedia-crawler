from threading import Thread
from queue import Queue, Empty

import datetime
import requests
import sqlite3
import signal
import parse
import time
import db


class ThreadKiller:
    """This class handles SIGTERM and tells the program it's time to quit"""
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        print("\nQuitting now...")
        self.kill_now = True


def fetch_worker(fetch_q: Queue, db_q: Queue, killer: ThreadKiller, t_kill: list):
    """This is the worker function executed by threads that are responsible for fetching webpage data from Wikipedia"""
    while True:
        if killer.kill_now or t_kill[0]:
            return

        href = fetch_q.get()
        db_q.put({
            'from': href,
            'links': parse.get_hyperlinks(href)
        })
        fetch_q.task_done()


def db_worker(fetch_q: Queue, db_q: Queue, dbname: str, stats: dict, killer: ThreadKiller):
    """This is the worker function that's responsible for storing results to the local database"""
    conn = sqlite3.connect(dbname)
    conn.execute('PRAGMA foreign_keys=1')
    c = conn.cursor()

    start = datetime.datetime.now()
    one_sec = datetime.timedelta(seconds=1)
    while True:
        if killer.kill_now:
            conn.commit()
            return

        ld = db_q.get() # ld = link data (see fetch_worker for format)

        # Mark webpage as scanned
        db.scan_webpage(c, ld['from'])
        stats['pages'] += 1

        for link in ld['links']:
            # Skip links we don't care about
            if any([link['href'][:2] != "./", "#cite" in link['href'], "./Special:BookSources" in link['href']]):
                continue
            
            # Attempt to add link to db (will fail when the webpage has never been seen before)
            if not db.add_link(c, ld['from'], link['href']):
                # If we failed, it's because the page does not yet exist in the database
                # Inform the fetch workers that the page needs to be fetched if it belongs to wikipedia
                fetch_q.put(link['href'])

                # Add page, then link, to database
                db.add_page(c, link['href'], link['title'])
                db.add_link(c, ld['from'], link['href'])
            stats['links'] += 1
        
        if datetime.datetime.now() - start > one_sec:
            # commit once every second
            print("%s pages scanned, %s total links. fq: %s, dbq: %s" % (stats['pages'], stats['links'], fetch_q.qsize(), db_q.qsize()))
            start = datetime.datetime.now()
            conn.commit()

        db_q.task_done()
        

if __name__ == '__main__':
    # Step 1: initialize the queues

    # The fetch queue stores a list of webpages which need to be scanned
    # This queue is initially populated by the main thread to kick things off, then becomes populated by the database queue after the crawler gets going
    fetch_q = Queue(maxsize=0)

    # The database queue stores a list of webpage data which needs to be saved to the database
    # This queue is populated by the fetch queue
    db_q = Queue(maxsize=0)

    num_fetch_threads = 20
    max_fetch_threads = 40
    num_db_threads = 1 # Keep at 1 for now
    dbname = 'links.sqlite' # Update to change database name

    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    stats = {
        'links': 0,
        'pages': 0
    }
    killer = ThreadKiller()

    # Initialize DB
    db.init_sqlite(c)

    # Step 2: Attempt to load a list of unscanned webpages or start with the "Philosophy" page
    print('Checking for unscanned webpages')
    unscanned = db.get_unscanned_pages(conn)

    if unscanned:
        print('Adding unscanned pages to processing queue')
        # Add unscanned pages to processing queue (useful if resuming scan from a previous run)
        for href in unscanned:
            fetch_q.put(href)

        # Update stats
        stats = db.get_stats(conn)

    else:
        db.add_page(c, './Philosophy', 'Philosophy')
        conn.commit()
        fetch_q.put('./Philosophy')
        

    # step 3: Initialize worker threads

    # Initialize fetch threads
    print('Kicking off fetch threads')
    fetch_threads = []
    for i in range(num_fetch_threads):
        t_kill = [False]
        t = Thread(target=fetch_worker, args=(fetch_q, db_q, killer, t_kill))
        t.setDaemon(True)
        t.start()
        fetch_threads.append((t, t_kill))

    # Initialize db threads
    print('Kicking off db threads')
    for i in range(num_db_threads):
        t = Thread(target=db_worker, args=(fetch_q, db_q, dbname, stats, killer))
        t.setDaemon(True)
        t.start()


    # Step 4: Block main thread until killed or we're completely done processing
    # also monitor the fetch queue and adjust the number of queue workers accordingly
    while (not killer.kill_now) or (fetch_q.empty() and db_q.empty()):
        size = db_q.qsize()

        if size > 2000 and len(fetch_threads):
            t, t_kill = fetch_threads.pop()
            print("Fetch queue too large, stopping a fetch worker. Total threads: %s" % len(fetch_threads))
            t_kill[0] = True
        elif size < 100 and len(fetch_threads) < max_fetch_threads:
            print("Fetch queue too small, starting a fetch worker. Total threads: %s" % len(fetch_threads))
            t_kill = [False]
            t = Thread(target=fetch_worker, args=(fetch_q, db_q, killer, t_kill))
            t.setDaemon(True)
            t.start()
            fetch_threads.append((t, t_kill))
        time.sleep(3)

    conn.close()
