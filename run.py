from app import create_app
import logging

app = create_app()  # <-- utilise l'instance Flask configurée

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

