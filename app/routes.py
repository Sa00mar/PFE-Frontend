from flask import Blueprint, render_template, request, redirect, url_for, session

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == '1234':  # simple exemple
            session['user'] = username
            return redirect(url_for('main.home'))
        else:
            error = "Nom d'utilisateur ou mot de passe incorrect"
    return render_template('login.html', error=error)

@main.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation des champs
        if not all([firstname, lastname, email, password, confirm_password]):
            error = "Tous les champs sont obligatoires"
        elif password != confirm_password:
            error = "Les mots de passe ne correspondent pas"
        elif len(password) < 6:
            error = "Le mot de passe doit contenir au moins 6 caractères"
        else:
            # Ici vous pouvez ajouter la logique pour sauvegarder l'utilisateur dans la base de données
            success = "Inscription réussie ! Vous pouvez maintenant vous connecter."
            
    return render_template('register.html', error=error, success=success)

@main.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    return render_template('home.html')

@main.route('/new_test')
def new_test():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    return render_template('new_test.html')

@main.route('/my_tests')
def my_tests():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    return render_template('my_tests.html')

@main.route('/test_details/<int:element_id>')
def test_details(element_id):
    if 'user' not in session:
        return redirect(url_for('main.login'))
    
    # Mock data for a single specific element
    # In a real app, you'd fetch this by ID
    mock_elements = {
        1: {
            'id': 1,
            'name': 'Bouton Connexion',
            'type': 'UI / Login',
            'status': 'PASS',
            'screenshot': '/static/img/bouton_connexion.png',
            'xpath': '//button[@id="login"]',
            'action': 'Clic sur le bouton "Se connecter"',
            'expected_result': 'L\'utilisateur est authentifié et la page d\'accueil s\'affiche.',
            'error': None
        },
        2: {
            'id': 2,
            'name': 'Input Email',
            'type': 'Form / Input',
            'status': 'PASS',
            'screenshot': '/static/img/input_email.png',
            'xpath': '//input[@name="email"]',
            'action': 'Saisie de "user@example.com"',
            'expected_result': 'Le texte est correctement saisi dans le champ.',
            'error': None
        },
        3: {
            'id': 3,
            'name': 'Validation Formulaire',
            'type': 'Logic / Form',
            'status': 'FAIL',
            'screenshot': '/static/img/Validation_formulaire.png',
            'xpath': '//form[@id="auth"]',
            'action': 'Soumission du formulaire',
            'expected_result': 'Le formulaire est validé et les données sont envoyées.',
            'error': 'Element not found: Impossible de localiser le bouton de soumission après remplissage.'
        }
    }
    
    test_element = mock_elements.get(element_id, mock_elements[3]) # default to 3 for demo
    return render_template('test_details.html', test=test_element)

@main.route('/settings')
def settings():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    # créer la page settings.html, ou rediriger vers un point de sortie existant
    return render_template('settings.html')

@main.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    
    url = request.form.get('url') if request.method == 'POST' else request.args.get('url', 'https://exemple.com')
    return render_template('analysis_result.html', url=url)

@main.route('/analysis_result')
def analysis_result():
    if 'user' not in session:
        return redirect(url_for('main.login'))
    return render_template('analysis_result.html', url='https://exemple.com')

@main.route('/test_results/<int:test_id>')
@main.route('/test_results')
def test_results(test_id=1):
    if 'user' not in session:
        return redirect(url_for('main.login'))
    
    # Mock data for demonstration
    test_data = {
        'id': test_id,
        'url': 'https://glovoapp.com/fr',
        'date': '31 Mars 2026',
        'time': '17:45',
        'version': 'v1.2.4',
        'total_time': '45s',
        'stats': {
            'pass': 3,
            'fail': 1,
            'warning': 1,
            'total': 5
        },
        'results': [
            {
                'id': 1,
                'name': 'Bouton Connexion',
                'type': 'UI / Button',
                'status': 'PASS',
                'screenshot': '/static/img/bouton_connexion.png',
                'xpath': '//button[@id="login"]',
                'action': 'click',
                'expected': 'Navigation vers Accueil',
                'error': None
            },
            {
                'id': 2,
                'name': 'Input Email',
                'type': 'Form / Input',
                'status': 'PASS',
                'screenshot': '/static/img/input_email.png',
                'xpath': '//input[@name="email"]',
                'action': 'type: user@example.com',
                'expected': 'Input contient le texte',
                'error': None
            },
            {
                'id': 3,
                'name': 'Validation Formulaire',
                'type': 'Logic / Form',
                'status': 'FAIL',
                'screenshot': '/static/img/Validation_formulaire.png',
                'xpath': '//form[@id="auth"]',
                'action': 'submit',
                'expected': 'Redirection réussie',
                'error': 'Element not found'
            },
            {
                'id': 4,
                'name': 'Logo Header',
                'type': 'UI / Image',
                'status': 'WARNING',
                'screenshot': '/static/img/Logo_header .png',
                'xpath': '//header/img',
                'action': 'check visibility',
                'expected': 'Logo est visible',
                'error': 'Slightly slow load time'
            },
            {
                'id': 5,
                'name': 'Champ Mot de passe',
                'type': 'Form / Input',
                'status': 'PASS',
                'screenshot': '/static/img/Champ_motdepasse.png',
                'xpath': '//input[@type="password"]',
                'action': 'type: *******',
                'expected': 'Input masqué',
                'error': None
            }
        ]
    }
    return render_template('test_results.html', data=test_data)

@main.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('main.login'))


