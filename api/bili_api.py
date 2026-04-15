from flask import Flask, Response, stream_with_context, abort
import subprocess
import shlex

app = Flask(__name__)

YTDLP = "Your_Path_To/yt-dlp"
COOKIES = "Your_Path_To/cookies.txt"

def normalize(q):
    if q.startswith("BV"):
        return f"https://www.bilibili.com/video/{q}"
    if q.startswith("AV") or q.startswith("av"):
        return f"https://www.bilibili.com/video/{q}"
    if q.startswith("http://") or q.startswith("https://"):
        return q
    return f"ytsearch1:{q}"

def get_direct_url(target):
    cmd = [
        YTDLP,
        "--cookies", COOKIES,
        "--add-header", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
        "--add-header", "Referer: https://www.bilibili.com/",
        "-f", "bestaudio",
        "-g",
        target
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "yt-dlp failed")
    return p.stdout.strip().splitlines()[0]

def stream_audio(src_url):
    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-headers", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11\r\nReferer: https://www.bilibili.com/",
#It's recommended to use the same headers for ffmpeg to avoid potential issues with some servers rejecting requests without proper headers.
#Also, you can generate the UA string using online tools.
        "-i", src_url,
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", "320k",
#Its not necessary to use such high bitrate.
#change it to lower value is recommended.
        "-f", "mp3",
        "pipe:1"
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            chunk = p.stdout.read(8192)
            if not chunk:
                break
            yield chunk
    finally:
        if p.poll() is None:
            p.kill()

@app.route("/bili/<path:q>")
def bili(q):
    try:
        target = normalize(q)
        direct = get_direct_url(target)
    except Exception as e:
        abort(500, str(e))

    return Response(
        stream_with_context(stream_audio(direct)),
        mimetype="audio/mpeg",
        headers={"Cache-Control": "no-cache"}
    )

app.run(host="0.0.0.0", port=5000, threaded=True)
