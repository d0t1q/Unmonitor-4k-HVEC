import os
import requests
import subprocess
import re
import sys

# Radarr API key, host and port
RADARR_API_KEY = "RADARR API KEY"
RADARR_HOST = "LOCALHOST"
RADARR_PORT = "7878"

# Directory to scan for video files
SCAN_DIR = r"C:\PATH"

# Track processed, matched, unmonitored, and already unmonitored files
processed_files = 0
matched_files = 0
unmonitored_files = []
already_unmonitored_files = []

def get_video_info(video_file):
    """Get video codec and resolution using ffprobe"""
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=codec_name,height,width", "-of", "csv=p=0", video_file]
        output = subprocess.check_output(cmd).decode('utf-8').strip().split(',')
        return output[0], (int(output[1]), int(output[2]))
    except Exception as e:
        print(f"Error getting video info for {video_file}: {e}")
        return None, (0, 0)

def set_movie_unmonitored(imdb_id, filename):
    """Flag a movie as unmonitored in Radarr"""
    try:
        response = requests.get(f"http://{RADARR_HOST}:{RADARR_PORT}/api/v3/movie?apikey={RADARR_API_KEY}")
        response.raise_for_status()
    except Exception as e:
        print(f"Error getting movie list from Radarr: {e}")
        return

    movies = response.json()
    movie_found = False

    for movie in movies:
        # Check if 'imdbId' key exists in the movie
        if 'imdbId' in movie and movie['imdbId'] == imdb_id:
            movie_found = True
            movie_id = movie['id']

            if movie['monitored']:
                movie['monitored'] = False
                unmonitored_files.append(filename)

                try:
                    response = requests.put(f"http://{RADARR_HOST}:{RADARR_PORT}/api/v3/movie/{movie_id}?apikey={RADARR_API_KEY}", json=movie)
                    response.raise_for_status()
                except Exception as e:
                    print(f"Error updating movie in Radarr: {e}")
                else:
                    print(f"Flagged {imdb_id} as unmonitored in Radarr.")
            else:
                already_unmonitored_files.append(filename)
                print(f"{imdb_id} is already unmonitored in Radarr. Continuing to the next movie.")
    
    if not movie_found:
        print(f"Movie with imdb id {imdb_id} not found in Radarr.")
        
def scan_directory():
    """Walk through directory and process video files"""
    global processed_files, matched_files
    for dirpath, dirnames, filenames in os.walk(SCAN_DIR):
        for filename in filenames:
            processed_files += 1
            if filename.endswith((".mp4", ".mkv", ".avi", ".mov", ".flv")):
                # Normalize the file path
                video_file = os.path.normpath(os.path.join(dirpath, filename))
                print(f"Processing {video_file}...")
                codec, resolution = get_video_info(video_file)
                if codec and codec.lower() == "hevc" and resolution == (3840, 2160):
                    matched_files += 1
                    print(f"{filename} is H265 encoded and in 4K resolution.")
                    match = re.search(r'imdb-(tt\d+)', filename)
                    if match:
                        imdb_id = match.group(1)
                        set_movie_unmonitored(imdb_id, filename)

def main():
    """Main function"""
    if not RADARR_API_KEY:
        print("Please set your Radarr API key.")
        sys.exit(1)
    scan_directory()
    print(f"\nProcessed {processed_files} files")
    print(f"{matched_files} Files matched 4K resolution and HVEC encoding\n")
    print("These files were un-monitored:")
    for file in unmonitored_files:
        print(file)
    print("\nThese files were already un-monitored:")
    for file in already_unmonitored_files:
        print(file)

if __name__ == "__main__":
    main()
