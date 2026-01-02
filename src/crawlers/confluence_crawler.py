"""
Confluence crawler for extracting documentation
"""

from atlassian import Confluence
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfluenceCrawler:
    """Crawl Confluence pages and extract content"""

    def __init__(self):
        """Initialize Confluence client"""
        if not Config.is_confluence_configured():
            logger.warning("Confluence not configured")
            self.client = None
            return

        try:
            self.client = Confluence(
                url=Config.CONFLUENCE_URL,
                username=Config.CONFLUENCE_EMAIL,
                password=Config.CONFLUENCE_API_TOKEN,
                cloud=True
            )
            logger.info("ConfluenceCrawler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Confluence client: {e}")
            self.client = None

    def crawl_space(self, space_key: str = None) -> List[Dict[str, Any]]:
        if not self.client:
            logger.warning("Confluence client not initialized")
            return []

        if not space_key:
            space_key = Config.CONFLUENCE_SPACE_KEY

        documents = []

        try:
            # Get all pages in space
            start = 0
            limit = 50

            while True:
                pages = self.client.get_all_pages_from_space(
                    space=space_key,
                    start=start,
                    limit=limit,
                    expand='body.storage,version,space'
                )

                if not pages:
                    break

                for page in pages:
                    doc = self._extract_page_content(page, space_key)
                    if doc:
                        documents.append(doc)

                start += limit

                # Break if we got less than limit (last page)
                if len(pages) < limit:
                    break

            logger.info(f"Crawled {len(documents)} pages from Confluence space '{space_key}'")

        except Exception as e:
            logger.error(f"Error crawling Confluence space: {e}")

        return documents

    def crawl_page(self, page_id: str) -> Dict[str, Any]:
        """
        Crawl a single Confluence page

        Args:
            page_id: Page ID to crawl

        Returns:
            Document with content and metadata
        """
        if not self.client:
            logger.warning("Confluence client not initialized")
            return None

        try:
            page = self.client.get_page_by_id(
                page_id=page_id,
                expand='body.storage,version,space'
            )
            return self._extract_page_content(page)

        except Exception as e:
            logger.error(f"Error crawling Confluence page {page_id}: {e}")
            return None

    def _extract_page_content(
        self,
        page: Dict[str, Any],
        space_key: str = None
    ) -> Dict[str, Any]:
        """
        Extract content from Confluence page

        Args:
            page: Page data from Confluence API
            space_key: Space key

        Returns:
            Document dictionary
        """
        try:
            page_id = page['id']
            title = page['title']
            html_content = page['body']['storage']['value']

            # Convert HTML to markdown
            markdown_content = self._html_to_markdown(html_content)

            # Combine title and content
            full_content = f"# {title}\n\n{markdown_content}"

            # Extract metadata
            metadata = {
                "page_id": page_id,
                "title": title,
                "space_key": space_key or page.get('space', {}).get('key'),
                "url": f"{Config.CONFLUENCE_URL}/wiki/spaces/{space_key}/pages/{page_id}",
                "version": page.get('version', {}).get('number', 1),
                "type": "confluence_page"
            }

            return {
                "content": full_content,
                "source": "confluence",
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error extracting page content: {e}")
            return None

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert Confluence HTML to markdown

        Args:
            html: HTML content

        Returns:
            Markdown text
        """
        try:
            # Parse HTML and extract text
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()

            # Convert to markdown
            markdown = md(str(soup), heading_style="ATX")

            return markdown.strip()

        except Exception as e:
            logger.error(f"Error converting HTML to markdown: {e}")
            return ""

    def search_pages(self, query: str, space_key: str = None) -> List[Dict[str, Any]]:
        """
        Search Confluence pages

        Args:
            query: Search query
            space_key: Optional space to limit search

        Returns:
            List of matching documents
        """
        if not self.client:
            logger.warning("Confluence client not initialized")
            return []

        try:
            cql = f'text ~ "{query}"'
            if space_key:
                cql += f' AND space = "{space_key}"'

            results = self.client.cql(cql, limit=50)

            documents = []
            for result in results.get('results', []):
                page_id = result['content']['id']
                doc = self.crawl_page(page_id)
                if doc:
                    documents.append(doc)

            logger.info(f"Found {len(documents)} pages matching '{query}'")
            return documents

        except Exception as e:
            logger.error(f"Error searching Confluence: {e}")
            return []
