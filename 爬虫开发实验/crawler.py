import re
import sys
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 10
MIN_REQUEST_INTERVAL = 2.0
MAX_ATTEMPTS = 3
_last_request_time = 0.0
_last_status_code = None


def _wait_for_request_slot():
    """Ensure at least two seconds between HTTP requests."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)


def _request(url: str) -> requests.Response:
    """Send one request, enforcing the request interval."""
    global _last_request_time, _last_status_code
    _wait_for_request_slot()

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)

    charset_match = re.search(
        rb"charset\s*=\s*[\"']?([^\s;\"/>]+)",
        response.content[:4096],
        re.IGNORECASE,
    )
    if charset_match:
        response.encoding = charset_match.group(1).decode("ascii", errors="ignore")

    _last_request_time = time.monotonic()
    _last_status_code = response.status_code
    return response


def _robots_allow(url: str) -> bool:
    """Check robots.txt for the target URL using requests."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(origin + '/', '/robots.txt')

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _request(robots_url)
            if response.status_code == 200:
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                return parser.can_fetch(USER_AGENT, url)

            print(f"robots.txt request failed (HTTP {response.status_code}), "
                  f"attempt {attempt}/{MAX_ATTEMPTS}")
        except requests.RequestException as exc:
            print(f"robots.txt network error: {exc}; attempt {attempt}/{MAX_ATTEMPTS}")

        if attempt < MAX_ATTEMPTS:
            time.sleep(MIN_REQUEST_INTERVAL)

    # Fail closed if robots.txt cannot be retrieved or checked.
    return False


def fetch_html(url: str) -> str:
    """Fetch a static public page and return its HTML text."""
    global _last_status_code

    if not _robots_allow(url):
        raise RuntimeError("Target URL is disallowed by robots.txt or robots.txt is unavailable")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _request(url)
            if response.status_code == 200:
                return response.text

            print(f"HTTP {response.status_code}; attempt {attempt}/{MAX_ATTEMPTS}")
        except requests.RequestException as exc:
            print(f"Network error: {exc}; attempt {attempt}/{MAX_ATTEMPTS}")

        if attempt < MAX_ATTEMPTS:
            time.sleep(MIN_REQUEST_INTERVAL)

    raise RuntimeError(
        f"Failed to fetch {url} after {MAX_ATTEMPTS} attempts "
        f"(last status: {_last_status_code})"
    )


def parse_list(html: str, base_url: str = "http://www.people.com.cn/") -> list[dict]:
    """Parse the People.com.cn 要闻 list page into news dictionaries."""
    # 页面结构（已通过请求实际 HTML 确认，不是猜测）：
    # 1. 新闻条目位于 <td class="p6"> 容器中；该容器直接包含若干 <li>。
    # 2. 每条条目的标题和详情页链接是 <li> 下的第一个 <a>；发布时间写在
    #    <li> 文本末尾，格式为“[YYYY年MM月DD日HH:MM]”。
    # 3. 当前列表页的 <li> 中没有作者/来源子标签或文本，因此 author 暂以
    #    页面所属媒体“人民网”作为保底值；若未来页面中出现“来源：xxx”，再取该文本。
    # 确定方式：抓取 /GB/59476/index.html 后检查实际标签与 li.parent 为 td.p6。
    soup = BeautifulSoup(html, "html.parser")
    result = []
    seen_links = set()

    for container in soup.select("td.p6"):
        for item in container.find_all("li", recursive=True):
            link_tag = item.find("a", href=True)
            title = link_tag.get_text(" ", strip=True) if link_tag else ""
            href = link_tag.get("href", "").strip() if link_tag else ""
            link = urljoin(base_url, href) if href else ""

            item_text = item.get_text(" ", strip=True)
            pub_time_match = re.search(
                r"(\d{4}年\d{1,2}月\d{1,2}日\d{1,2}:\d{2})",
                item_text,
            )
            pub_time = pub_time_match.group(1) if pub_time_match else ""

            author_match = re.search(r"(?:来源|作者)[：:]\s*([^\]\[]+)", item_text)
            author = author_match.group(1).strip() if author_match else "人民网"

            if not title or not link or link in seen_links:
                continue

            seen_links.add(link)
            result.append({
                "title": title,
                "pub_time": pub_time,
                "author": author,
                "link": link,
            })

    return result


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    target_url = "http://www.people.com.cn/GB/59476/index.html"

    try:
        html = fetch_html(target_url)
        news_items = parse_list(html, target_url)
        for item in news_items[:3]:
            print(item)
    except RuntimeError as exc:
        print(f"Status: {_last_status_code}")
        print(exc)
