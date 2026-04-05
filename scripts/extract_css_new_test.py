from pathlib import Path
nt_path = Path('app/templates/new_test.html')
css_path = Path('static/css/new-test.css')
text = nt_path.read_text(encoding='utf-8')
start = text.find('<style>')
end = text.find('</style>', start)
if start != -1 and end != -1:
    css = text[start+len('<style>'):end].strip() + '\n'
    existing = css_path.read_text(encoding='utf-8') if css_path.exists() else ''
    if css.strip() and css not in existing:
        with css_path.open('a', encoding='utf-8') as f:
            f.write('\n/* NEW TEST PAGE STYLES */\n')
            f.write(css)
    text2 = text[:start] + text[end+len('</style>'):]
    if "url_for('static', filename='css/new-test.css')" not in text2:
        pos = text2.find('</head>')
        link = '    <link href="{{ url_for(\'static\', filename=\'css/new-test.css\') }}" rel="stylesheet">\n'
        text2 = text2[:pos] + link + text2[pos:]
    nt_path.write_text(text2, encoding='utf-8')
    print('new_test updated; css saved to new-test.css')
else:
    print('No style block found in new_test.html')
