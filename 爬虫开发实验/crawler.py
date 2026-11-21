import logging
import re
import sys
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup


class NewsCrawler:
    """Crawler for public static news lists on People.com.cn."""

    COLUMNS = ["title", "pub_time", "author", "link"]
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        base_url: str,
        delay: float = 2.0,
        max_retries: int = 3,
    ):
        if not self._is_allowed_url(base_url):
            raise ValueError("base_url 必须是人民网的 http/https 静态页面")

        try:
            self.delay = max(2.0, float(delay))
            self.max_retries = min(5, max(1, int(max_retries)))
        except (TypeError, ValueError) as exc:
            raise ValueError("delay 和 max_retries 必须为有效数值") from exc

        self.base_url = base_url
        self.timeout = 10
        self.last_request_time = 0.0
        self.last_status_code = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    @staticmethod
    def _is_allowed_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except (TypeError, ValueError):
            return False

        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc or parsed.username or parsed.password:
            return False

        hostname = (parsed.hostname or "").lower()
        return hostname == "people.com.cn" or hostname.endswith(".people.com.cn")

    def _wait_for_request_slot(self) -> None:
        elapsed = time.monotonic() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _request(self, url: str) -> requests.Response:
        if not self._is_allowed_url(url):
            raise ValueError(f"不允许请求非法或非人民网页面: {url}")

        self._wait_for_request_slot()
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
            )
        finally:
            self.last_request_time = time.monotonic()

        self.last_status_code = response.status_code
        return response

    def _robots_allow(self) -> bool:
        parsed = urlparse(self.base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = urljoin(origin + "/", "/robots.txt")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._request(robots_url)
                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                    return parser.can_fetch(self.USER_AGENT, self.base_url)

                logging.warning(
                    "robots.txt 请求返回 HTTP %s；重试 %d/%d",
                    response.status_code,
                    attempt,
                    self.max_retries,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                logging.warning(
                    "robots.txt 超时或连接失败: %s；重试 %d/%d",
                    exc,
                    attempt,
                    self.max_retries,
                )
            except requests.RequestException as exc:
                logging.warning(
                    "robots.txt 请求失败: %s；重试 %d/%d",
                    exc,
                    attempt,
                    self.max_retries,
                )

            if attempt < self.max_retries:
                time.sleep(self.delay)

        logging.error("robots.txt 检查失败，已拒绝抓取该页")
        return False

    def fetch_html(self, url: str = None) -> str:
        target_url = url or self.base_url

        if not self._is_allowed_url(target_url):
            raise ValueError("目标 URL 必须是合法的人民网页面")
        if not self._robots_allow():
            raise RuntimeError("目标 URL 被 robots.txt 禁止或 robots.txt 不可用")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._request(target_url)
                if response.status_code == 200:
                    charset_match = re.search(
                        rb"charset\s*=\s*[\"']?([^\s;\"/>]+)",
                        response.content[:4096],
                        re.IGNORECASE,
                    )
                    if charset_match:
                        response.encoding = charset_match.group(1).decode(
                            "ascii", errors="ignore"
                        )
                    return response.text

                logging.warning(
                    "HTTP %s；重试 %d/%d",
                    response.status_code,
                    attempt,
                    self.max_retries,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                logging.warning(
                    "请求超时或连接失败: %s；重试 %d/%d",
                    exc,
                    attempt,
                    self.max_retries,
                )
            except requests.RequestException as exc:
                logging.warning(
                    "网络请求失败: %s；重试 %d/%d",
                    exc,
                    attempt,
                    self.max_retries,
                )

            if attempt < self.max_retries:
                time.sleep(self.delay)

        raise RuntimeError(
            f"抓取失败，已重试 {self.max_retries} 次 "
            f"（最后状态码: {self.last_status_code}）"
        )

    def parse_list(self, html: str) -> list[dict]:
        # 页面结构（已通过实际 HTML 确认）：<td class="p6"> 为列表容器，
        # 其中直接包含 <li>；标题与详情链接位于 <li> 下的第一个 <a>，
        # 发布时间位于同一 <li> 文本末尾的 [YYYY年MM月DD日HH:MM]。
        soup = BeautifulSoup(html, "html.parser")
        result = []
        seen_links = set()

        for container in soup.select("td.p6"):
            for item in container.find_all("li", recursive=True):
                try:
                    link_tag = item.find("a", href=True)
                    title = link_tag.get_text(" ", strip=True) if link_tag else ""
                    href = link_tag.get("href", "").strip() if link_tag else ""
                    link = urljoin(self.base_url, href) if href else ""

                    if not self._is_allowed_url(link):
                        logging.warning("跳过非法详情页链接: %s", href)
                        continue

                    item_text = item.get_text(" ", strip=True)
                    pub_time_match = re.search(
                        r"(\d{4}年\d{1,2}月\d{1,2}日\d{1,2}:\d{2})",
                        item_text,
                    )
                    pub_time = pub_time_match.group(1) if pub_time_match else ""

                    author_match = re.search(
                        r"(?:来源|作者)[：:]\s*([^\]\[]+)", item_text
                    )
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
                except Exception as exc:
                    logging.warning("解析单条新闻失败，已跳过: %s", exc)

        return result

    def save_to_csv(self, rows: list[dict], path: str = "result.csv") -> int:
        dataframe = pd.DataFrame(rows, columns=self.COLUMNS)

        try:
            dataframe.to_csv(path, index=False, encoding="utf-8-sig")
            return len(dataframe)
        except (IOError, OSError) as exc:
            logging.error("写入 CSV 失败: %s", exc)
            return 0

    def run(self) -> int:
        try:
            html = self.fetch_html()
            news_items = self.parse_list(html)
            written_count = self.save_to_csv(news_items, "result.csv")
            logging.info("成功抓取 %d 条", written_count)
            return written_count
        except (RuntimeError, ValueError) as exc:
            logging.error("页面抓取失败，已跳过该页: %s", exc)
            logging.info("成功抓取 0 条")
            return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    target_url = "http://www.people.com.cn/GB/59476/index.html"

    try:
        crawler = NewsCrawler(
            base_url=target_url,
            delay=2.0,
            max_retries=3,
        )
        crawler.run()
    finally:
        time.sleep(2)
