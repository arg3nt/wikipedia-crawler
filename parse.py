import requests


base_page_url = "https://en.wikipedia.org/api/rest_v1/page/html/"


def get_href_content(href):
        """Attempts to get the content of a webpage"""
        if href[:2] == "./":
            full_url = base_page_url + href[2:]
        else:
            return False

        res = requests.get(full_url)
        if not res.content:
            return False
        else:
            return str(res.content)


def get_hyperlinks(link):
    """Parses an HTML document and returns a list of all hyperlinks found in the document"""
    content = get_href_content(link)
    if not content:
        return []

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
