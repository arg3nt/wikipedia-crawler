# wikipedia-crawler

A multithreaded python web crawler that mostly uses built-in libraries. Downloads and stores
the links between all webpages in English Wikipedia.

## Major libraries used

* [queue](https://docs.python.org/3/library/queue.html)
* [threading](https://docs.python.org/3/library/threading.html)
* [requests](https://pypi.org/project/requests/)
* [sqlite3](https://docs.python.org/3/library/sqlite3.html)

## Architecture

The main system is composed of two queues, the 'fetch queue' and the 'database queue'. Each queue has a set of threads which are responsible for processing their items. These threads generally take items from their own queue, then add items to the other queue.

### The Fetch Queue

The fetch queue contains a list of URLs. This queue is processed by a group of threads ("fetch workers"). The number of active fetch workers depends on the length of the database queue. The more items are in the database queue, the fewer fetch workers there are. The fewer items are in the database queue, the more workers there are. This prevents the database queue from getting too long and taking up excess memory. The general algorithm for the fetch workers is as follows:

1. Pull a URL from the queue
2. Attempt to get the webpage via Wikipedia API
3. If the webpage request was successful, parse the webpage to get a list of hyperlinks
4. Add data about the webpage and its hyperlinks to the database queue
5. Repeat from step 1

Note: the fetch workers will terminate gracefully when the main thread receives a SIGTERM.

### The Database Queue

The database queue contains a list of dictionaries. Each dictionary contains a list of all the links that a particular page has to other pages. The database queue is currently served by a single thread, the database worker. The database worker's job is to store data about the webpages and their links in the database so that they're easy to access later. The general algorithm for the database worker is as follows:

1. Pull a dict from the queue
2. Mark the webpage as scanned.
3. For each link in the webpage dict:
    1. Attempt to add the link to the database
    2. If inserting the link fails due to violating a foreign key constraint:
        1. Create a new page object in the database
        2. Add the link to the database
        3. Add the href for the destination to the fetch queue.

Like the fetch workers, the database worker also handles SIGTERMs gracefully.

### The Main Thread

The main thread is responsible for managing the application. If a partially complete sqlite database is not found, the main thread creates a database, then starts off the wikipedia crawler from the philosophy page. Otherwise, if a partially complete database is found, the main thread gets a list of all unscanned pages from the database, loads them into the fetch queue, then starts the fetch workers and the database worker. While the fetch workers and database worker are running, the main thread monitors the size of the fetch queue and adjusts the number of fetch workers accordingly.
