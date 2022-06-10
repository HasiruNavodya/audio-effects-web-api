import os
import urllib.request
from flask import Flask, current_app, flash, request, jsonify, redirect, send_from_directory, url_for, render_template
from werkzeug.utils import secure_filename
import moviepy.editor as mp
from pedalboard import *
from pedalboard.io import AudioFile
from moviepy.editor import *
from firebase_admin import credentials, initialize_app, storage, firestore
import calendar
import time

app = Flask(__name__)

cred = credentials.Certificate("fbadmin.json")
initialize_app(cred, {'storageBucket': 'hnmp-museup.appspot.com'})
db = firestore.client()


# API Endpoint for uploading videos to add audio effects
@app.route('/upload/video-with-fx', methods=["POST"])
def upload():
    if request.method == "POST":
        file = request.files['video']
        user_id = request.args.get('userID')

        gmt = time.gmtime()
        ts = calendar.timegm(gmt)
        file_name = secure_filename(user_id + str(ts))
        file_name_ex = secure_filename(file_name + ".mp4")
        file.save("storage/" + file_name_ex)

        clip = mp.VideoFileClip(r"storage/" + file_name_ex)
        clip.audio.write_audiofile(r"storage/" + file_name + ".wav")

        add_fx("storage/" + file_name + ".wav", file_name, user_id)

        return jsonify({
            "filename": str(file_name_ex),
            "url": str(),
        })


# this function adds effects to the audio file -compression, delay, reverb, limiter
def add_fx(file_path, file_name, user_id):
    with AudioFile(file_path, 'r') as f:
        audio = f.read(f.frames)
        samplerate = f.samplerate

    board = Pedalboard([
        #Compressor(threshold_db=-30, ratio=1.1),
        Delay(delay_seconds=0.5, mix=0.1, feedback=0.05),
        Reverb(room_size=0.1, wet_level=0.1, damping=0.9),
        #Limiter(threshold_db=-0.1),
    ])
    effected = board(audio, samplerate)
    with AudioFile("storage/" + file_name + "afx.wav", 'w', samplerate, effected.shape[0]) as f:
        f.write(effected)

    videoclip = VideoFileClip("storage/" + file_name + ".mp4")
    new_clip = videoclip.without_audio()
    new_clip.write_videofile("storage/" + file_name + "no-audio.mp4")

    audioclip = AudioFileClip("storage/" + file_name + "afx.wav")

    new_audioclip = CompositeAudioClip([audioclip])
    new_clip.audio = new_audioclip
    new_clip.write_videofile("storage/" + file_name + "final.mp4")
    #upload_to_fb_storage("storage/" + file_name + "final.mp4", user_id)


# upload new video to firebase storage
def upload_to_fb_storage(file_name, user_id):
    bucket = storage.bucket()
    blob = bucket.blob(file_name)
    blob.upload_from_filename(file_name)
    blob.make_public()
    url = blob.public_url

    db.collection('media').add({
        "userID": user_id,
        "url": url,
        "type": "video",
        "time": firestore.SERVER_TIMESTAMP,
    })


if __name__ == '__main__':
    app.run(debug=True, port=3500)
