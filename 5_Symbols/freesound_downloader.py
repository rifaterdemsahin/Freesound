#!/usr/bin/env python3
"""
Freesound Music Downloader
Downloads sample music from Freesound.org for YouTube videos
"""

import os
import sys
import requests
import json
from pathlib import Path


def download_freesound_samples():
    """
    Download sample music files from Freesound.org using API token authentication.
    Uses repository secrets for authentication.
    """
    # Get API credentials from environment variables
    api_key = os.environ.get('FREESOUND_API_KEY')
    client_secret = os.environ.get('FREESOUND_CLIENT_SECRET')
    
    if not api_key:
        print("ERROR: FREESOUND_API_KEY environment variable not set")
        sys.exit(1)
    
    print("Freesound Music Downloader")
    print("=" * 50)
    print(f"API Key configured: {api_key[:10]}...")
    
    # Create downloads directory
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    # Freesound API endpoint for text search
    search_url = "https://freesound.org/apiv2/search/text/"
    
    # Search parameters - looking for music suitable for YouTube videos
    search_params = {
        'query': 'music background',
        'filter': 'duration:[10 TO 60] tag:music',  # 10-60 seconds, tagged as music
        'fields': 'id,name,previews,duration,license,username,download,url',
        'page_size': 3,  # Download 3 sample tracks
        'sort': 'rating_desc'  # Get highest rated tracks
    }
    
    # Set up authentication header
    headers = {
        'Authorization': f'Token {api_key}'
    }
    
    print(f"\nSearching for music samples...")
    print(f"Query: {search_params['query']}")
    print(f"Filter: {search_params['filter']}")
    
    try:
        # Search for sounds
        response = requests.get(search_url, params=search_params, headers=headers)
        response.raise_for_status()
        
        search_results = response.json()
        
        if search_results.get('count', 0) == 0:
            print("No sounds found matching the criteria")
            return
        
        print(f"\nFound {search_results['count']} total results")
        print(f"Downloading {len(search_results['results'])} samples...\n")
        
        # Download preview files for each result
        for idx, sound in enumerate(search_results['results'], 1):
            sound_id = sound['id']
            sound_name = sound['name']
            duration = sound.get('duration', 'unknown')
            username = sound.get('username', 'unknown')
            license_type = sound.get('license', 'unknown')
            
            print(f"[{idx}] Sound: {sound_name}")
            print(f"    ID: {sound_id}")
            print(f"    Duration: {duration}s")
            print(f"    Author: {username}")
            print(f"    License: {license_type}")
            print(f"    URL: {sound.get('url', 'N/A')}")
            
            # Download preview (HQ preview MP3)
            previews = sound.get('previews', {})
            preview_url = previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3')
            
            if preview_url:
                print(f"    Downloading preview...")
                
                try:
                    preview_response = requests.get(preview_url)
                    preview_response.raise_for_status()
                    
                    # Create safe filename
                    safe_name = "".join(c for c in sound_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = f"freesound_{sound_id}_{safe_name[:50]}.mp3"
                    filepath = downloads_dir / filename
                    
                    # Save file
                    with open(filepath, 'wb') as f:
                        f.write(preview_response.content)
                    
                    file_size = len(preview_response.content) / 1024  # KB
                    print(f"    ✓ Downloaded: {filename} ({file_size:.1f} KB)")
                    
                    # Save metadata
                    metadata = {
                        'id': sound_id,
                        'name': sound_name,
                        'duration': duration,
                        'username': username,
                        'license': license_type,
                        'url': sound.get('url'),
                        'filename': filename
                    }
                    
                    metadata_file = downloads_dir / f"{filename}.json"
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                except Exception as e:
                    print(f"    ✗ Error downloading preview: {e}")
            else:
                print(f"    ⚠ No preview available")
            
            print()
        
        print("=" * 50)
        print("Download complete!")
        print(f"Files saved to: {downloads_dir.absolute()}")
        
        # List downloaded files
        downloaded_files = list(downloads_dir.glob("*.mp3"))
        print(f"\nDownloaded {len(downloaded_files)} music samples:")
        for f in downloaded_files:
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")
        
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: API request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_freesound_samples()
