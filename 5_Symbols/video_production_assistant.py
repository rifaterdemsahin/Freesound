#!/usr/bin/env python3
"""
Video Production Assistant - Music & Sound Effects Scorer
Analyzes music requirements and downloads scored matches from Freesound.org
"""

import os
import sys
import re
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Tuple

load_dotenv()


class MusicRequirement:
    """Represents a music track requirement from the production document"""

    def __init__(self, track_num: int, title: str, time_range: str,
                 genre: str, mood: str, bpm: str, instruments: str,
                 duration: float = None):
        self.track_num = track_num
        self.title = title
        self.time_range = time_range
        self.genre = genre
        self.mood = mood
        self.bpm = bpm
        self.instruments = instruments
        self.duration = duration

    def get_search_query(self) -> str:
        """Generate search query from music requirements"""
        # Focus on genre-specific terms for better matches
        genre_lower = self.genre.lower()

        # Primary genre keywords
        if 'orchestral' in genre_lower:
            return 'orchestral cinematic'
        elif 'electronic' in genre_lower and 'pop' in genre_lower:
            return 'electronic music loop'
        elif 'electronic' in genre_lower:
            return 'electronic music'
        elif 'industrial' in genre_lower:
            return 'industrial electronic'
        elif 'progressive' in genre_lower:
            return 'progressive music'
        elif 'tech' in genre_lower or 'corporate' in genre_lower:
            return 'corporate tech music'
        elif 'epic' in genre_lower:
            return 'epic music'
        else:
            # Fallback: use first few genre words
            words = genre_lower.split()[:2]
            return ' '.join(words) if words else 'music'

    def get_bpm_range(self) -> Tuple[int, int]:
        """Extract BPM range from requirement"""
        try:
            if '-' in self.bpm:
                bpm_parts = self.bpm.split('-')
                return (int(bpm_parts[0]), int(bpm_parts[1]))
            else:
                bpm = int(self.bpm)
                return (bpm - 5, bpm + 5)
        except:
            return (80, 140)  # Default range

    def score_match(self, sound_data: Dict) -> float:
        """Score how well a sound matches this requirement (0-100)"""
        score = 0.0

        # Get sound metadata
        name = sound_data.get('name', '').lower()
        tags = [t.lower() for t in sound_data.get('tags', [])]
        description = sound_data.get('description', '').lower()
        duration = sound_data.get('duration', 0)
        avg_rating = sound_data.get('avg_rating', 0)
        num_ratings = sound_data.get('num_ratings', 0)

        # Genre matching (25 points)
        genre_keywords = self.genre.lower().split()
        for keyword in genre_keywords:
            if keyword in name or keyword in tags or keyword in description:
                score += 5
        score = min(score, 25)  # Cap at 25

        # Mood matching (25 points)
        mood_keywords = self.mood.lower().replace(',', ' ').split()
        for keyword in mood_keywords:
            if keyword in name or keyword in tags or keyword in description:
                score += 4
        score = min(score, 50)  # Cap at 50 total

        # Instrument matching (15 points)
        inst_keywords = self.instruments.lower().replace(',', ' ').split()
        for keyword in inst_keywords:
            if keyword in name or keyword in tags or keyword in description:
                score += 3
        score = min(score, 65)  # Cap at 65 total

        # Duration matching (10 points)
        if self.duration and duration > 0:
            duration_diff = abs(self.duration - duration)
            if duration_diff < 5:
                score += 10
            elif duration_diff < 10:
                score += 7
            elif duration_diff < 20:
                score += 4

        # Rating quality (10 points)
        if avg_rating > 0:
            # Weighted by number of ratings
            weight = min(num_ratings / 10, 1.0)  # Max weight at 10+ ratings
            score += (avg_rating / 5.0) * 10 * weight

        # License preference (5 points) - prefer CC0
        license_name = sound_data.get('license', '')
        if 'Creative Commons 0' in license_name or 'CC0' in license_name:
            score += 5
        elif 'Attribution' in license_name:
            score += 3

        return min(score, 100)


