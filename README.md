# wikipedia-crawler
A multithreaded python web crawler that mostly uses built-in libraries. Downloads and stores 
the links between all webpages in English Wikipedia.

**NOTE**: In its current form, the script stores all its data in RAM, rendering 
it unsuitable for use with most laptops. A sqlite version is coming shortly.

## Major libraries used
* [queue](https://docs.python.org/3/library/queue.html)
* [threading](https://docs.python.org/3/library/threading.html)
* [requests](https://pypi.org/project/requests/)
* (soon) [sqlite3](https://docs.python.org/3/library/sqlite3.html)
* (for now) [pickle](https://docs.python.org/3/library/pickle.html)
