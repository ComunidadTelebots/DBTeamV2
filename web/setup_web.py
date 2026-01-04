from flask import jsonify
import sys
@app.route('/start_backend', methods=['POST'])
def start_backend():
    try:
        # Ruta al backend principal (ajusta si es necesario)
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../python_api/ai_server.py'))
        # Lanzar el backend como proceso independiente
        subprocess.Popen([sys.executable, backend_path])
        return jsonify({'detail': 'Backend iniciado correctamente.'}), 200
    except Exception as e:
        import traceback
        return jsonify({'detail': str(e), 'traceback': traceback.format_exc()}), 500
import os
import subprocess
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

from flask import jsonify
import sys

@app.route('/start_backend', methods=['POST'])
def start_backend():
    try:
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../python_api/ai_server.py'))
        # Lanzar el backend y capturar salida de error
        proc = subprocess.Popen([sys.executable, backend_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        import time
        time.sleep(2)  # Espera breve para capturar errores inmediatos
        retcode = proc.poll()
        if retcode is not None and retcode != 0:
            _, err = proc.communicate(timeout=2)
            return jsonify({'detail': 'Error al iniciar el backend.', 'traceback': err.decode()}), 500
        return jsonify({'detail': 'Backend iniciado correctamente.'}), 200
    except Exception as e:
        import traceback
        return jsonify({'detail': str(e), 'traceback': traceback.format_exc()}), 500

FORM_HTML = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Instalador DBTeamV2</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; }
        .container { max-width: 500px; margin: 40px auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px #ccc; }
        h2 { text-align: center; }
        label { display: block; margin-top: 15px; }
        input[type=text], input[type=password] { width: 100%; padding: 8px; margin-top: 5px; }
        button { margin-top: 20px; width: 100%; padding: 10px; background: #007bff; color: #fff; border: none; border-radius: 4px; font-size: 16px; }
        .msg { margin-top: 20px; color: green; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Instalador DBTeamV2</h2>
        <form method="post">
            <label>BOT_TOKEN (de @BotFather):</label>
            <input type="text" name="BOT_TOKEN" required>
            <label>WEB_API_SECRET (cadena segura):</label>
            <input type="password" name="WEB_API_SECRET" required>
            <label>Admin User ID (Telegram):</label>
            <input type="text" name="ADMIN_USER" required>
            <label>Owner User ID (Telegram):</label>
            <input type="text" name="OWNER_USER" required disabled>
            <label>Redis URL:</label>
            <input type="text" name="REDIS_URL" value="redis://127.0.0.1:6379/0">
            <button type="submit">Instalar y Configurar</button>
            <div style="color:#c00; font-weight:bold; margin-top:1em;">La creación de cuentas está deshabilitada en esta versión pública.</div>
        </form>
        {% if msg %}<div class="msg">{{ msg }}</div>{% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def setup():
    msg = None
    if request.method == 'POST':
        # Recoger datos del formulario
        bot_token = request.form['BOT_TOKEN']
        web_api_secret = request.form['WEB_API_SECRET']
        admin_user = request.form['ADMIN_USER']
        owner_user = request.form['OWNER_USER']
        redis_url = request.form['REDIS_URL']
        # Guardar en .env
        with open(os.path.join(os.path.dirname(__file__), '../.env'), 'w') as f:
            f.write(f"BOT_TOKEN={bot_token}\nWEB_API_SECRET={web_api_secret}\nADMIN_USER={admin_user}\nOWNER_USER={owner_user}\nREDIS_URL={redis_url}\n")
        # Ejecutar instalador general
        install_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../install.sh'))
        subprocess.Popen(['bash', install_path])
        msg = "Configuración guardada y proceso de instalación iniciado. Revisa la terminal para detalles."
    return render_template_string(FORM_HTML, msg=msg)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
