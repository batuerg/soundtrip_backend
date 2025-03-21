import os
import sys
import requests
import logging
from flask import Flask, request, redirect, jsonify

# Logging yapılandırması: DEBUG seviyesinde log alınır.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ortam değişkenlerinden alınan bilgiler
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# Örneğin: https://soundtripbackend-production.up.railway.app/callback
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Spotify OAuth URL'leri ve istenen izinler (scope)
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPE = "user-top-read user-read-recently-played"

@app.route('/')
def home():
    return "Welcome to SoundTrip! Integration successful, you can return back to Sound Trip on your browser to continue"

# /login: Kullanıcıyı Spotify yetkilendirme sayfasına yönlendirir.
@app.route('/login')
def login():
    auth_query = f"?response_type=code&client_id={CLIENT_ID}&scope={SCOPE}&redirect_uri={REDIRECT_URI}"
    full_url = SPOTIFY_AUTH_URL + auth_query
    logger.debug("Redirecting to Spotify Auth URL: %s", full_url)
    sys.stdout.flush()
    return redirect(full_url)

# /callback: Spotify, kullanıcı yetkilendirmesi sonrası bu endpoint'e yönlendirir.
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Authentication failed: code not provided.", 400

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
    token_info = token_response.json()
    
    # Token yanıtını logla
    logger.debug("Token Yanıtı: %s", token_info)
    sys.stdout.flush()
    
    access_token = token_info.get("access_token")
    if not access_token:
        return "Token exchange failed.", 400

    # Kullanıcıyı /spotify_list endpoint'ine yönlendir, token URL'e eklenir.
    return redirect(f"/spotify_list?access_token={access_token}")

# /spotify_list: Kullanıcının son 6 ayın top tracks verisini ve her şarkının BPM bilgisini döner.
@app.route('/spotify_list', methods=['GET'])
def spotify_list():
    access_token = request.args.get('access_token')
    if not access_token:
        return jsonify({"error": "Access token eksik"}), 400

    headers = {"Authorization": f"Bearer {access_token}"}

    # Spotify'dan medium_term (son 6 ay) top tracks verisini çekiyoruz.
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks"
    params = {
        "time_range": "medium_term",
        "limit": 20
    }
    top_tracks_response = requests.get(top_tracks_url, headers=headers, params=params)
    logger.debug("Top Tracks Response Status Code: %s", top_tracks_response.status_code)
    logger.debug("Top Tracks Response: %s", top_tracks_response.text)
    sys.stdout.flush()
    
    if top_tracks_response.status_code != 200:
        return jsonify({
            "error": "Spotify top tracks isteği başarısız", 
            "status_code": top_tracks_response.status_code
        }), 400

    top_tracks = top_tracks_response.json()

    # Top tracks listesinden şarkı ID'lerini alıyoruz.
    track_ids = [track["id"] for track in top_tracks.get("items", [])]
    if not track_ids:
        return jsonify({"error": "Hiç şarkı bulunamadı."}), 400

    # Audio features endpoint'ini kullanarak şarkıların BPM (tempo) bilgilerini alıyoruz.
    audio_features_url = "https://api.spotify.com/v1/audio-features"
    features_params = {
        "ids": ",".join(track_ids)
    }
    audio_features_response = requests.get(audio_features_url, headers=headers, params=features_params)
    logger.debug("Audio Features Response Status Code: %s", audio_features_response.status_code)
    logger.debug("Audio Features Response: %s", audio_features_response.text)
    sys.stdout.flush()
    
    if audio_features_response.status_code != 200:
        return jsonify({
            "error": "Spotify audio features isteği başarısız", 
            "status_code": audio_features_response.status_code
        }), 400

    audio_features = audio_features_response.json()

    # Audio features listesini, track ID'sine göre sözlüğe dönüştürüyoruz.
    features_by_id = {}
    for feature in audio_features.get("audio_features", []):
        if feature and "id" in feature:
            features_by_id[feature["id"]] = feature

    # Sonuç listesi: her şarkı için şarkı adı, sanatçılar ve BPM.
    results = []
    for track in top_tracks.get("items", []):
        track_id = track.get("id")
        track_name = track.get("name")
        artists = [artist.get("name") for artist in track.get("artists", [])]
        bpm = features_by_id.get(track_id, {}).get("tempo", "N/A")
        results.append({
            "track_name": track_name,
            "artists": artists,
            "bpm": bpm
        })

    logger.debug("Final Results: %s", results)
    sys.stdout.flush()
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
