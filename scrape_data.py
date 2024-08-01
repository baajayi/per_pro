import json
import os
import requests
import time
from typing import Optional
from typing import Tuple
from urllib.parse import urljoin, urlparse
import re
from typing import Any, cast

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter 
from bs4 import BeautifulSoup

year = 2024
month = '04'
host = 'https://www.churchofjesuschrist.org'
base_dir = 'data/raw'
bs_parser = 'html.parser'
delay_seconds = 5

if not os.path.exists(base_dir):
    os.makedirs(base_dir)
def _is_talk_url(url):
    """A talk URL has 6 components (first component is empty) and last component does not end in -session."""
    path_components = urlparse(url).path.split('/')
    return len(path_components) == 6 and not path_components[-1].endswith('-session')


def get_talk_urls(base_url, html):
    """Find all talk URLs on the page."""
    soup = BeautifulSoup(html, bs_parser)
    return [urljoin(base_url, a['href']) for a in soup.find_all('a', href=True) \
            if _is_talk_url(urljoin(base_url, a['href']))]


def get_talk_path(url):
    """Return the file path for saving the talk."""
    path_components = urlparse(url).path.split('/')
    year, month, title = path_components[3:6]
    return os.path.join(base_dir, f"{year}-{month}-{title}.json")

def get_page(
    url: str,
    delay_seconds: int = 30,
    headers: Optional[dict[str, str]] = None,
    encoding: str = "utf-8",
    timeout: int = 30,
) -> Tuple[int, str]:
    """Get page from url."""
    if headers is None:
        # make your program look like a chrome
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: B950
            "Accept-Encoding": "gzip, deflate",  # gzip, deflate, br, zstd
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Cookie": "TAsessionID=8f51490c-5611-45b6-9847-8585037a0e1b|NEW; notice_behavior=implied|us; gpv_Page=general-conference%7C2024%7C04%7C11oaks; gpv_cURL=www.churchofjesuschrist.org%2Fstudy%2Fgeneral-conference%2F2024%2F04%2F11oaks; s_ips=838; s_tp=1517; s_ppv=general-conference%257C2024%257C04%257C11oaks%2C55%2C55%2C55%2C838%2C1%2C1; AMCVS_66C5485451E56AAE0A490D45%40AdobeOrg=1; AMCV_66C5485451E56AAE0A490D45%40AdobeOrg=179643557%7CMCIDTS%7C19909%7CMCMID%7C88116570082250571280802679967931299750%7CMCAAMLH-1720711596%7C9%7CMCAAMB-1720711596%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1720113996s%7CNONE%7CvVersion%7C5.5.0; s_cc=true; s_plt=1.01; s_pltp=general-conference%7C2024%7C04%7C11oaks; adcloud={%22_les_v%22:%22c%2Cy%2Cchurchofjesuschrist.org%2C1720108596%22}; at_check=true; mbox=session#6bb5efff4aea494c8e2e9c7d3469ab29#1720108658|PC#6bb5efff4aea494c8e2e9c7d3469ab29.35_0#1783351598",
            "Pragma": "no-cache",
            "Priority": "u=0, i",
            "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",  # noqa: B950
        }
    # make the request
    response = requests.get(url, headers=headers, timeout=timeout)
    # wait 
    time.sleep(delay_seconds)
    if encoding:
        response.encoding = encoding
    return response.status_code, response.text

def save_page(path: str, url: str, html: str, encoding: str = "utf-8") -> None:
    """Save page url and html to path."""
    page_info = {
        "url": url,
        "html": html,
    }
    with open(path, "w", encoding=encoding) as f:
        json.dump(page_info, f, ensure_ascii=False, indent=2)

dir_url = f"{host}/study/general-conference/{year}/{month}?lang=eng"
# get the root page
status_code, dir_html = get_page(dir_url, delay_seconds)
if status_code != 200:
    print(f"Status code={status_code} url={dir_url}")

# get all of the talk URLs from the conference root
talk_urls = get_talk_urls(dir_url, dir_html)
print(dir_url, len(talk_urls))

for ix, talk_url in enumerate(talk_urls):
    path = get_talk_path(talk_url)
    # don't re-crawl if you've already crawled
    if os.path.exists(path):
        continue
    print("    ", path)
    status_code, talk_html = get_page(talk_url, delay_seconds)
    if status_code != 200:
        print(f"Status code={status_code} url={talk_url}")
        continue
    save_page(path, talk_url, talk_html)
file_dir = 'data/raw'

def clean(text: Any) -> str:
    """Convert text to a string and clean it."""
    if text is None:
        return ""
    if isinstance(text, Tag):
        text = text.get_text()
    if not isinstance(text, str):
        text = str(text)
    """Replace non-breaking space with normal space and remove surrounding whitespace."""
    text = text.replace(" ", " ").replace("\u200b", "").replace("\u200a", " ")
    text = re.sub(r"(\n\s*)+\n", "\n\n", text)
    text = re.sub(r" +\n", "\n", text)
    return cast(str, text.strip())

class ConferenceMarkdownConverter(MarkdownConverter):  # type: ignore
    """Create a custom MarkdownConverter."""

    def __init__(self, **kwargs: Any):
        """Initialize custom MarkdownConverter."""
        super().__init__(**kwargs)
        self.base_url = kwargs.get("base_url", "")

    def convert_a(self, el, text, convert_as_inline):  # type: ignore
        """Join hrefs with a base url."""
        if "href" in el.attrs:
            el["href"] = urljoin(self.base_url, el["href"])
        return super().convert_a(el, text, convert_as_inline)

    def convert_p(self, el, text, convert_as_inline):  # type: ignore
        """Add anchor tags to paragraphs with ids."""
        if el.has_attr("id") and len(el["id"]) > 0:
            _id = el["id"]
            text = f'<a name="{_id}"></a>{text}'  # noqa: B907
        return super().convert_p(el, text, convert_as_inline)

# Create shorthand method for custom conversion
def _to_markdown(html: str, **options: Any) -> str:
    """Convert html to markdown."""
    return cast(str, ConferenceMarkdownConverter(**options).convert(html))


# read conference talk dir
for file_name in os.listdir(file_dir):
    if file_name.endswith('.json'):  # Check if the file is a JSON file
        file_path = os.path.join(file_dir, file_name)
        with open(file_path, encoding="utf8") as f:
            data = json.load(f)
        url = data['url']
        html = data['html']
        
        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        title = clean(soup.select_one("article header h1").get_text())
        author = clean(soup.select_one("article p.author-name").get_text())
        author_role = clean(soup.select_one("article p.author-role").get_text())
        body = soup.select_one("article div.body-block")
        
        # Convert HTML body to markdown
        markdown = clean(_to_markdown(str(body), base_url=url, heading_style="ATX", strip=["script", "style"]))
        
        # Define the markdown content
        markdown_content = f"# {title}\n\n**Author:** {author}\n**Role:** {author_role}\n\n{markdown}"
        
        # Define the output file path
        output_file_path = os.path.join(file_dir, f"{os.path.splitext(file_name)[0]}.md")
        
        # Save the markdown content to a .md file
        with open(output_file_path, 'w', encoding="utf8") as md_file:
            md_file.write(markdown_content)
        
        print(f"Saved markdown to {output_file_path}")

