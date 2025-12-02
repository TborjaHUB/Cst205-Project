# Unsplash API Integration

This document describes the Unsplash API integration that allows users to fetch random images using keywords.

## Features

- **Keyword Search**: Users can enter any keyword and fetch a random image from Unsplash
- **Non-blocking UI**: Image fetching runs in a background thread, keeping the UI responsive
- **Image Metadata**: Displays author name and image description
- **Error Handling**: Graceful error handling with user-friendly error messages
- **Local File Support**: Still supports opening local images alongside Unsplash searches

## Setup

### 1. Install Dependencies

Install the required packages in your virtual environment:

```bash
pip install -r requirements.txt
```

Or install them individually:

```bash
pip install requests python-dotenv PySide6 Pillow
```

### 2. Unsplash API Credentials

The project includes a `.env` file with Unsplash API credentials. Make sure it contains:

```
UNSPLASH_ACCESS_KEY=your_access_key_here
UNSPLASH_SECRET_KEY=your_secret_key_here
```

If you need new credentials, create an Unsplash application at:
https://unsplash.com/oauth/applications

## Usage

### Running the Application

```bash
python application.py
```

### Fetching Images

1. Enter a keyword in the search field (e.g., "nature", "sunset", "cats")
2. Click "Get Random Image" button or press Enter
3. The application will fetch a random image matching your keyword from Unsplash
4. The image author and description will be displayed below the image

### Opening Local Images

The original "Open Image" button still works to open local image files from your computer.

## Code Structure

### Files

- **application.py**: Main application file with UI and event handling
- **unsplash_api.py**: Unsplash API wrapper class
- **requirements.txt**: Python package dependencies

### Key Classes

#### `UnsplashAPI` (unsplash_api.py)
- Wraps the Unsplash API
- Methods:
  - `get_random_image(query)`: Fetch random image data
  - `get_image_url(query)`: Get just the image URL
  - `get_image_with_metadata(query)`: Get image URL + metadata (author, description)

#### `ImageFetcherWorker` (application.py)
- QThread subclass for non-blocking image fetching
- Signals:
  - `image_fetched`: Emits PIL Image object
  - `metadata_fetched`: Emits metadata dictionary
  - `error_occurred`: Emits error message string

#### `Home` (application.py)
- Main application window
- Methods:
  - `fetch_unsplash_image()`: Initiate image fetch
  - `on_image_fetched()`: Handle fetched image
  - `on_metadata_fetched()`: Display metadata
  - `on_fetch_error()`: Handle errors

## API Details

### Unsplash API Endpoint

The integration uses the Unsplash `/photos/random` endpoint with the following parameters:

- `query`: Search keyword(s)
- `orientation`: Set to "landscape" for wider images
- `content_filter`: Set to "high" to avoid explicit content

For more information, see the [Unsplash API Documentation](https://unsplash.com/napi)

## Troubleshooting

### No images found error
- Try a different keyword
- Some very specific keywords may not have results

### API authentication errors
- Check that your `.env` file contains valid UNSPLASH_ACCESS_KEY
- Verify your API key is active on the Unsplash website

### Network errors
- Check your internet connection
- The application has a 10-second timeout for API requests

### Image won't display
- Check that the image URL is accessible
- The Unsplash API may have rate limits if too many requests are made

## Future Enhancements

- Add image filters and effects
- Allow users to save fetched images
- Display multiple image results for user selection
- Add image caching to reduce API calls
- Implement rate limiting display
