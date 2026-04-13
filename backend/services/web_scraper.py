"""Web scraping utilities for dynamic RAG document updates.

Provides functionality to:
- Scrape content from web sources (Google News, RSS feeds, HackerNews, etc.)
- Extract relevant information
- Update RAG knowledge base with fresh content
- Keep knowledge base current beyond model training date
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING_DEPS = True
except ImportError:
    HAS_SCRAPING_DEPS = False

import config

logger = logging.getLogger(__name__)


def fetch_news_from_api(query: str = None, max_results: int = 5) -> List[Dict]:
    """
    Fetch news articles from NewsAPI.
    
    Args:
        query: Search query for news (if None, uses trending topics)
        max_results: Maximum number of articles
        
    Returns:
        List of article dicts with 'title', 'description', 'url'
    """
    if not config.NEWS_API_KEY:
        logger.warning("⚠️ NEWS_API_KEY not set")
        return []
    
    try:
        # Use NewsAPI to get recent articles
        url = "https://newsapi.org/v2/everything"
        
        if query is None:
            # Get trending if no query
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'country': config.NEWS_API_COUNTRY,
                'sortBy': 'publishedAt',
                'apiKey': config.NEWS_API_KEY,
                'pageSize': min(max_results, config.NEWS_MAX_RESULTS)
            }
        else:
            params = {
                'q': query,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': config.NEWS_API_KEY,
                'pageSize': min(max_results, config.NEWS_MAX_RESULTS)
            }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        if data.get('status') == 'ok':
            for article in data.get('articles', []):
                formatted = {
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                    'published_at': article.get('publishedAt', ''),
                    'content': article.get('content', '') or article.get('description', '')
                }
                if formatted['content']:
                    articles.append(formatted)
        
        logger.info(f"📰 Fetched {len(articles)} articles about '{query}'")
        return articles
    
    except Exception as e:
        logger.error(f"Error fetching from NewsAPI: {e}")
        return []


def scrape_wikipedia_summary(topic: str) -> Optional[str]:
    """
    Scrape Wikipedia summary for a topic.
    
    Args:
        topic: Wikipedia topic to search
        
    Returns:
        Summary text or None if not found
    """
    if not HAS_SCRAPING_DEPS:
        return None
    
    try:
        url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
        headers = {'User-Agent': 'Pragna Chatbot/1.0'}
        
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract first paragraph
        paragraphs = soup.find_all('p')
        if paragraphs:
            # Skip infobox/navigation text
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 100 and not text.startswith('['):
                    logger.debug(f"📖 Scraped Wikipedia summary for: {topic}")
                    return text
        
        return None
    
    except Exception as e:
        logger.debug(f"Error scraping Wikipedia for '{topic}': {e}")
        return None


def extract_text_from_url(url: str, max_length: int = 1000) -> Optional[str]:
    """
    Extract main text content from a URL.
    
    Args:
        url: URL to scrape
        max_length: Maximum length of extracted text
        
    Returns:
        Extracted text or None if failed
    """
    if not HAS_SCRAPING_DEPS:
        return None
    
    try:
        headers = {'User-Agent': 'Pragna Chatbot/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        logger.debug(f"📰 Extracted {len(text)} characters from URL")
        return text if len(text) > 100 else None
    
    except Exception as e:
        logger.debug(f"Error extracting text from URL: {e}")
        return None


def format_article_for_rag(article: Dict) -> str:
    """
    Format news article for RAG knowledge base.
    
    Args:
        article: Article dict from news API
        
    Returns:
        Formatted text for RAG
    """
    parts = []
    
    if article.get('title'):
        parts.append(f"Title: {article['title']}")
    
    if article.get('published_at'):
        parts.append(f"Date: {article['published_at']}")
    
    if article.get('source'):
        parts.append(f"Source: {article['source']}")
    
    if article.get('content'):
        parts.append(f"Content: {article['content']}")
    
    return "\n".join(parts)


def _merge_priority_topics() -> List[str]:
    """Merge configured topic lists and remove duplicates while preserving order."""
    merged: List[str] = []
    seen = set()

    for topic in list(config.RAG_UPDATE_TOPICS) + list(getattr(config, "RAG_PRIORITY_DOMAINS", [])):
        normalized = (topic or "").strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        merged.append(normalized)

    return merged


def fetch_latest_domain_news(max_results: int = 10) -> List[str]:
    """
    Fetch latest news for configured domain topics.
    
    Args:
        max_results: Maximum articles to fetch
        
    Returns:
        List of formatted article texts
    """
    all_topics = _merge_priority_topics()
    if not all_topics:
        logger.warning("⚠️ No configured topics found for domain news update")
        return []

    # Rotate the window every run so all domains get refreshed over time.
    per_topic_docs = 1 if max_results <= 12 else 2
    topic_window = max(1, min(len(all_topics), max_results // per_topic_docs))
    start_index = datetime.now().hour % len(all_topics)
    topics = [all_topics[(start_index + i) % len(all_topics)] for i in range(topic_window)]
    
    documents = []
    
    for topic in topics:
        logger.info(f"🔍 Fetching news about '{topic}'...")
        articles = fetch_news_from_api(topic, max_results=per_topic_docs)
        
        for article in articles:
            doc = format_article_for_rag(article)
            if doc and len(doc) > 50:
                documents.append(doc)
    
    logger.info(
        "📰 Fetched %s domain news documents across %s topics",
        len(documents),
        len(topics),
    )
    return documents


def update_rag_with_web_content(query: str, max_docs: int = 3) -> bool:
    """
    Update RAG knowledge base with fresh web content.
    
    Args:
        query: Topic/query to search for
        max_docs: Maximum number of documents to add
        
    Returns:
        True if successful
    """
    from services.rag_service import get_rag_service
    
    try:
        logger.info(f"🌐 Updating RAG with web content for: {query}")
        
        # Fetch news articles
        articles = fetch_news_from_api(query, max_results=max_docs)
        documents = []
        doc_ids = []
        
        for article in articles:
            doc = format_article_for_rag(article)
            if doc and len(doc) > 50:
                documents.append(doc)
                doc_id = f"news_{query.replace(' ', '_')}_{datetime.now().isoformat()}"
                doc_ids.append(doc_id)
        
        # Add Wikipedia summary as additional context
        wiki_content = scrape_wikipedia_summary(query)
        if wiki_content:
            documents.append(wiki_content)
            doc_ids.append(f"wikipedia_{query.replace(' ', '_')}_{datetime.now().isoformat()}")
        
        if documents:
            rag = get_rag_service()
            success = rag.add_documents(documents, doc_ids)
            
            if success:
                logger.info(f"✅ RAG updated with {len(documents)} documents about '{query}'")
                return True
        else:
            logger.warning(f"⚠️ No web content found for: {query}")
            return False
    
    except Exception as e:
        logger.error(f"Error updating RAG with web content: {e}", exc_info=True)
        return False


def update_rag_with_latest_news(max_articles: int = 20) -> bool:
    """
    Update RAG with latest technology and general news.
    
    This keeps the knowledge base current with information beyond
    the model's training date (December 2023).
    
    Args:
        max_articles: Maximum articles to fetch and add
        
    Returns:
        True if successful
    """
    from services.rag_service import get_rag_service
    
    try:
        logger.info(f"📰 Updating RAG with latest news (max {max_articles} articles)...")
        
        # Fetch domain-aware news using configured topic packs.
        documents = fetch_latest_domain_news(max_articles)
        
        if documents:
            rag = get_rag_service()
            doc_ids = [f"latest_news_{i}_{datetime.now().isoformat()}" for i in range(len(documents))]
            
            success = rag.add_documents(documents, doc_ids)
            
            if success:
                logger.info(f"✅ RAG updated with {len(documents)} latest news articles")
                return True
        else:
            logger.warning("⚠️ No news articles found")
            return False
    
    except Exception as e:
        logger.error(f"Error updating RAG with latest news: {e}", exc_info=True)
        return False


def update_rag_with_custom_content(topics: List[str]) -> bool:
    """
    Update RAG with custom content for multiple topics.
    
    Args:
        topics: List of topics to scrape and add
        
    Returns:
        True if at least one topic was successfully added
    """
    success_count = 0
    
    for topic in topics:
        try:
            if update_rag_with_web_content(topic):
                success_count += 1
        except Exception as e:
            logger.error(f"Error processing topic '{topic}': {e}")
    
    return success_count > 0


def update_rag_with_topic_pack(extra_topics: Optional[List[str]] = None) -> Dict[str, object]:
    """Update RAG with the full configured topic pack plus optional extra topics."""
    base_topics = _merge_priority_topics()
    merged_topics = list(base_topics)

    if extra_topics:
        seen = {topic.lower() for topic in merged_topics}
        for topic in extra_topics:
            normalized = (topic or "").strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged_topics.append(normalized)

    success_count = 0
    failed_topics: List[str] = []
    for topic in merged_topics:
        try:
            if update_rag_with_web_content(topic, max_docs=2):
                success_count += 1
            else:
                failed_topics.append(topic)
        except Exception as exc:
            logger.error("Error updating topic pack for '%s': %s", topic, exc)
            failed_topics.append(topic)

    return {
        "total_topics": len(merged_topics),
        "successful_topics": success_count,
        "failed_topics": failed_topics,
    }
