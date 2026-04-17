#!/usr/bin/env python3
"""HealBotics 3D AI Video Generator - Flask Application"""

import os
import json
import uuid
import queue
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

job_queues: dict = {}
job_results: dict = {}

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def send_update(job_id: str, data: dict):
    if job_id in job_queues:
        job_queues[job_id].put(data)


def run_generation_pipeline(job_id: str, prompt: str, options: dict):
    output_path = OUTPUT_DIR / job_id
    output_path.mkdir(exist_ok=True)

    try:
        from generators.script_gen import generate_script
        from generators.tts_gen import generate_tts
        from generators.video_gen import generate_video_scenes
        from generators.assembler import assemble_video

        send_update(job_id, {
            "step": "script", "status": "running",
            "message": "Analysiere Prompt und generiere Skript...", "progress": 5
        })
        script = generate_script(prompt, options)
        send_update(job_id, {
            "step": "script", "status": "done",
            "message": f"Skript erstellt: {len(script['scenes'])} Szenen",
            "data": script, "progress": 25
        })

        send_update(job_id, {
            "step": "tts", "status": "running",
            "message": "Generiere KI-Sprachausgabe auf Deutsch...", "progress": 30
        })
        audio_files = generate_tts(script, output_path)
        send_update(job_id, {
            "step": "tts", "status": "done",
            "message": f"{len([a for a in audio_files if a])} Audio-Segmente erstellt", "progress": 50
        })

        send_update(job_id, {
            "step": "video", "status": "running",
            "message": "Generiere 3D-Animationsszenen (dauert 2-5 Min.)...", "progress": 55
        })
        video_files = generate_video_scenes(script, output_path)
        send_update(job_id, {
            "step": "video", "status": "done",
            "message": f"{len([v for v in video_files if v])} Video-Szenen generiert", "progress": 80
        })

        send_update(job_id, {
            "step": "assemble", "status": "running",
            "message": "Assembliere finales Video...", "progress": 85
        })
        final_video = assemble_video(script, audio_files, video_files, output_path)

        job_results[job_id] = {
            "status": "completed",
            "video_path": str(final_video),
            "script": script
        }
        send_update(job_id, {
            "step": "complete", "status": "done",
            "message": "Video erfolgreich generiert!",
            "progress": 100,
            "download_url": f"/api/download/{job_id}"
        })

    except Exception as e:
        error_msg = str(e)
        job_results[job_id] = {"status": "failed", "error": error_msg}
        send_update(job_id, {
            "step": "error", "status": "failed",
            "message": f"Fehler: {error_msg}", "progress": 0
        })
    finally:
        threading.Timer(2.0, lambda: job_queues.get(job_id) and job_queues[job_id].put(None)).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    if not data or not data.get('prompt'):
        return jsonify({"error": "Kein Prompt angegeben"}), 400

    job_id = str(uuid.uuid4())
    job_queues[job_id] = queue.Queue()

    thread = threading.Thread(
        target=run_generation_pipeline,
        args=(job_id, data['prompt'], data.get('options', {})),
        daemon=True
    )
    thread.start()
    return jsonify({"job_id": job_id})


@app.route('/api/status/<job_id>')
def status_stream(job_id: str):
    def generate_sse():
        q = job_queues.get(job_id)
        if not q:
            yield f"data: {json.dumps({'error': 'Job nicht gefunden'})}\n\n"
            return
        while True:
            try:
                msg = q.get(timeout=30)
                if msg is None:
                    yield "data: {\"done\": true}\n\n"
                    break
                yield f"data: {json.dumps(msg)}\n\n"
            except queue.Empty:
                yield "data: {\"heartbeat\": true}\n\n"

    return Response(
        generate_sse(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/download/<job_id>')
def download_video(job_id: str):
    result = job_results.get(job_id)
    if not result or result['status'] != 'completed':
        return jsonify({"error": "Video nicht gefunden"}), 404
    video_path = result['video_path']
    if not Path(video_path).exists():
        return jsonify({"error": "Video-Datei nicht gefunden"}), 404
    return send_file(
        video_path,
        as_attachment=True,
        download_name=f"healbotics_video_{job_id[:8]}.mp4",
        mimetype='video/mp4'
    )


@app.route('/api/script-only', methods=['POST'])
def script_only():
    data = request.json
    if not data or not data.get('prompt'):
        return jsonify({"error": "Kein Prompt angegeben"}), 400
    try:
        from generators.script_gen import generate_script
        script = generate_script(data['prompt'], data.get('options', {}))
        return jsonify({"success": True, "script": script})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
