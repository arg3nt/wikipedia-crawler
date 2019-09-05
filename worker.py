from threadkiller import ThreadKiller
from queue import Queue
import datetime
import sqlite3
import parse
import db

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
            if any([link['href'][:2] != './', '#cite' in link['href'], './Special:BookSources' in link['href']]):
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
            print('%s pages scanned, %s total links. fq: %s, dbq: %s' % (stats['pages'], stats['links'], fetch_q.qsize(), db_q.qsize()))
            start = datetime.datetime.now()
            conn.commit()

        db_q.task_done()
