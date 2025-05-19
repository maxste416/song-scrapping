import os
import re
import json
import time
import logging
import requests
import trafilatura
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Constants
BASE_URL = 'https://songsofpraise.in/'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
REQUEST_DELAY = 1  # Delay between requests in seconds to avoid overloading the server

# Storage paths
SONGS_PATH = 'data/songs.json'
CATEGORIES_PATH = 'data/categories.json'


def make_request(url: str) -> Optional[requests.Response]:
    """
    Make a request to the target URL with proper headers and error handling
    """
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to {url}: {str(e)}")
        return None


def parse_song_page(url: str, song_id: int) -> Dict[str, Any]:
    """
    Parse a song page to extract title, lyrics, chords, etc.
    """
    logger.info(f"Parsing song page: {url}")
    response = make_request(url)
    
    if not response:
        return {
            'id': song_id,
            'url': url,
            'title': 'Unknown',
            'error': 'Failed to load page',
            'timestamp': int(datetime.now().timestamp())
        }
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract song title
    title_element = soup.select_one('h1.entry-title')
    title = title_element.text.strip() if title_element else 'Unknown Title'
    
    # Extract song content (lyrics and chords)
    content_element = soup.select_one('div.entry-content')
    
    if not content_element:
        return {
            'id': song_id,
            'url': url,
            'title': title,
            'error': 'No content found',
            'timestamp': int(datetime.now().timestamp())
        }
    
    # Process content to preserve formatting
    content_html = str(content_element)
    content_text = content_element.get_text('\n', strip=True)
    
    # Extract lyrics (text without chords)
    # This is a simplified approach - might need refinement based on site structure
    lyrics_lines = []
    for line in content_text.split('\n'):
        # Skip lines that are likely to be chord lines (contain mostly chord names)
        chord_pattern = r'^[A-G][m#b]?(\s+[A-G][m#b]?)*$'
        if not re.match(chord_pattern, line.strip()):
            lyrics_lines.append(line)
    
    lyrics = '\n'.join(lyrics_lines)
    
    # Extract categories if available
    categories = []
    category_elements = soup.select('a[rel="category tag"]')
    for cat_elem in category_elements:
        categories.append(cat_elem.text.strip())
    
    return {
        'id': song_id,
        'url': url,
        'title': title,
        'content': content_text,
        'content_html': content_html,
        'lyrics': lyrics,
        'categories': categories,
        'timestamp': int(datetime.now().timestamp())
    }


def extract_song_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """
    Extract song links from a page
    """
    links = []
    
    # Look for song links - adjust selectors based on actual site structure
    # This example assumes links are in article titles or post listings
    for article in soup.select('article.post'):
        title_link = article.select_one('h2.entry-title a, h1.entry-title a')
        if title_link and 'href' in title_link.attrs:
            links.append({
                'title': title_link.text.strip(),
                'url': urljoin(base_url, str(title_link['href']))
            })
    
    # In case the above selector doesn't find anything, try a more general approach
    if not links:
        for link in soup.select('a.more-link, .entry-title a, .entry-content a'):
            if 'href' in link.attrs:
                url = urljoin(base_url, str(link['href']))
                # Skip if it's a category, tag, or other non-song link
                if '/category/' in url or '/tag/' in url or 'comments' in url:
                    continue
                links.append({
                    'title': link.text.strip(),
                    'url': url
                })
    
    return links


