import requests


base_page_url = "https://en.wikipedia.org/api/rest_v1/page/html/"


def get_href_content(link):
        """Attempts to get the content of a webpage"""
        link['scanned'] = True

        if link['href'][:2] == "./":
            full_url = base_page_url + link['href'][2:]
        else:
            full_url = link['href']

        res = requests.get(full_url)
        if not res.content:
            return False
        else:
            return str(res.content)


def get_hyperlinks(link):
    content = get_href_content(link)
    """Parses an HTML document and returns a list of all hyperlinks found in the document"""
    splits = content.split("<a ")

    links = []

    for raw_split in splits:
        processed = raw_split.split("href=\"")
        if len(processed) <= 1:
            # <a> tag has no href for some reason
            continue

        href = processed[1][:processed[1].find("\"")]


        processed = raw_split.split("title=\"")
        if len(processed) <= 1:
            # <a> tag has no title for some reason
            continue

        title = processed[1][:processed[1].find("\"")]


        links.append({ 'href': href, 'title': title })

    return links        
