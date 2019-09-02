from threading import Thread
from queue import Queue, Empty

import requests
import pickle
import signal
import parse
import time

# This class handles SIGTERM and tells the program it's time to quit
class ThreadKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        print("\nQuitting now")
        self.kill_now = True


# This builds an instance of the hyperlink dictionary when it's needed
def build_hyperlink_dict(href, title):
    return {
        'href': href,
        'title': title,
        'is_wikipedia': href[:2] == "./",
        'references': [],
        'referenced_by': [],
        'scanned': False
    }


# This function is what the worker threads execute. Essentially it's responsible for pulling an item 
# from the queue, getting the webpage, and processing it
def worker(q, links, pages, killer):
    while True:
        # If the program has received SIGTERM
        if killer.kill_now:
            # empty the queue and quit once done
            # NOTE: this can take some time if there are several million items in the queue
            try:
                q.get(timeout=2)
            except Empty:
                return
            
            q.task_done()
            continue
        
        # Get the next item in the queue and save the links from the page
        # (q.get blocks until an object in the queue is available for processing. 
        #   This prevents the loop from cycling endlessly when the queue is empty)
        link = q.get()
        pages[0] += 1
        print("(links: %s, pages: %s, ratio: %.5f) Saving links for %s " % (len(links), pages[0], (pages[0]/(len(links)+1)), link['title']))
        save_links(q, link, links)

        q.task_done()



# Scans a wikipedia page for hyperlinks and adds new links to the processing queue if necessary
def save_links(q, link, links):
    if not link['is_wikipedia'] or link['scanned']:
        return

    new_links = parse.get_hyperlinks(link)
    for nl in new_links:
        if links.get(nl['href']):
            hyper = links[nl['href']]
        else:
            hyper = build_hyperlink_dict(nl['href'], nl['title'])
            links[nl['href']] = hyper
            if hyper['is_wikipedia']:
                q.put(hyper)
        
        # Add links between objects
        hyper['referenced_by'].append(link['href'])
        link['references'].append(hyper['href'])
        


if __name__ == "__main__":
    # Initialize the Queue
    q = Queue(maxsize=0)
    links = {}
    num_threads = 20
    pages = [0] # Need to pass in a list bc ints are immutable and won't exist in shared memory :/
    killer = ThreadKiller()


    # Attempt to load data from an existing save file if necessary
    # Note: long-term success of this project on computers that don't have tons of RAM will require saving to a database here
    # TODO: save data to sqlite DB instead of storing in memory
    print('Checking for existing save file')

    # Attempt to load an existing save file (if you started running this program in the past but it had to be interrupted for some reason)
    try:
        save_file = open('links.p')
        links = pickle.load(open('links.p', 'rb'))

        print("Save file found with %s links, loading in data" % len(links))
        for href, obj_dict in links.items():
            if not links[href]['scanned'] and links[href]['is_wikipedia']:
                q.put(links[href])
            else:
                pages[0] += 1
    except Exception:
        print("No valid save file, starting from beginning")
        q.put(build_hyperlink_dict("./Philosophy", "Philosophy"))


    # Initialize all the threads, which will block until something gets added to the queue
    print('Kicking off threads')
    for i in range(num_threads):
        t = Thread(target=worker, args=(q, links, pages, killer))
        t.setDaemon(True)
        t.start()

    # Wait until every item in the queue has had q.task_done for it 
    # (if we attempt to quit the program early it will empty out the queue)
    q.join()

    print("Total links:")
    print(len(links))
    print("Total pages:")
    print(pages[0])

    print("Saving results to file")

    pickle.dump(links, open('links.p', 'wb'))
