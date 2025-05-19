import os
import json
import re
import time
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort, Response
import simplified_scraper as scraper

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "songsofpraise_secret_key")

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Routes
@app.route('/')
def index():
    """Homepage with categories and recently scraped songs"""
    try:
        # Load categories if they exist
        if os.path.exists('data/categories.json'):
            with open('data/categories.json', 'r', encoding='utf-8') as f:
                categories = json.load(f)
        else:
            categories = []
        
        # Load songs if they exist
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
                # Sort by most recently added
                songs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                recent_songs = songs[:10]  # Show only the 10 most recent songs
        else:
            recent_songs = []
            
        return render_template('index.html', categories=categories, recent_songs=recent_songs)
    except Exception as e:
        logger.error(f"Error on homepage: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('index.html', categories=[], recent_songs=[])

@app.route('/search')
def search():
    """Search songs by title or content"""
    query = request.args.get('q', '').strip().lower()
    
    if not query:
        return render_template('search.html', songs=[], query='')
    
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
                
            # Filter songs based on search query
            results = [song for song in songs if 
                      query in song.get('title', '').lower() or 
                      query in song.get('content', '').lower() or
                      query in song.get('lyrics', '').lower()]
            
            return render_template('search.html', songs=results, query=query)
        else:
            flash("No songs data available. Please scrape songs first.", "warning")
            return render_template('search.html', songs=[], query=query)
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        flash(f"An error occurred during search: {str(e)}", "danger")
        return render_template('search.html', songs=[], query=query)

@app.route('/song/<int:song_id>')
def view_song(song_id):
    """View a specific song"""
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
            
            # Find the song with the given ID
            song = next((s for s in songs if s.get('id') == song_id), None)
            
            if song:
                # Find next and previous songs based on ID
                sorted_songs = sorted(songs, key=lambda x: x.get('id', 0))
                
                # Find current index in sorted list
                current_index = None
                for i, s in enumerate(sorted_songs):
                    if s.get('id') == song_id:
                        current_index = i
                        break
                
                next_song = None
                prev_song = None
                
                if current_index is not None:
                    if current_index < len(sorted_songs) - 1:  # Not the last song
                        next_song = sorted_songs[current_index + 1]
                    if current_index > 0:  # Not the first song
                        prev_song = sorted_songs[current_index - 1]
                
                # Find related songs in the same category
                related_songs = []
                if song.get('categories'):
                    for s in songs:
                        if s.get('id') != song_id and s.get('categories'):  # Skip current song
                            if any(cat in song.get('categories', []) for cat in s.get('categories', [])):
                                related_songs.append(s)
                    
                    # Limit to 5 related songs and sort by title
                    related_songs = sorted(related_songs[:5], key=lambda x: x.get('title', '').lower())
                
                return render_template(
                    'song.html', 
                    song=song,
                    next_song=next_song,
                    prev_song=prev_song,
                    related_songs=related_songs
                )
            else:
                flash(f"Song with ID {song_id} not found", "warning")
                return redirect(url_for('index'))
        else:
            flash("No songs data available. Please scrape songs first.", "warning")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error viewing song {song_id}: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/category/<category_name>')
def view_category(category_name):
    """View songs in a specific category"""
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
            
            # Filter songs by category
            category_songs = [s for s in songs if category_name.lower() in [c.lower() for c in s.get('categories', [])]]
            
            return render_template('search.html', songs=category_songs, 
                                  query='', category=category_name)
        else:
            flash("No songs data available. Please scrape songs first.", "warning")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error viewing category {category_name}: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('index'))

# API routes
@app.route('/results')
def results():
    """Show results of the most recent scraping operation"""
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
                
            # Sort by most recently added
            songs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            return render_template('results.html', songs=songs)
        else:
            flash("No songs data available. Please scrape songs first.", "warning")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error showing results: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/history')