def extract_categories(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """
    Extract category links from a page
    """
    categories = []
    
    # Look for category links in the sidebar or navigation
    for cat_link in soup.select('.widget_categories a, .nav-menu a, .cat-item a'):
        if 'href' in cat_link.attrs and '/category/' in cat_link['href']:
            categories.append({
                'name': cat_link.text.strip(),
                'url': urljoin(base_url, str(cat_link['href']))
            })
    
    return categories


def load_existing_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load existing songs and categories from JSON files
    """
    songs = []
    if os.path.exists(SONGS_PATH):
        try:
            with open(SONGS_PATH, 'r', encoding='utf-8') as f:
                songs = json.load(f)
            logger.info(f"Loaded {len(songs)} existing songs")
        except Exception as e:
            logger.error(f"Error loading songs data: {str(e)}")
    
    categories = []
    if os.path.exists(CATEGORIES_PATH):
        try:
            with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
                categories = json.load(f)
            logger.info(f"Loaded {len(categories)} existing categories")
        except Exception as e:
            logger.error(f"Error loading categories data: {str(e)}")
    
    return songs, categories


def save_data(songs: List[Dict[str, Any]], categories: List[Dict[str, Any]]) -> None:
    """
    Save songs and categories to JSON files
    """
    try:
        with open(SONGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(songs, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(songs)} songs to {SONGS_PATH}")
    except Exception as e:
        logger.error(f"Error saving songs data: {str(e)}")
    
    try:
        with open(CATEGORIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(categories)} categories to {CATEGORIES_PATH}")
    except Exception as e:
        logger.error(f"Error saving categories data: {str(e)}")


def scrape_site(start_url: str = BASE_URL, max_songs: int = 20) -> Dict[str, Any]:
    """
    Main function to scrape the site
    
    Args:
        start_url: The URL to start scraping from
        max_songs: Maximum number of songs to scrape (prevents timeout issues)
    """
    logger.info(f"Starting scrape from: {start_url}")
    
    # Load existing data
    existing_songs, existing_categories = load_existing_data()
    
    # Track URLs to avoid duplicates
    processed_urls = set(song['url'] for song in existing_songs)
    songs_to_process = []
    categories = []
    
    try:
        # Validate the URL to ensure it's from the expected domain
        if "songsofpraise.in" not in start_url:
            return {
                'success': False,
                'message': f"URL must be from songsofpraise.in domain for safety reasons."
            }
            
        # Start with the main page
        response = make_request(start_url)
        if not response:
            return {
                'success': False,
                'message': f"Failed to access the site: {start_url}"
            }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract category links
        new_categories = extract_categories(soup, BASE_URL)
        
        # Add categories that don't exist yet
        existing_category_urls = set(cat['url'] for cat in existing_categories)
        for category in new_categories:
            if category['url'] not in existing_category_urls:
                categories.append(category)
                existing_categories.append(category)
                existing_category_urls.add(category['url'])
        
        # First pass: collect song links from the main page
        song_links = extract_song_links(soup, BASE_URL)
        
        # Second pass: visit category pages to collect more song links
        for category in categories:
            logger.info(f"Processing category: {category['name']}")
            
            cat_response = make_request(category['url'])
            if not cat_response:
                logger.warning(f"Failed to access category: {category['url']}")
                continue
            
            time.sleep(REQUEST_DELAY)  # Respect rate limiting
            
            cat_soup = BeautifulSoup(cat_response.text, 'html.parser')
            cat_song_links = extract_song_links(cat_soup, BASE_URL)
            
            for link in cat_song_links:
                song_links.append(link)
            
            # Check for pagination and process additional pages
            pagination = cat_soup.select('.pagination a, .page-numbers a')
            for page_link in pagination:
                if 'href' in page_link.attrs and page_link.text.strip().isdigit():
                    page_url = urljoin(BASE_URL, str(page_link['href']))
                    
                    logger.info(f"Processing pagination page: {page_url}")
                    time.sleep(REQUEST_DELAY)  # Respect rate limiting
                    
                    page_response = make_request(page_url)
                    if not page_response:
                        logger.warning(f"Failed to access page: {page_url}")
                        continue
                    
                    page_soup = BeautifulSoup(page_response.text, 'html.parser')
                    page_song_links = extract_song_links(page_soup, BASE_URL)
                    
                    for link in page_song_links:
                        song_links.append(link)
        
        # Remove duplicates from song links
        unique_songs = {}
        for link in song_links:
            if link['url'] not in unique_songs and link['url'] not in processed_urls:
                unique_songs[link['url']] = link
        
        songs_to_process = list(unique_songs.values())
        
        # Generate a new ID for each song
        next_id = 1
        if existing_songs:
            next_id = max(song.get('id', 0) for song in existing_songs) + 1
        
        # Process each song page (up to max_songs limit)
        processed_songs = []
        songs_to_process = songs_to_process[:max_songs]  # Limit to max_songs
        
        for i, song in enumerate(songs_to_process):
            logger.info(f"Processing song {i+1}/{len(songs_to_process)}: {song['title']}")
            
            song_data = parse_song_page(song['url'], next_id)
            processed_songs.append(song_data)
            processed_urls.add(song['url'])
            next_id += 1
            
            time.sleep(REQUEST_DELAY)  # Respect rate limiting
            
            # Save periodically
            if (i + 1) % 5 == 0 or i == len(songs_to_process) - 1:  # Save more frequently
                all_songs = existing_songs + processed_songs
                save_data(all_songs, existing_categories)
                
                # Update processed songs to avoid memory issues with large datasets
                existing_songs = all_songs
                processed_songs = []
        
        # Save final data
        all_songs = existing_songs
        save_data(all_songs, existing_categories)
        
        return {
            'success': True,
            'songs_count': len(all_songs),
            'categories_count': len(existing_categories),
            'message': f"Successfully scraped {len(all_songs)} songs from {len(existing_categories)} categories"
        }
    
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        return {
            'success': False,
            'message': f"An error occurred during scraping: {str(e)}"
        }


if __name__ == "__main__":
    # Test scraping a single page
    result = scrape_site()
    print(json.dumps(result, indent=2))
