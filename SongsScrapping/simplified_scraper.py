import os
import re
import json
import logging
import trafilatura
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Constants
BASE_URL = 'https://songsofpraise.in/'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Storage paths
SONGS_PATH = 'data/songs.json'
CATEGORIES_PATH = 'data/categories.json'

def get_webpage_content(url: str) -> Optional[str]:
    """
    Get the HTML content of a webpage using trafilatura
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return downloaded
        return None
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return None

def extract_links(html_content: str, base_url: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract songs and category links from HTML content
    """
    result = {
        'songs': [],
        'categories': [],
        'index_links': []  # For links in index pages like Hindi songs list
    }
    
    if not html_content:
        return result
    
    # Parse with BeautifulSoup for link extraction
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check if this is an index page (like Hindi songs index)
    is_index_page = False
    if '/hindi/' in base_url or '/english/' in base_url or '/malayalam/' in base_url:
        is_index_page = True
    
    # Look for song links in the entry content (typically where song lists appear)
    entry_content = soup.select_one('.entry-content')
    
    # Extract song links - looking for links in articles, content blocks, etc.
    links_to_check = soup.find_all('a')
    
    # If we have entry content and this is an index page, prioritize links there
    if entry_content and is_index_page:
        links_to_check = entry_content.find_all('a') + links_to_check
    
    for link in links_to_check:
        # Skip links without href (fix for type checking)
        href = link.get('href')
        if not href:
            continue
            
        url = urljoin(base_url, str(href))
        title = link.get_text().strip()
        
        # Skip empty titles
        if not title:
            continue
            
        # Categorize links
        if '/category/' in url:
            result['categories'].append({
                'name': title,
                'url': url
            })
        elif url.startswith(BASE_URL) and not any(x in url for x in ['/tag/', '/author/', '/page/', 'comments', 'wp-content']):
            # Likely a song link if it's on the same domain and not a tag, author, etc.
            
            # If this is a song in an index page, add to index_links
            if is_index_page and entry_content and link in entry_content.find_all('a'):
                result['index_links'].append({
                    'title': title,
                    'url': url
                })
            
            # Add to regular songs as well
            result['songs'].append({
                'title': title,
                'url': url
            })
    
    return result

def extract_song_content(url: str, song_id: int) -> Dict[str, Any]:
    """
    Extract song content using trafilatura which is more reliable for content extraction
    """
    logger.info(f"Extracting content from: {url}")
    
    try:
        downloaded = get_webpage_content(url)
        if not downloaded:
            return {
                'id': song_id,
                'url': url,
                'title': 'Unknown',
                'error': 'Failed to download page',
                'timestamp': int(datetime.now().timestamp())
            }
        
        # Extract full text content
        content = trafilatura.extract(downloaded)
        if not content:
            # Fallback to standard HTML extraction
            soup = BeautifulSoup(downloaded, 'html.parser')
            title_element = soup.select_one('h1.entry-title')
            title = title_element.text.strip() if title_element else 'Unknown Title'
            
            content_element = soup.select_one('div.entry-content')
            content = content_element.get_text('\n', strip=True) if content_element else ''
            content_html = str(content_element) if content_element else ''
        else:
            # Try to extract title from HTML
            soup = BeautifulSoup(downloaded, 'html.parser')
            title_element = soup.select_one('h1.entry-title')
            title = title_element.text.strip() if title_element else 'Unknown Title'
            content_html = ''  # We don't have HTML when using trafilatura extraction
        
        # Extract categories if available
        categories = []
        soup = soup or BeautifulSoup(downloaded, 'html.parser')
        category_elements = soup.select('a[rel="category tag"]')
        for cat_elem in category_elements:
            categories.append(cat_elem.text.strip())
        
        # Separate lyrics from content (simple heuristic)
        lines = content.split('\n') if content else []
        lyrics_lines = []
        for line in lines:
            # Skip lines that are likely chord lines (contain mostly chord names)
            chord_pattern = r'^[A-G][m#b]?(\s+[A-G][m#b]?)*$'
            if not re.match(chord_pattern, line.strip()):
                lyrics_lines.append(line)
        
        lyrics = '\n'.join(lyrics_lines)
        
        return {
            'id': song_id,
            'url': url,
            'title': title,
            'content': content or '',
            'content_html': content_html,
            'lyrics': lyrics,
            'categories': categories,
            'timestamp': int(datetime.now().timestamp())
        }
        
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return {
            'id': song_id,
            'url': url,
            'title': 'Unknown',
            'error': f"Error: {str(e)}",
            'timestamp': int(datetime.now().timestamp())
        }

