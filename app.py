# app.py
import os
from flask import Flask, render_template, jsonify, send_from_directory

app = Flask(__name__)
OUTPUT_FOLDER = 'output'

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')

@app.route('/api/stories')
def list_stories():
    """output 폴더에 있는 모든 이야기 폴더 목록을 반환"""
    try:
        stories = [d for d in os.listdir(OUTPUT_FOLDER) if os.path.isdir(os.path.join(OUTPUT_FOLDER, d))]
        # 최신순으로 정렬
        stories.sort(reverse=True)
        return jsonify(stories)
    except FileNotFoundError:
        return jsonify([])

@app.route('/outputs/<path:filename>')
def serve_output_file(filename):
    """output 폴더의 정적 파일(이미지, 오디오 등)을 서빙"""
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True)