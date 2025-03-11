import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, SoundTrip!"

if __name__ == '__main__':
    # Railway'un verdiği PORT'u al; yoksa 5000 kullan
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