def load_existing_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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

def scrape_site(start_url: str = BASE_URL, max_songs: int = 10, follow_links: bool = False) -> Dict[str, Any]:
    """
    Main function to scrape the site with improved efficiency using trafilatura
    
    Args:
        start_url: The URL to start scraping from
        max_songs: Maximum number of songs to scrape
        follow_links: Whether to follow links from the index page (for Hindi, English, etc. categories)
    """
    logger.info(f"Starting scrape from: {start_url}")
    
    try:
        # Validate URL
        if "songsofpraise.in" not in start_url:
            return {
                'success': False,
                'message': "URL must be from songsofpraise.in domain for safety reasons."
            }
        
        # Load existing data
        existing_songs, existing_categories = load_existing_data()
        existing_song_urls = {song['url'] for song in existing_songs}
        existing_category_urls = {cat['url'] for cat in existing_categories}
        
        # Get the HTML content of the start URL
        html_content = get_webpage_content(start_url)
        if not html_content:
            return {
                'success': False,
                'message': f"Failed to access the site: {start_url}"
            }
        
        # Extract links from the HTML content
        extracted_links = extract_links(html_content, start_url)
        
        # Add new categories
        new_categories = []
        for category in extracted_links['categories']:
            if category['url'] not in existing_category_urls:
                new_categories.append(category)
                existing_categories.append(category)
                existing_category_urls.add(category['url'])
        
        # Prepare song URLs to process
        songs_to_process = []
        
        # If this is an index page (like Hindi songs) and follow_links is True, 
        # process the links from the index first
        if follow_links and extracted_links['index_links']:
            logger.info(f"Found {len(extracted_links['index_links'])} songs in the index page. Following these links...")
            for song in extracted_links['index_links']:
                if song['url'] not in existing_song_urls:
                    songs_to_process.append(song)
        else:
            # Regular processing of songs found on the page
            for song in extracted_links['songs']:
                if song['url'] not in existing_song_urls:
                    songs_to_process.append(song)
        
        # Limit the number of songs to process
        songs_to_process = songs_to_process[:max_songs]
        
        if not songs_to_process:
            # If no new songs found on the main page, go directly to a category page
            direct_process = True
            parsed_url = urlparse(start_url)
            if '/category/' in parsed_url.path or parsed_url.path == '/':
                # If we're already on a category page or home page, don't process directly
                direct_process = False
            
            if direct_process:
                # Process the page directly as a song page
                next_id = max([song.get('id', 0) for song in existing_songs]) + 1 if existing_songs else 1
                song_data = extract_song_content(start_url, next_id)
                
                # Check if we actually got song content
                if 'error' not in song_data:
                    existing_songs.append(song_data)
                    save_data(existing_songs, existing_categories)
                    
                    return {
                        'success': True,
                        'songs_count': len(existing_songs),
                        'categories_count': len(existing_categories),
                        'message': f"Successfully scraped 1 song from {start_url}"
                    }
                else:
                    return {
                        'success': False,
                        'message': f"Failed to extract song content from {start_url}. Error: {song_data.get('error', 'Unknown error')}"
                    }
        
        # Process each song
        new_songs_count = 0
        next_id = max([song.get('id', 0) for song in existing_songs]) + 1 if existing_songs else 1
        
        for i, song in enumerate(songs_to_process):
            logger.info(f"Processing song {i+1}/{len(songs_to_process)}: {song['title']}")
            
            # Extract content from the song page
            song_data = extract_song_content(song['url'], next_id)
            existing_songs.append(song_data)
            existing_song_urls.add(song['url'])
            next_id += 1
            new_songs_count += 1
            
            # Save periodically to avoid data loss
            if (i + 1) % 3 == 0 or i == len(songs_to_process) - 1:
                save_data(existing_songs, existing_categories)
        
        # Success message
        return {
            'success': True,
            'songs_count': len(existing_songs),
            'categories_count': len(existing_categories),
            'new_songs_count': new_songs_count,
            'message': f"Successfully scraped {new_songs_count} new songs from {start_url}"
        }
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        return {
            'success': False,
            'message': f"An error occurred during scraping: {str(e)}"
        }

if __name__ == "__main__":
    # Test scraping a single page
    result = scrape_site("https://songsofpraise.in/english/")
    print(json.dumps(result, indent=2))