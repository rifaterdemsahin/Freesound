# 5_Symbols - Core Source Code

## Purpose
Contains the main application files and core source code.

## Description
This folder houses the core source code for the Freesound automation application. It includes all the main application logic, backend services, and integration code for downloading and scoring music from Freesound.org.

## Contents
- Main application code
- Backend services
- API integrations
- Business logic
- Data models and schemas
- Core utilities and helpers
- Freesound.org integration code
- Music scoring algorithms

---

# Freesound Music Downloader

This script downloads sample music from Freesound.org for use in YouTube videos.

## Setup

### 1. Get Freesound API Credentials

1. Create an account at [Freesound.org](https://freesound.org/)
2. Apply for API credentials at [https://freesound.org/apiv2/apply](https://freesound.org/apiv2/apply)
3. You'll receive an API key (also called client_id)

### 2. Configure Environment Variables

Set your API credentials as environment variables:

```bash
export FREESOUND_API_KEY="your_api_key_here"
```

### 3. Install Dependencies

```bash
pip install requests
```

### 4. Run the Script

```bash
python 5_Symbols/freesound_downloader.py
```

## GitHub Actions Workflow

The repository includes a GitHub Actions workflow (`.github/workflows/test-freesound-download.yml`) that automatically tests downloading music samples.

### Configure Repository Secrets

In your GitHub repository, add the following secret:
- `freesound_clientid` - Your Freesound API key (this will be mapped to FREESOUND_API_KEY in the workflow)

Go to: Settings → Secrets and variables → Actions → New repository secret

**Note:** The workflow maps the `freesound_clientid` secret to the `FREESOUND_API_KEY` environment variable used by the script.

### Trigger the Workflow

The workflow runs automatically on:
- Push to `main` or `copilot/*` branches
- Pull requests to `main`
- Manual trigger via "Actions" tab

## Features

- Downloads 3 sample music tracks from Freesound.org
- Filters for background music suitable for YouTube videos
- Duration: 10-60 seconds
- Sorts by highest rating
- Downloads HQ MP3 previews
- Saves metadata (license, author, duration) for each track
- Uploads samples as GitHub Actions artifacts

## Output

Downloaded files are saved to the `downloads/` directory with:
- MP3 audio files
- JSON metadata files with licensing information

## License Compliance

Always check the license information in the metadata JSON files. Freesound hosts files under various Creative Commons licenses. Make sure to:
- Provide attribution when required
- Respect license restrictions (commercial use, derivatives, etc.)
- Link back to the original sound on Freesound.org

## Troubleshooting

### Authentication Error
- Verify your API key is correct
- Check that environment variables are properly set
- Ensure your API key is active on Freesound.org

### No Results Found
- Try adjusting the search query or filters in the script
- Check if Freesound.org is accessible
- Verify the API endpoint hasn't changed

### Download Errors
- Some sounds may not have previews available
- Network issues may cause timeouts - try again
- Rate limiting: wait a moment between requests
