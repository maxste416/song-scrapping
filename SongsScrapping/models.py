from datetime import datetime
from typing import Dict, List, Any, Optional

class Song:
    """
    Represents a song with lyrics and chords
    """
    def __init__(self, 
                 id: int, 
                 url: str, 
                 title: str, 
                 content: str,
                 content_html: str = "",
                 lyrics: str = "",
                 categories: List[str] = None,
                 timestamp: int = None):
        self.id = id
        self.url = url
        self.title = title
        self.content = content
        self.content_html = content_html
        self.lyrics = lyrics
        self.categories = categories or []
        self.timestamp = timestamp or int(datetime.now().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the song to a dictionary for JSON serialization"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'content': self.content,
            'content_html': self.content_html,
            'lyrics': self.lyrics,
            'categories': self.categories,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Song':
        """Create a song instance from a dictionary"""
        return cls(
            id=data.get('id', 0),
            url=data.get('url', ''),
            title=data.get('title', 'Unknown'),
            content=data.get('content', ''),
            content_html=data.get('content_html', ''),
            lyrics=data.get('lyrics', ''),
            categories=data.get('categories', []),
            timestamp=data.get('timestamp', int(datetime.now().timestamp()))
        )


class Category:
    """
    Represents a song category
    """
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
    
    def to_dict(self) -> Dict[str, str]:
        """Convert the category to a dictionary for JSON serialization"""
        return {
            'name': self.name,
            'url': self.url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Category':
        """Create a category instance from a dictionary"""
        return cls(
            name=data.get('name', 'Unknown'),
            url=data.get('url', '')
        )
