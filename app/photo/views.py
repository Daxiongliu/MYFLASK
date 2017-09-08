from flask import render_template, request, url_for, send_from_directory, current_app, flash
from werkzeug.utils import secure_filename
from . import photo

import os

ALLOWED_EXTENSIONS = set(['png', 'ipg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@photo.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config.get('UPLOAD_FOLDER'), filename)

@photo.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config.get('UPLOAD_FOLDER'), filename))
            file_url = url_for('photo.uploaded_file', filename=filename)
            flash('You have upload a photo!')
            return render_template('photo/photowall.html')
        else:
            flash("This file can't upload!")
    return render_template('photo/photowall.html')