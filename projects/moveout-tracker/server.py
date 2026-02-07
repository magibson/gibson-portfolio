from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='.')


@app.get('/')
def index():
    return send_from_directory('.', 'index.html')


@app.get('/<path:path>')
def static_proxy(path):
    return send_from_directory('.', path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088, debug=True)
