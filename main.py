from threading import Thread
from queue import Queue, Empty
from threadkiller import ThreadKiller

import sqlite3
import worker
import parse
import time
import db


def _startFetchWorker(workers, fetch_q, db_q, killer):
    """This helper function starts a new fetch worker and adds it to the list of workers"""
    t_kill = [False]
    t = Thread(target=worker.fetch_worker, args=(fetch_q, db_q, killer, t_kill))
    t.setDaemon(True)
    t.start()
    fetch_threads.append((t, t_kill))
        

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
        _startFetchWorker(fetch_threads, fetch_q, db_q, killer)

    # Initialize db threads
    print('Kicking off db threads')
    for i in range(num_db_threads):
        t = Thread(target=worker.db_worker, args=(fetch_q, db_q, dbname, stats, killer))
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
            _startFetchWorker(fetch_threads, fetch_q, db_q, killer)

        time.sleep(3)

    conn.close()
