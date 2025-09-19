#!/usr/bin/env python3
"""
Petite interface web pour lister et télécharger les fichiers de la carte SD
du Teensy, avec choix du dossier de sortie et renommage optionnel.
"""

import os
import threading
import tempfile
import shutil
import atexit
from typing import Optional, List

from flask import Flask, render_template_string, request, redirect, url_for, flash, send_from_directory

import numpy as np
import sounddevice as sd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
        self.temp_dir = tempfile.mkdtemp(prefix="teensy_sd_web_")
        self.hammer_output_root: str = os.path.abspath(os.path.join(os.getcwd(), "marteau", "results"))
        self.hammer_device: Optional[int] = None  # None -> system default
        self.hammer_threshold_n: float = 10.0
        self.hammer_fs: int = 48000
        self.hammer_sensitivity_v_per_n: float = 0.002251

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

def _cleanup_temp_dir(path: str):
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

atexit.register(_cleanup_temp_dir, path=lambda: STATE.temp_dir if 'STATE' in globals() else None)


STATE = AppState()
def _find_input_device_index_by_name(name_substring: str) -> Optional[int]:
    try:
        q = sd.query_devices()
        name_sub = name_substring.lower()
        candidates = []
        for idx, d in enumerate(q):
            if d.get('max_input_channels', 0) > 0:
                n = (d.get('name') or '').lower()
                if name_sub in n:
                    candidates.append(idx)
        if candidates:
            return candidates[0]
    except Exception:
        pass
    return None


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
        <div class="row">
          <form method="post" action="{{ url_for('refresh_files') }}">
            <button class="secondary" type="submit">Rafraîchir</button>
          </form>
          <form method="get" action="{{ url_for('hammer_index') }}">
            <button class="secondary" type="submit">Marteau</button>
          </form>
          <form method="post" action="{{ url_for('delete_all_route') }}" onsubmit="return confirm('Supprimer tous les fichiers ?');">
            <button type="submit" style="border-color:#ef4444;background:#ef4444;">Supprimer tout</button>
          </form>
        </div>
      </div>
      {% if files %}
      <table>
        <thead>
          <tr>
            <th>Nom SD</th>
            <th>Renommer en</th>
            <th style="width: 1%;">Supprimer</th>
            <th style="width: 1%;">Tracer</th>
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
            <td>
              <form method="post" action="{{ url_for('delete_file_route') }}" onsubmit="return confirm('Supprimer {{ f }} ?');">
                <input type="hidden" name="filename" value="{{ f }}" />
                <button type="submit" style="border-color:#ef4444;background:#ef4444;">Supprimer</button>
              </form>
            </td>
            <td>
              <form method="post" action="{{ url_for('plot_file_route') }}">
                <input type="hidden" name="filename" value="{{ f }}" />
                <button type="submit">Plot</button>
              </form>
            </td>
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


PLOT_HTML = """
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Teensy SD Web - Plot</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
      img { max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px; }
      a { color: #0ea5e9; text-decoration: none; }
    </style>
  </head>
  <body>
    <h1>Tracé: {{ filename }}</h1>
    <p><a href="{{ url_for('index') }}">← Retour</a></p>
    <div style="margin: 12px 0; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px;">
      <form method="post" action="{{ url_for('download_file') }}" class="row" style="gap:8px; align-items:center;">
        <input type="hidden" name="filename" value="{{ filename }}" />
        <label for="rename_plot"><strong>Renommer en</strong></label>
        <input id="rename_plot" type="text" name="rename" placeholder="{{ filename }}" />
        <button type="submit">Télécharger</button>
      </form>
    </div>
    {% for img in images %}
      <div style="margin-bottom:16px;">
        <img src="{{ url_for('serve_temp_file', name=img) }}" alt="plot" />
      </div>
    {% endfor %}
  </body>
  </html>
"""