def history():
    """Show history of scraping sessions"""
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
            
            # Group songs by timestamp (day)
            from datetime import datetime
            history_data = {}
            
            for song in songs:
                timestamp = song.get('timestamp', 0)
                if timestamp == 0:
                    continue
                    
                # Convert timestamp to date string
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                
                if date_str not in history_data:
                    history_data[date_str] = []
                    
                history_data[date_str].append(song)
            
            # Format the data for the template
            history_sessions = []
            for date, session_songs in sorted(history_data.items(), reverse=True):
                history_sessions.append({
                    'date': date,
                    'songs': sorted(session_songs, key=lambda x: x.get('title', '').lower())
                })
            
            return render_template('history.html', history=history_sessions)
        else:
            flash("No history data available. Please scrape songs first.", "warning")
            return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error showing history: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint to trigger scraping process"""
    try:
        # Get the URL from the request, with proper error handling
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        if not url:
            url = 'https://songsofpraise.in/'  # Default URL
        
        # Validate URL
        if "songsofpraise.in" not in url:
            return jsonify({
                'success': False,
                'message': "URL must be from songsofpraise.in domain for safety reasons."
            }), 400
            
        # Check if we should follow index links
        follow_links = data.get('follow_links', False)

        # Set a reasonable limit for songs to prevent timeout issues
        max_songs = 10  # Limit to 10 songs per scrape to avoid timeouts
        
        # Start scraping with timeout protection
        result = scraper.scrape_site(url, max_songs, follow_links)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f"Scraped {result['songs_count']} songs from {result['categories_count']} categories",
                'songs_count': result['songs_count'],
                'categories_count': result['categories_count'],
                'redirect_url': url_for('results')  # Add redirect URL to results page
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
    except Exception as e:
        logger.error(f"API scrape error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"An error occurred during scraping. Please try a more specific URL."
        }), 500

@app.route('/api/songs', methods=['GET'])
def api_songs():
    """API endpoint to get all songs"""
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
            return jsonify(songs)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"API get songs error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/categories', methods=['GET'])
def api_categories():
    """API endpoint to get all categories"""
    try:
        if os.path.exists('data/categories.json'):
            with open('data/categories.json', 'r', encoding='utf-8') as f:
                categories = json.load(f)
            return jsonify(categories)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"API get categories error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/songs/<int:song_id>', methods=['GET', 'PUT'])
def api_get_song(song_id):
    """API endpoint to get or update a specific song"""
    try:
        if not os.path.exists('data/songs.json'):
            return jsonify({
                'success': False,
                'message': "No songs data available"
            }), 404
            
        with open('data/songs.json', 'r', encoding='utf-8') as f:
            songs = json.load(f)
        
        # Find the song and its index
        song_index = None
        for i, song in enumerate(songs):
            if song.get('id') == song_id:
                song_index = i
                break
                
        if song_index is None:
            return jsonify({
                'success': False,
                'message': f"Song with ID {song_id} not found"
            }), 404
        
        # GET request - return the song
        if request.method == 'GET':
            return jsonify(songs[song_index])
        
        # PUT request - update the song
        if request.method == 'PUT':
            data = request.get_json(silent=True) or {}
            
            # Update song fields
            if 'title' in data and data['title']:
                songs[song_index]['title'] = data['title']
                
            if 'content' in data and data['content']:
                songs[song_index]['content'] = data['content']
                # Update lyrics by removing chords (simple approach)
                songs[song_index]['lyrics'] = re.sub(r'\b([A-G][#b]?(?:maj|min|m|sus|aug|dim|add)?(?:\d+)?(?:\/[A-G][#b]?)?)\b', '', data['content'])
                
            if 'categories' in data:
                songs[song_index]['categories'] = data['categories']
            
            # Update timestamp
            songs[song_index]['timestamp'] = int(time.time())
            
            # Save updated songs
            with open('data/songs.json', 'w', encoding='utf-8') as f:
                json.dump(songs, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': 'Song updated successfully',
                'song': songs[song_index]
            })
            
    except Exception as e:
        logger.error(f"API song operation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"An error occurred: {str(e)}"
        }), 500

@app.route('/api/search', methods=['GET'])
def api_search():
    """API endpoint to search for songs"""
    query = request.args.get('q', '').strip().lower()
    
    if not query:
        return jsonify([])
    
    try:
        if os.path.exists('data/songs.json'):
            with open('data/songs.json', 'r', encoding='utf-8') as f:
                songs = json.load(f)
                
            # Filter songs based on search query
            results = [song for song in songs if 
                      query in song.get('title', '').lower() or 
                      query in song.get('content', '').lower() or
                      query in song.get('lyrics', '').lower()]
            
            return jsonify(results)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"API search error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"An error occurred: {str(e)}"
        }), 500

# Error handlers
@app.route('/api/download-all', methods=['GET'])
def api_download_all():
    """API endpoint to download all songs as a text file"""
    try:
        if not os.path.exists('data/songs.json'):
            return jsonify({
                'success': False,
                'message': "No songs data available"
            }), 404
            
        with open('data/songs.json', 'r', encoding='utf-8') as f:
            songs = json.load(f)
        
        # Create a text file with all songs
        all_songs_text = ""
        
        for song in songs:
            all_songs_text += f"Title: {song.get('title', 'Untitled')}\n"
            all_songs_text += f"URL: {song.get('url', 'No URL')}\n"
            
            if song.get('categories'):
                all_songs_text += f"Categories: {', '.join(song.get('categories', []))}\n"
                
            all_songs_text += "\n" + song.get('content', '') + "\n\n"
            all_songs_text += "-" * 80 + "\n\n"
        
        # Return as a downloadable file
        response = Response(all_songs_text, mimetype='text/plain')
        response.headers["Content-Disposition"] = "attachment; filename=all_songs.txt"
        return response
        
    except Exception as e:
        logger.error(f"API download all error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"An error occurred: {str(e)}"
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error occurred'), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
