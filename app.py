import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    return "Welcome to SoundTrip! Integration successful, you can return back to Sound Trip on your browser to continue"

@app.route('/spotify_list', methods=['GET'])
def spotify_list():
    # Kullanıcıdan access_token'ı query parametresi olarak alıyoruz.
    access_token = request.args.get('access_token')
    if not access_token:
        return jsonify({"error": "Access token eksik"}), 400

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Kullanıcının son 6 ayda en çok dinlediği şarkıları (medium_term) çekiyoruz.
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks"
    params = {
        "time_range": "medium_term",  # Son 6 ay
        "limit": 20  # Örnek olarak 20 şarkı alıyoruz, bunu ihtiyacına göre ayarlayabilirsin.
    }
    top_tracks_response = requests.get(top_tracks_url, headers=headers, params=params)
    
    if top_tracks_response.status_code != 200:
        return jsonify({"error": "Spotify top tracks isteği başarısız", 
                        "status_code": top_tracks_response.status_code}), 400
    
    top_tracks = top_tracks_response.json()
    
    # Top tracks listesinden şarkı ID'lerini alıyoruz.
    track_ids = [track["id"] for track in top_tracks.get("items", [])]
    if not track_ids:
        return jsonify({"error": "Hiç şarkı bulunamadı."}), 400
    
    # Audio Features endpoint'ini kullanarak şarkıların BPM (tempo) bilgilerini alıyoruz.
    audio_features_url = "https://api.spotify.com/v1/audio-features"
    features_params = {
        "ids": ",".join(track_ids)
    }
    audio_features_response = requests.get(audio_features_url, headers=headers, params=features_params)
    
    if audio_features_response.status_code != 200:
        return jsonify({"error": "Spotify audio features isteği başarısız", 
                        "status_code": audio_features_response.status_code}), 400
    
    audio_features = audio_features_response.json()
    
    # Audio features listesini, track ID'lerine göre sözlük haline getiriyoruz.
    features_by_id = {}
    for feature in audio_features.get("audio_features", []):
        if feature and "id" in feature:
            features_by_id[feature["id"]] = feature
    
    # Sonuç listemizi oluşturuyoruz: şarkı adı, sanatçılar ve BPM bilgisi.
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
    
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
