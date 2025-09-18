#!/usr/bin/env python3
"""
Petite interface web pour lister et télécharger les fichiers de la carte SD
du Teensy, avec choix du dossier de sortie et renommage optionnel.
"""

import os
import threading
from typing import Optional

from flask import Flask, render_template_string, request, redirect, url_for, flash

from teensy_sd_interface import TeensySDInterface


# Application Flask simple (pas de templates séparés pour garder un seul fichier)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")


# État global minimal
class AppState:
    def __init__(self):
        self.output_dir: str = os.path.abspath(os.path.join(os.getcwd(), "downloaded_files"))
        self.interface: Optional[TeensySDInterface] = None
        self.lock = threading.Lock()

    def ensure_interface(self) -> Optional[TeensySDInterface]:
        with self.lock:
            if self.interface is None:
                self.interface = TeensySDInterface()
                if not self.interface.connect():
                    self.interface = None
            return self.interface

    def disconnect(self):
        with self.lock:
            if self.interface is not None:
                try:
                    self.interface.disconnect()
                finally:
                    self.interface = None


STATE = AppState()


INDEX_HTML = """
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Teensy SD Web</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
      h1 { margin-top: 0; }
      form, .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
      .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
      label { font-weight: 600; }
      input[type=text] { padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 280px; }
      button { padding: 8px 12px; border: 1px solid #0ea5e9; background: #0ea5e9; color: white; border-radius: 6px; cursor: pointer; }
      button.secondary { background: #fff; color: #0ea5e9; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 8px 10px; border-bottom: 1px solid #e5e7eb; text-align: left; }
      .muted { color: #6b7280; }
      .flash { padding: 10px 12px; border-radius: 6px; margin-bottom: 12px; }
      .flash.ok { background: #ecfeff; color: #0c4a6e; border: 1px solid #67e8f9; }
      .flash.err { background: #fef2f2; color: #7f1d1d; border: 1px solid #fecaca; }
      .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
      @media (min-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
    </style>
  </head>
  <body>
    <h1>Teensy SD Web</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="flash {{ 'ok' if category == 'success' else 'err' }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="grid">
      <div class="card">
        <h2>Dossier de sortie</h2>
        <form method="post" action="{{ url_for('set_output_dir') }}" class="row">
          <label for="output_dir">Chemin:</label>
          <input type="text" id="output_dir" name="output_dir" value="{{ output_dir }}" />
          <button type="submit">Enregistrer</button>
        </form>
        <div class="muted">Les fichiers téléchargés seront sauvegardés dans ce dossier.</div>
      </div>

      <div class="card">
        <h2>Connexion</h2>
        <form method="post" action="{{ url_for('refresh_connection') }}" class="row">
          <button class="secondary" type="submit">Reconnecter le Teensy</button>
          <span class="muted">Statut: {{ 'Connecté' if connected else 'Non connecté' }}</span>
        </form>
      </div>
    </div>

    <div class="card">
      <div class="row" style="justify-content: space-between;">
        <h2 style="margin: 0;">Fichiers sur la carte SD</h2>
        <form method="post" action="{{ url_for('refresh_files') }}">
          <button class="secondary" type="submit">Rafraîchir</button>
        </form>
      </div>
      {% if files %}
      <table>
        <thead>
          <tr>
            <th>Nom SD</th>
            <th>Renommer en</th>
            <th style="width: 1%;">Action</th>
          </tr>
        </thead>
        <tbody>
          {% for f in files %}
          <tr>
            <td><code>{{ f }}</code></td>
            <td>
              <form method="post" action="{{ url_for('download_file') }}" class="row">
                <input type="hidden" name="filename" value="{{ f }}" />
                <input type="text" name="rename" placeholder="{{ f }}" />
                <button type="submit">Télécharger</button>
              </form>
            </td>
            <td></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
        <div class="muted">Aucun fichier trouvé. Vérifiez la connexion et rafraîchissez.</div>
      {% endif %}
    </div>

  </body>
  </html>
"""


