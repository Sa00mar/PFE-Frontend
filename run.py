from app import create_app

app = create_app()  # <-- utilise l'instance Flask configurée

if __name__ == '__main__':
    app.run(debug=True , use_reloader=False)