HAMMER_HTML = """
<!doctype html>
<html lang=\"fr\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Teensy SD Web - Marteau</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
      form, .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
      .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
      label { font-weight: 600; }
      input[type=text], input[type=number] { padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 180px; }
      button { padding: 8px 12px; border: 1px solid #0ea5e9; background: #0ea5e9; color: white; border-radius: 6px; cursor: pointer; }
      button.secondary { background: #fff; color: #0ea5e9; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 8px 10px; border-bottom: 1px solid #e5e7eb; text-align: left; }
      .muted { color: #6b7280; }
      .flash { padding: 10px 12px; border-radius: 6px; margin-bottom: 12px; }
      .flash.ok { background: #ecfeff; color: #0c4a6e; border: 1px solid #67e8f9; }
      .flash.err { background: #fef2f2; color: #7f1d1d; border: 1px solid #fecaca; }
    </style>
  </head>
  <body>
    <h1>Calibration Marteau</h1>
    <p><a href=\"{{ url_for('index') }}\">← Retour</a></p>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class=\"flash {{ 'ok' if category == 'success' else 'err' }}\">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class=\"card\">
      <h2>Paramètres d'enregistrement (mode attente)</h2>
      <form method=\"post\" action=\"{{ url_for('hammer_record') }}\" class=\"row\">
        <label for=\"device\">Device index</label>
        <input type=\"number\" id=\"device\" name=\"device\" value=\"{{ hammer_device if hammer_device is not none else '' }}\" placeholder=\"par défaut\" />

        <label for=\"threshold\">Seuil min (N)</label>
        <input type=\"number\" step=\"0.1\" id=\"threshold\" name=\"threshold\" value=\"{{ hammer_threshold_n }}\" />

        <label for=\"fs\">Fréquence (Hz)</label>
        <input type=\"number\" id=\"fs\" name=\"fs\" value=\"{{ hammer_fs }}\" />

        <label for=\"sens\">Sensibilité (V/N)</label>
        <input type=\"number\" step=\"0.000001\" id=\"sens\" name=\"sens\" value=\"{{ hammer_sensitivity }}\" />

        <button type=\"submit\">Démarrer (attente seuil)</button>
      </form>
      <div class=\"muted\">Le système attend qu'une force dépasse le seuil et enregistre uniquement la valeur maximale. Laissez "Device index" vide pour auto-détection (cherche le périphérique nommé \"485B39\").</div>
    </div>

    <div class=\"card\">
      <h2>Dossier de sortie</h2>
      <form method=\"post\" action=\"{{ url_for('hammer_set_dir') }}\" class=\"row\">
        <label for=\"outdir\">Base:</label>
        <input type=\"text\" id=\"outdir\" name=\"outdir\" value=\"{{ hammer_output_root }}\" />
        <button type=\"submit\">Enregistrer</button>
      </form>
      <div class=\"muted\">Chaque enregistrement crée un sous-dossier horodaté dans ce dossier.</div>
    </div>

    <div class=\"card\">
      <h2>Périphériques audio (lecture seule)</h2>
      <table>
        <thead>
          <tr><th>#</th><th>Nom</th><th>Max in</th><th>Max out</th></tr>
        </thead>
        <tbody>
          {% for d in devices %}
            <tr>
              <td>{{ d['index'] }}</td>
              <td>{{ d['name'] }}</td>
              <td>{{ d['max_input_channels'] }}</td>
              <td>{{ d['max_output_channels'] }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
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

    # Normaliser le renommage: ajouter .bin si manquant
    if rename and not rename.lower().endswith('.bin'):
        rename = rename + '.bin'

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


@app.route("/delete", methods=["POST"])
def delete_file_route():
    filename = request.form.get("filename", "").strip()
    if not filename:
        flash("Nom de fichier manquant", "error")
        return redirect(url_for("index"))

    interface = STATE.ensure_interface()
    if interface is None:
        flash("Non connecté au Teensy", "error")
        return redirect(url_for("index"))

    try:
        with STATE.lock:
            ok = interface.delete_file(filename)
        if not ok:
            flash("Échec de la suppression", "error")
            return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Erreur pendant la suppression: {exc}", "error")
        return redirect(url_for("index"))

    flash(f"Fichier supprimé: {filename}", "success")
    return redirect(url_for("index"))

@app.route("/delete_all", methods=["POST"])
def delete_all_route():
    interface = STATE.ensure_interface()
    if interface is None:
        flash("Non connecté au Teensy", "error")
        return redirect(url_for("index"))

    try:
        with STATE.lock:
            deleted_count = interface.delete_all()
        if deleted_count < 0:
            flash("Échec de la suppression globale", "error")
            return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Erreur pendant la suppression globale: {exc}", "error")
        return redirect(url_for("index"))

    flash(f"Fichiers supprimés: {deleted_count}", "success")
    return redirect(url_for("index"))


@app.route("/plot", methods=["POST"])
def plot_file_route():
    filename = request.form.get("filename", "").strip()
    if not filename:
        flash("Nom de fichier manquant", "error")
        return redirect(url_for("index"))

    interface = STATE.ensure_interface()
    if interface is None:
        flash("Non connecté au Teensy", "error")
        return redirect(url_for("index"))

    # Télécharger dans le dossier temporaire
    try:
        with STATE.lock:
            ok = interface.get_file(filename, STATE.temp_dir)
        if not ok:
            flash("Échec du téléchargement pour tracé", "error")
            return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Erreur téléchargement: {exc}", "error")
        return redirect(url_for("index"))

    temp_path = os.path.join(STATE.temp_dir, filename)
    if not os.path.exists(temp_path):
        flash("Fichier temporaire introuvable", "error")
        return redirect(url_for("index"))

    # Lire et tracer
    try:
        data = np.fromfile(temp_path, dtype=np.int32)
        NUM_CHANNELS = 6
        if data.size % NUM_CHANNELS != 0:
            flash(f"Taille binaire incorrecte ({data.size})", "error")
            return redirect(url_for("index"))
        data = data.reshape(-1, NUM_CHANNELS)
        adc_data = data[:, :5]
        timestamps = data[:, 5]
        time_s = timestamps * 1e-6

        # Figure signaux
        fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
        pins = [15, 17, 19, 21, 23]
        for i in range(5):
            axs[i].plot(time_s, adc_data[:, i])
            axs[i].set_title(f"ADC Pin {pins[i]}")
            axs[i].set_ylabel("Valeur ADC")
            axs[i].grid(True)
        axs[-1].set_xlabel('Temps (s)')
        plt.tight_layout()
        img1 = f"plot_{os.path.basename(filename)}_signals.png"
        out1 = os.path.join(STATE.temp_dir, img1)
        fig.savefig(out1, dpi=120)
        plt.close(fig)

        # Figure fréquence instantanée
        time_s2 = timestamps / 1e6
        if len(time_s2) > 1:
            delta_t = np.diff(time_s2)
            frequencies = 1.0 / delta_t
            fig2 = plt.figure(figsize=(10, 4))
            plt.plot(frequencies)
            plt.title("Fréquence d'échantillonnage instantanée")
            plt.xlabel("Échantillon")
            plt.ylabel("Fréquence (Hz)")
            plt.grid(True)
            plt.tight_layout()
            img2 = f"plot_{os.path.basename(filename)}_freq.png"
            out2 = os.path.join(STATE.temp_dir, img2)
            fig2.savefig(out2, dpi=120)
            plt.close(fig2)
            images: List[str] = [img1, img2]
        else:
            images = [img1]
    except Exception as exc:
        flash(f"Erreur tracé: {exc}", "error")
        return redirect(url_for("index"))

    return render_template_string(PLOT_HTML, filename=filename, images=images)


@app.route('/tmp/<path:name>')
def serve_temp_file(name: str):
    return send_from_directory(STATE.temp_dir, name, as_attachment=False, mimetype='image/png')


@app.route("/hammer", methods=["GET"])
def hammer_index():
    try:
        q = sd.query_devices()
        devices = []
        for idx, d in enumerate(q):
            devices.append({
                'index': idx,
                'name': d.get('name', ''),
                'max_input_channels': d.get('max_input_channels', 0),
                'max_output_channels': d.get('max_output_channels', 0),
            })
    except Exception as exc:
        devices = []
        flash(f"Erreur lecture périphériques: {exc}", "error")

    return render_template_string(
        HAMMER_HTML,
        hammer_device=STATE.hammer_device,
        hammer_threshold_n=STATE.hammer_threshold_n,
        hammer_fs=STATE.hammer_fs,
        hammer_sensitivity=STATE.hammer_sensitivity_v_per_n,
        hammer_output_root=STATE.hammer_output_root,
        devices=devices,
    )


@app.route("/hammer/set_dir", methods=["POST"])
def hammer_set_dir():
    outdir = request.form.get("outdir", "").strip()
    if not outdir:
        flash("Chemin invalide", "error")
        return redirect(url_for("hammer_index"))
    outdir_abs = os.path.abspath(outdir)
    try:
        os.makedirs(outdir_abs, exist_ok=True)
    except Exception as exc:
        flash(f"Impossible de créer le dossier: {exc}", "error")
        return redirect(url_for("hammer_index"))
    STATE.hammer_output_root = outdir_abs
    flash(f"Dossier de sortie marteau défini: {STATE.hammer_output_root}", "success")
    return redirect(url_for("hammer_index"))


@app.route("/hammer/record", methods=["POST"])
def hammer_record():
    # Lire les paramètres
    dev_raw = request.form.get("device", "").strip()
    fs = int(request.form.get("fs", STATE.hammer_fs))
    sens = float(request.form.get("sens", STATE.hammer_sensitivity_v_per_n))
    threshold = float(request.form.get("threshold", STATE.hammer_threshold_n))

    device = None
    if dev_raw != "":
        try:
            device = int(dev_raw)
        except Exception:
            flash("Device index invalide", "error")
            return redirect(url_for("hammer_index"))
    else:
        # Auto-détection par nom partiel fourni par l'utilisateur
        auto_idx = _find_input_device_index_by_name("485B39")
        if auto_idx is not None:
            device = auto_idx

    # Mode attente: flux continu et détection du max au-delà du seuil
    if sens == 0:
        flash("Sensibilité ne peut pas être 0", "error")
        return redirect(url_for("hammer_index"))
    try:
        if device is not None:
            sd.default.device = device
        block_size = 2048
        global_max = 0.0
        detected = False
        with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
            while True:
                frames, overflowed = stream.read(block_size)
                volt = frames.flatten().astype(np.float64, copy=False)
                force = volt / sens
                block_max = float(np.max(np.abs(force)))
                if block_max > global_max:
                    global_max = block_max
                if global_max >= threshold:
                    detected = True
                    break
    except Exception as exc:
        flash(f"Erreur enregistrement audio: {exc}", "error")
        return redirect(url_for("hammer_index"))

    # Sauvegarde: seulement le max
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session_dir = os.path.join(STATE.hammer_output_root, ts)
    try:
        os.makedirs(session_dir, exist_ok=True)
        csv_path = os.path.join(session_dir, "force_max.csv")
        import csv
        with open(csv_path, mode="w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["threshold_N", "max_force_N", "fs_hz", "sensitivity_V_per_N", "device_index"])
            w.writerow([f"{threshold:.6f}", f"{global_max:.6f}", fs, f"{sens:.6f}", device if device is not None else "default"])
    except Exception as exc:
        flash(f"Erreur sauvegarde: {exc}", "error")
        return redirect(url_for("hammer_index"))

    # MàJ état par défaut
    STATE.hammer_device = device
    STATE.hammer_threshold_n = threshold
    STATE.hammer_fs = fs
    STATE.hammer_sensitivity_v_per_n = sens

    if detected:
        flash(f"Max détecté {global_max:.2f} N ≥ seuil {threshold:.2f} N. Sauvé dans: {session_dir}", "success")
    else:
        flash(f"Aucune détection. Max observé {global_max:.2f} N < seuil {threshold:.2f} N.", "error")
    return redirect(url_for("hammer_index"))

def create_app() -> Flask:
    return app


if __name__ == "__main__":
    # Permet de lancer rapidement: python teensy_sd_web.py --host 0.0.0.0 --port 5000
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=True)


