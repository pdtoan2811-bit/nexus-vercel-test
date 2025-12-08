import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_webpage(url: str):
    """
    Scrapes a webpage for its title, description, thumbnail, and text content.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Metadata
        title = None
        if soup.find("meta", property="og:title"):
            title = soup.find("meta", property="og:title")["content"]
        elif soup.title:
            title = soup.title.string
            
        description = ""
        if soup.find("meta", property="og:description"):
            description = soup.find("meta", property="og:description")["content"]
        elif soup.find("meta", {"name": "description"}):
            description = soup.find("meta", {"name": "description"})["content"]
            
        thumbnail = None
        if soup.find("meta", property="og:image"):
            thumbnail = soup.find("meta", property="og:image")["content"]
            
        # Extract Text Content (Simplistic approach)
        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return {
            "title": title or url,
            "description": description,
            "thumbnail": thumbnail,
            "content": clean_text[:50000] # Limit context window usage
        }
        
    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")
        raise e

