import subprocess
import json
import os
import csv
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    """Estrae l'ID video da un URL YouTube"""
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        if query.path.startswith('/live/'):
            return query.path.split('/')[-1]
    return None

def get_youtube_hls_url(video_id):
    try:
        cmd = [
            'yt-dlp',
            f'https://www.youtube.com/watch?v={video_id}',
            '-j',
            '--skip-download'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)
        
        # Trova la migliore qualità HLS
        for fmt in video_info.get('formats', []):
            if fmt.get('protocol') == 'm3u8_native':
                return fmt['url']
        
        if 'manifest_url' in video_info:
            return video_info['manifest_url']
        
        return None
    except Exception as e:
        print(f"Errore durante il processing di {video_id}: {e}")
        return None

def process_csv(csv_file):
    """Processa il file CSV e genera i file M3U8"""
    if not os.path.exists('YouTubeLive'):
        os.makedirs('YouTubeLive')
    
    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            video_id = extract_video_id(row['url'])
            if not video_id:
                print(f"URL non valido: {row['url']}")
                continue
            
            hls_url = get_youtube_hls_url(video_id)
            if hls_url:
                output_file = os.path.join('YouTubeLive', f"{row['nome']}.m3u8")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(hls_url)
                print(f"Creato: {output_file}")
            else:
                print(f"Impossibile ottenere HLS per {row['nome']}")

if __name__ == "__main__":
    CSV_FILE = "liveyoutube.csv"
    if os.path.exists(CSV_FILE):
        process_csv(CSV_FILE)
    else:
        print(f"File {CSV_FILE} non trovato!")
        with open(CSV_FILE, 'w', encoding='utf-8') as f:
            f.write("url,nome\n")
            f.write("https://www.youtube.com/live/xRPjKQtRXR8,stream1\n")
        print(f"Creato file CSV di esempio: {CSV_FILE}")