def is_safe_path(base: str, path: str) -> bool:
    base = os.path.realpath(base)
    target = os.path.realpath(path)
    return os.path.commonpath([base]) == os.path.commonpath([base, target])


@app.route("/", methods=["GET"])
def index():
    interface = STATE.ensure_interface()
    files = []
    connected = interface is not None
    if connected:
        try:
            # Sérialiser l'accès série pour éviter les chevauchements avec d'autres requêtes
            with STATE.lock:
                files = interface.list_files()
        except Exception as exc:
            files = []
            connected = False
            flash(f"Erreur de liste: {exc}", "error")
            STATE.disconnect()
    return render_template_string(INDEX_HTML, files=files, output_dir=STATE.output_dir, connected=connected)


@app.route("/refresh", methods=["POST"])
def refresh_files():
    return redirect(url_for("index"))


@app.route("/reconnect", methods=["POST"])
def refresh_connection():
    STATE.disconnect()
    interface = STATE.ensure_interface()
    if interface is None:
        flash("Impossible de se connecter au Teensy", "error")
    else:
        flash("Connecté au Teensy", "success")
    return redirect(url_for("index"))


@app.route("/set_output_dir", methods=["POST"])
def set_output_dir():
    output_dir = request.form.get("output_dir", "").strip()
    if not output_dir:
        flash("Chemin invalide", "error")
        return redirect(url_for("index"))

    output_dir_abs = os.path.abspath(output_dir)
    try:
        os.makedirs(output_dir_abs, exist_ok=True)
    except Exception as exc:
        flash(f"Impossible de créer le dossier: {exc}", "error")
        return redirect(url_for("index"))

    STATE.output_dir = output_dir_abs
    flash(f"Dossier de sortie défini: {STATE.output_dir}", "success")
    return redirect(url_for("index"))


@app.route("/download", methods=["POST"])
def download_file():
    filename = request.form.get("filename", "").strip()
    rename = request.form.get("rename", "").strip()

    if not filename:
        flash("Nom de fichier manquant", "error")
        return redirect(url_for("index"))

    interface = STATE.ensure_interface()
    if interface is None:
        flash("Non connecté au Teensy", "error")
        return redirect(url_for("index"))

    # Chemin final avec renommage optionnel
    target_name = rename if rename else filename
    # Sécurité: éviter les traversals
    if os.path.sep in target_name or (os.path.altsep and os.path.altsep in target_name):
        flash("Nom de fichier de destination invalide", "error")
        return redirect(url_for("index"))

    # Téléchargement d'abord dans un nom temporaire si renommage
    temp_name = filename if rename else target_name

    try:
        # Sérialiser l'accès série pendant le téléchargement
        with STATE.lock:
            ok = interface.get_file(filename, STATE.output_dir)
        if not ok:
            flash("Échec du téléchargement", "error")
            return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Erreur pendant le téléchargement: {exc}", "error")
        return redirect(url_for("index"))

    # Renommage si demandé
    if rename and rename != filename:
        src_path = os.path.join(STATE.output_dir, temp_name)
        dst_path = os.path.join(STATE.output_dir, target_name)
        # Vérifier que dst reste dans le dossier configuré
        if not is_safe_path(STATE.output_dir, dst_path):
            flash("Cible de renommage invalide", "error")
            return redirect(url_for("index"))
        try:
            os.replace(src_path, dst_path)
        except Exception as exc:
            flash(f"Téléchargé, mais renommage échoué: {exc}", "error")
            return redirect(url_for("index"))

    flash(f"Fichier sauvegardé dans {STATE.output_dir} sous '{target_name}'", "success")
    return redirect(url_for("index"))


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    # Permet de lancer rapidement: python teensy_sd_web.py --host 0.0.0.0 --port 5000
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=True)