class SoundEffectRequirement:
    """Represents a sound effect requirement"""

    def __init__(self, category: str, effects: List[str]):
        self.category = category
        self.effects = effects

    def score_match(self, sound_data: Dict, effect_name: str) -> float:
        """Score how well a sound matches this effect requirement"""
        score = 0.0

        name = sound_data.get('name', '').lower()
        tags = [t.lower() for t in sound_data.get('tags', [])]
        description = sound_data.get('description', '').lower()
        avg_rating = sound_data.get('avg_rating', 0)

        effect_keywords = effect_name.lower().split()

        # Exact name match (40 points)
        if all(kw in name for kw in effect_keywords):
            score += 40
        elif any(kw in name for kw in effect_keywords):
            score += 20

        # Tag matching (30 points)
        tag_matches = sum(1 for kw in effect_keywords if any(kw in tag for tag in tags))
        score += min(tag_matches * 10, 30)

        # Description matching (15 points)
        desc_matches = sum(1 for kw in effect_keywords if kw in description)
        score += min(desc_matches * 5, 15)

        # Quality score (15 points)
        score += (avg_rating / 5.0) * 15

        return min(score, 100)


class VideoProductionAssistant:
    """Main assistant for scoring and downloading music/SFX"""

    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.api_key = os.environ.get('FREESOUND_API_KEY')

        if not self.api_key:
            print("ERROR: FREESOUND_API_KEY not set in environment")
            sys.exit(1)

        self.headers = {'Authorization': f'Token {self.api_key}'}
        self.base_url = "https://freesound.org/apiv2"

        # Create subdirectories in output
        self.music_dir = output_dir / "music_tracks"
        self.sfx_dir = output_dir / "sound_effects"
        self.music_dir.mkdir(exist_ok=True)
        self.sfx_dir.mkdir(exist_ok=True)

    def parse_music_requirements(self) -> List[MusicRequirement]:
        """Parse source_music.md to extract track requirements"""
        music_file = self.input_dir / "source_music.md"

        if not music_file.exists():
            print(f"ERROR: {music_file} not found")
            return []

        with open(music_file, 'r') as f:
            content = f.read()

        requirements = []

        # Find all track sections
        track_pattern = r'### Track (\d+): (.+?)\n\*\*Time:\*\* (.+?)\n- \*\*Genre:\*\* (.+?)\n- \*\*Mood:\*\* (.+?)\n- \*\*BPM:\*\* (.+?)\n- \*\*Instruments:\*\* (.+?)\n'

        matches = re.finditer(track_pattern, content)

        for match in matches:
            track_num = int(match.group(1))
            title = match.group(2).strip()
            time_range = match.group(3).strip()
            genre = match.group(4).strip()
            mood = match.group(5).strip()
            bpm = match.group(6).strip()
            instruments = match.group(7).strip()

            # Calculate duration from time range
            time_parts = time_range.split(' - ')
            if len(time_parts) == 2:
                duration = self._parse_duration(time_parts[0], time_parts[1])
            else:
                duration = 30  # Default

            req = MusicRequirement(
                track_num=track_num,
                title=title,
                time_range=time_range,
                genre=genre,
                mood=mood,
                bpm=bpm,
                instruments=instruments,
                duration=duration
            )
            requirements.append(req)

        return requirements

    def _parse_duration(self, start_time: str, end_time: str) -> float:
        """Calculate duration in seconds from time strings"""
        try:
            def time_to_seconds(t):
                parts = t.split(':')
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

            return time_to_seconds(end_time) - time_to_seconds(start_time)
        except:
            return 30

    def parse_sfx_requirements(self) -> List[SoundEffectRequirement]:
        """Parse sound effects from source_music.md"""
        music_file = self.input_dir / "source_music.md"

        if not music_file.exists():
            return []

        with open(music_file, 'r') as f:
            content = f.read()

        requirements = []

        # Find sound effects section
        sfx_section = re.search(r'## Sound Effects Library(.+?)(?=##|$)', content, re.DOTALL)

        if not sfx_section:
            return []

        sfx_content = sfx_section.group(1)

        # Find categories
        category_pattern = r'### (.+?)\n((?:- \[ \] .+?\n)+)'

        for match in re.finditer(category_pattern, sfx_content):
            category = match.group(1).strip()
            effects_text = match.group(2)

            # Extract individual effects
            effects = re.findall(r'- \[ \] (.+)', effects_text)

            requirements.append(SoundEffectRequirement(category, effects))

        return requirements

    def search_freesound(self, query: str, filters: str = "", page_size: int = 15) -> List[Dict]:
        """Search Freesound API"""
        search_url = f"{self.base_url}/search/text/"

        params = {
            'query': query,
            'fields': 'id,name,tags,description,duration,previews,license,avg_rating,num_ratings,username,url',
            'page_size': page_size,
            'sort': 'rating_desc'
        }

        if filters:
            params['filter'] = filters

        try:
            response = requests.get(search_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def download_sound(self, sound_data: Dict, output_dir: Path, prefix: str = "") -> bool:
        """Download sound preview"""
        try:
            sound_id = sound_data['id']
            sound_name = sound_data['name']

            # Get preview URL
            previews = sound_data.get('previews', {})
            preview_url = previews.get('preview-hq-mp3') or previews.get('preview-lq-mp3')

            if not preview_url:
                return False

            # Download file
            response = requests.get(preview_url)
            response.raise_for_status()

            # Create filename
            safe_name = re.sub(r'[^\w\s-]', '', sound_name)
            safe_name = re.sub(r'[-\s]+', '_', safe_name)
            safe_name = safe_name.strip('_')[:50]

            if prefix:
                filename = f"{prefix}_{sound_id}_{safe_name}.mp3"
            else:
                filename = f"freesound_{sound_id}_{safe_name}.mp3"

            filepath = output_dir / filename

            with open(filepath, 'wb') as f:
                f.write(response.content)

            # Save metadata
            metadata = {
                'id': sound_id,
                'name': sound_name,
                'duration': sound_data.get('duration'),
                'tags': sound_data.get('tags', []),
                'description': sound_data.get('description', ''),
                'username': sound_data.get('username'),
                'license': sound_data.get('license'),
                'url': sound_data.get('url'),
                'avg_rating': sound_data.get('avg_rating', 0),
                'num_ratings': sound_data.get('num_ratings', 0),
                'filename': filename
            }

            metadata_file = output_dir / f"{filename}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            file_size = len(response.content) / 1024
            print(f"    ✓ Downloaded: {filename} ({file_size:.1f} KB)")

            return True

        except Exception as e:
            print(f"    ✗ Download error: {e}")
            return False

    def process_music_tracks(self, top_n: int = 3):
        """Process music track requirements and download top matches"""
        print("\n" + "=" * 70)
        print("MUSIC TRACKS - Scoring & Download")
        print("=" * 70)

        requirements = self.parse_music_requirements()

        if not requirements:
            print("No music requirements found")
            return

        print(f"\nFound {len(requirements)} music track requirements\n")

        for req in requirements:
            print(f"\n{'─' * 70}")
            print(f"Track {req.track_num}: {req.title}")
            print(f"{'─' * 70}")
            print(f"Time: {req.time_range}")
            print(f"Genre: {req.genre}")
            print(f"Mood: {req.mood}")
            print(f"BPM: {req.bpm}")
            print(f"Instruments: {req.instruments}")

            # Generate search query
            query = req.get_search_query()
            print(f"\nSearch Query: {query}")

            # Search Freesound - Use broader duration range for better results
            bpm_min, bpm_max = req.get_bpm_range()

            # Start with broad search, then narrow down with scoring
            filters = "tag:music"

            # For shorter tracks (< 60s), add duration filter
            if req.duration and req.duration < 60:
                filters = f"duration:[10 TO 120] tag:music"
            # For longer tracks, look for loops and longer pieces
            elif req.duration and req.duration >= 60:
                filters = f"duration:[30 TO 300] tag:music OR tag:loop"

            print(f"Filters: {filters}")
            print("\nSearching Freesound...")

            results = self.search_freesound(query, filters, page_size=20)

            if not results:
                print("No results found")
                continue

            # Score all results
            scored_results = []
            for sound in results:
                score = req.score_match(sound)
                scored_results.append((score, sound))

            # Sort by score
            scored_results.sort(reverse=True, key=lambda x: x[0])

            # Show top matches
            print(f"\nTop {min(top_n, len(scored_results))} matches:")
            for i, (score, sound) in enumerate(scored_results[:top_n], 1):
                print(f"\n  [{i}] Score: {score:.1f}/100")
                print(f"      Name: {sound['name']}")
                print(f"      Duration: {sound.get('duration', 'N/A')}s")
                print(f"      Rating: {sound.get('avg_rating', 0):.1f}/5 ({sound.get('num_ratings', 0)} ratings)")
                print(f"      License: {sound.get('license', 'N/A')}")
                print(f"      Tags: {', '.join(sound.get('tags', [])[:5])}")

            # Download top matches
            print(f"\nDownloading top {top_n} matches...")
            for i, (score, sound) in enumerate(scored_results[:top_n], 1):
                prefix = f"track{req.track_num:02d}_match{i}"
                self.download_sound(sound, self.music_dir, prefix)

            # Save scoring report
            report_file = self.music_dir / f"track{req.track_num:02d}_scoring_report.json"
            report = {
                'track_number': req.track_num,
                'title': req.title,
                'requirements': {
                    'genre': req.genre,
                    'mood': req.mood,
                    'bpm': req.bpm,
                    'instruments': req.instruments,
                    'duration': req.duration
                },
                'search_query': query,
                'top_matches': [
                    {
                        'rank': i + 1,
                        'score': score,
                        'sound_id': sound['id'],
                        'name': sound['name'],
                        'url': sound.get('url')
                    }
                    for i, (score, sound) in enumerate(scored_results[:top_n])
                ]
            }

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

    def process_sound_effects(self, top_n: int = 2):
        """Process sound effect requirements and download top matches"""
        print("\n" + "=" * 70)
        print("SOUND EFFECTS - Scoring & Download")
        print("=" * 70)

        requirements = self.parse_sfx_requirements()

        if not requirements:
            print("No sound effect requirements found")
            return

        total_effects = sum(len(req.effects) for req in requirements)
        print(f"\nFound {len(requirements)} categories with {total_effects} sound effects\n")

        for req in requirements:
            print(f"\n{'─' * 70}")
            print(f"Category: {req.category}")
            print(f"{'─' * 70}")

            category_dir = self.sfx_dir / req.category.lower().replace(' ', '_').replace('&', 'and')
            category_dir.mkdir(exist_ok=True)

            # Process each effect in category
            for effect in req.effects[:5]:  # Limit to first 5 per category
                print(f"\n  Effect: {effect}")

                # Search
                results = self.search_freesound(effect, page_size=10)

                if not results:
                    print(f"    No results found")
                    continue

                # Score results
                scored_results = []
                for sound in results:
                    score = req.score_match(sound, effect)
                    scored_results.append((score, sound))

                scored_results.sort(reverse=True, key=lambda x: x[0])

                # Show top match
                if scored_results:
                    score, sound = scored_results[0]
                    print(f"    Best match: {sound['name']} (Score: {score:.1f}/100)")

                    # Download top matches
                    for i, (score, sound) in enumerate(scored_results[:top_n], 1):
                        safe_effect = re.sub(r'[^\w\s-]', '', effect)
                        safe_effect = re.sub(r'[-\s]+', '_', safe_effect)
                        prefix = f"sfx_{safe_effect[:30]}_match{i}"
                        self.download_sound(sound, category_dir, prefix)

    def generate_summary_report(self):
        """Generate overall summary report"""
        print("\n" + "=" * 70)
        print("DOWNLOAD SUMMARY")
        print("=" * 70)

        # Count music files
        music_files = list(self.music_dir.glob("*.mp3"))
        music_size = sum(f.stat().st_size for f in music_files) / (1024 * 1024)

        # Count SFX files
        sfx_files = list(self.sfx_dir.glob("**/*.mp3"))
        sfx_size = sum(f.stat().st_size for f in sfx_files) / (1024 * 1024)

        print(f"\nMusic Tracks: {len(music_files)} files ({music_size:.2f} MB)")
        print(f"Sound Effects: {len(sfx_files)} files ({sfx_size:.2f} MB)")
        print(f"Total: {len(music_files) + len(sfx_files)} files ({music_size + sfx_size:.2f} MB)")

        print(f"\nOutput Directories:")
        print(f"  Music: {self.music_dir}")
        print(f"  SFX: {self.sfx_dir}")

        print("\n" + "=" * 70)


def main():
    """Main execution"""
    print("VIDEO PRODUCTION ASSISTANT")
    print("Music & Sound Effects Scorer and Downloader")
    print("=" * 70)

    # Set up paths
    input_dir = Path("/Users/rifaterdemsahin/projects/Freesound/3_Simulation/downloads/2026-07/input")
    output_dir = Path("/Users/rifaterdemsahin/projects/Freesound/3_Simulation/downloads/2026-07/output")

    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    # Create assistant
    assistant = VideoProductionAssistant(input_dir, output_dir)

    # Process music tracks (download top 3 matches per track)
    assistant.process_music_tracks(top_n=3)

    # Process sound effects (download top 2 matches per effect)
    assistant.process_sound_effects(top_n=2)

    # Generate summary
    assistant.generate_summary_report()

    print("\nProcessing complete!")


if __name__ == "__main__":
    main()
