import sqlite3

# Initializes the sqlite database by creating the database tables if they don't already exist.
# Serves as a good reference point for the system's data model
def init_sqlite(c: sqlite3.Cursor):
    c.execute('''
    CREATE TABLE IF NOT EXISTS page (
        href TEXT PRIMARY KEY,
        name TEXT,
        scanned INT DEFAULT 0,
        is_wikipedia INT,
        fullpage TEXT
    )''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS link (
        pg_from INT,
        pg_to INT,
        FOREIGN KEY (pg_from) REFERENCES page(href),
        FOREIGN KEY (pg_to) REFERENCES page(href)
    )
    ''')


# Insert new page if it doesn't already exist in the database
# NOTE: This function does NOT commit the transaction
def add_page(c: sqlite3.Cursor, href: str, name: str):
    try:
        c.execute('''
        INSERT INTO page (href, name, is_wikipedia) VALUES (?,?,?)
        ''', (href, name, href[:2] == "./"))
    except sqlite3.IntegrityError:
        # href exists already (violates unique constraint on primary key)
        return


# Add link between two existent pages to database
# NOTE: This function does NOT commit the transaction
def add_link(c: sqlite3.Cursor, pg_from: str, pg_to: str):
    try:
        c.execute('''
        INSERT INTO link (pg_from, pg_to) VALUES (?,?)
        ''', (pg_from, pg_to))
        return True
    except sqlite3.IntegrityError:
        return False


# Scan webpage contents
def scan_webpage(c: sqlite3.Cursor, href: str, content: str = ""):
    c.execute('''
    UPDATE page SET scanned=1, fullpage=? WHERE href=?
    ''', (content, href))

# Return data about total stats
def get_stats(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM page WHERE scanned=1''')
    total_pages = c.fetchone()[0]

    c.execute('''SELECT COUNT(*) FROM link''')
    total_links = c.fetchone()[0]

    return {
        'pages': total_pages,
        'links': total_links
    }


# Get a comprehensive list of unscanned webpages
def get_unscanned_pages(conn: sqlite3.Connection):
    c = conn.cursor()
    rows = c.execute('''SELECT href FROM page WHERE scanned=0''')

    return [r[0] for r in rows]
