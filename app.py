from flask import Flask, render_template, request, redirect, jsonify
import os
import random
from PIL import Image
import base64
import io
import json
import requests
import uuid
from datetime import datetime
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

# Configuración de Google Drive y Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive'
]

def drive_to_direct_link(url):
    """Convierte una URL de Google Drive en un enlace directo."""
    if "drive.google.com" in url:
        file_id = url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

def get_google_credentials():
    """Obtiene las credenciales de Google desde variables de entorno o archivo."""
    try:
        # Primero intenta desde variable de entorno
        if os.getenv('GOOGLE_CREDENTIALS'):
            return json.loads(os.getenv('GOOGLE_CREDENTIALS'))
        
        # Luego intenta desde la ubicación de secretos de Render
        render_credentials_path = '/etc/secrets/google-credentials.json'
        if os.path.exists(render_credentials_path):
            with open(render_credentials_path) as f:
                return json.load(f)
        
        # Finalmente, intenta desde el archivo local para desarrollo
        if os.path.exists('credentials.json'):
            with open('credentials.json') as f:
                return json.load(f)
        
        raise Exception("No se encontraron credenciales de Google")
    except Exception as e:
        raise Exception(f"Error al cargar credenciales: {str(e)}")

def refresh_image_links():
    """Actualiza el diccionario de image_links desde la hoja de cálculo."""
    try:
        if link_sheet is None:
            return {}
        rows = link_sheet.get_all_records()
        return {row['id']: (row['file_name'], drive_to_direct_link(row['url'])) for row in rows}
    except Exception as e:
        print(f"Error refreshing image links: {str(e)}")
        return {}

# Inicializar credenciales y servicios
try:
    # Get credentials as dictionary
    credentials_dict = get_google_credentials()
    
    # Initialize gspread client with credentials dictionary
    sheets_client = gspread.service_account_from_dict(credentials_dict)
    
    # Initialize drive service
    creds = service_account.Credentials.from_service_account_info(
        credentials_dict, 
        scopes=SCOPES
    )
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Configuración de hojas de cálculo
    sheet = sheets_client.open("Annotations").sheet1  
    link_sheet = sheets_client.open("LinksImagenes").sheet1
    components_sheet = sheets_client.open("Annotations").worksheet("Sheet2")
    
    # Initialize image_links
    image_links = refresh_image_links()
    
except Exception as e:
    print(f"Error al inicializar servicios de Google: {str(e)}")
    # Initialize empty variables to prevent NameError
    sheet = None
    link_sheet = None
    components_sheet = None
    image_links = {}
    drive_service = None

# ID de la carpeta en Google Drive donde se subirán las imágenes
UPLOAD_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', "1Dg2RisoHoR8xabk3rzQ8EAcWslpUN3io")

def get_components():
    """Obtiene la lista de componentes desde Google Sheets."""
    try:
        # Obtener todos los registros de la hoja de componentes
        components = components_sheet.get_all_records()
        return sorted(components, key=lambda x: x['name'])
    except Exception as e:
        print(f"Error al obtener componentes: {e}")
        return []

def add_new_component(name):
    """Agrega un nuevo componente a Google Sheets."""
    try:
        # Obtener todos los IDs existentes
        components = components_sheet.get_all_records()
        existing_names = [c['name'].lower() for c in components]
        
        # Verificar si el componente ya existe
        if name.lower() in existing_names:
            return False, "El componente ya existe"
        
        # Encontrar el siguiente ID disponible
        next_id = max([c['id'] for c in components], default=0) + 1
        
        # Agregar el nuevo componente
        components_sheet.append_row([next_id, name])
        return True, {"id": next_id, "name": name}
    except Exception as e:
        print(f"Error al agregar componente: {e}")
        return False, "Error al agregar el componente"

def get_latest_image_data():
    """Obtiene los datos de la última imagen agregada a LinksImagenes."""
    try:
        all_records = link_sheet.get_all_records()
        if not all_records:
            return None
        return max(all_records, key=lambda x: x['id'])
    except Exception as e:
        print(f"Error al obtener última imagen: {e}")
        return None

def get_image_by_id(image_id):
    """Obtiene los datos de una imagen específica desde la hoja de cálculo."""
    try:
        link_data = link_sheet.get_all_records()
        return next((row for row in link_data if row['id'] == image_id), None)
    except Exception as e:
        print(f"Error al obtener imagen por ID: {e}")
        return None

def get_direct_download_url(file_id):
    """Convierte la URL de visualización en una URL de descarga directa."""
    return f"https://drive.google.com/uc?export=view&id={file_id}"

def get_image_data(url, max_retries=3):
    """Obtiene los datos de la imagen en base64 con reintentos."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Intento {attempt + 1}: Status code {response.status_code}")
                time.sleep(2)
                continue

            image = Image.open(io.BytesIO(response.content))
            w, h = image.size
            
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_data = base64.b64encode(buffered.getvalue()).decode()
            
            return image_data, w, h
        except Exception as e:
            print(f"Intento {attempt + 1}: Error al obtener datos de imagen: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    return None, None, None

@app.route('/')
def index():
    global image_links
    
    # Check if Google services are initialized
    if link_sheet is None or sheet is None or components_sheet is None:
        return render_template("error.html", 
                            error="Error: No se pudo conectar con Google Sheets. Por favor, contacte al administrador.")
    
    # Obtener el ID de la imagen de la URL si existe
    image_id = request.args.get('image_id')
    
    try:
        if image_id:
            image_id = int(image_id)
            # Obtener datos actualizados de la imagen
            image_data = get_image_by_id(image_id)
            if not image_data:
                image_id = None
    except ValueError:
        image_id = None
    
    try:
        if not image_id and image_links:
            # Si no hay ID específico o es inválido, elegir uno aleatorio
            image_id = random.choice(list(image_links.keys()))
        elif not image_links:
            return render_template("error.html", 
                                error="No hay imágenes disponibles en el sistema.")
        
        # Actualizar image_links antes de obtener la imagen
        image_links = refresh_image_links()
        
        if image_id not in image_links:
            return render_template("error.html", 
                                error="La imagen solicitada no está disponible.")
        
        image_name, image_url = image_links[image_id]
        image_data, width, height = get_image_data(image_url)
        components = get_components()
        
        if not image_data:
            return render_template("error.html", 
                                error="No se pudo cargar la imagen. Por favor, intente con otra.")
        
        return render_template("index.html", 
                             image_data=image_data,
                             image_name=image_name,
                             width=width,
                             height=height,
                             image_id=image_id,
                             components=components)
                             
    except Exception as e:
        print(f"Error en index: {str(e)}")
        return render_template("error.html", 
                            error="Ocurrió un error al cargar la página. Por favor, intente de nuevo.")

@app.route('/add_component', methods=['POST'])
def add_component():
    """Endpoint para agregar un nuevo componente."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({"success": False, "error": "El nombre no puede estar vacío"}), 400
        
        success, result = add_new_component(name)
        
        if success:
            return jsonify({"success": True, "component": result})
        else:
            return jsonify({"success": False, "error": result}), 400
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def get_category_id(name):
    """Obtiene el ID de un componente por su nombre."""
    components = get_components()
    for component in components:
        if component['name'] == name:
            return component['id']
    return None

@app.route('/submit', methods=['POST'])
def submit():
    global image_links
    try:
        # Obtener y validar los datos del formulario
        image_id = int(request.form['image_id'])
        width = int(request.form['width'])
        height = int(request.form['height'])
        
        # Obtener datos actualizados de la imagen
        current_image = get_image_by_id(image_id)
        if not current_image:
            print(f"Error: No se encontró la imagen con ID {image_id} en LinksImagenes")
            return jsonify({'success': False, 'error': 'Imagen no encontrada en la hoja de datos'}), 400
        
        # Usar los datos exactos de la hoja
        image_id = current_image['id']
        image_name = current_image['file_name']
        
        annotations = json.loads(request.form.get('annotations', '[]'))
        
        if not annotations:
            # Si no hay anotaciones, redirigir a una imagen aleatoria
            available_ids = list(image_links.keys())
            if available_ids:
                random_id = random.choice([id for id in available_ids if id != image_id])
                return redirect(f'/?image_id={random_id}')
            return redirect('/')
        
        # Validar que todas las cajas tengan componente y estado
        for annotation in annotations:
            if not annotation['component'] or not annotation['estado']:
                return "<h3>Error: Todas las cajas deben tener un componente y estado seleccionados. <a href='javascript:history.back()'>Volver</a></h3>"
        
        print(f"Guardando anotaciones para imagen {image_id} ({image_name})")
        
        # Guardar cada anotación en la hoja de cálculo
        for idx, annotation in enumerate(annotations):
            annotation_id = len(sheet.get_all_values())
            category_id = get_category_id(annotation['component'])
            
            sheet.append_row([
                annotation_id,
                image_id,
                image_name,
                width,
                height,
                category_id,
                annotation['component'],
                annotation['estado'],
                annotation['estado_operativo'],
                annotation['analisis'],
                annotation['x'],
                annotation['y'],
                annotation['width'],
                annotation['height'],
                datetime.now().isoformat()
            ])
        
        # Actualizar image_links después de guardar
        image_links = refresh_image_links()
        
        # Redirigir a una imagen aleatoria diferente
        available_ids = list(image_links.keys())
        if available_ids:
            random_id = random.choice([id for id in available_ids if id != image_id])
            return redirect(f'/?image_id={random_id}')
        return redirect('/')
        
    except Exception as e:
        print(f"Error en submit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_or_create_folder(folder_path):
    """Obtiene o crea la carpeta en Google Drive."""
    try:
        # Separar la ruta en partes
        parts = folder_path.split('/')
        parent_id = 'root'
        current_folder_id = None

        for part in parts:
            # Buscar la carpeta actual
            query = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
            results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            items = results.get('files', [])

            if not items:
                # Crear la carpeta si no existe
                folder_metadata = {
                    'name': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                current_folder_id = folder.get('id')
            else:
                current_folder_id = items[0]['id']

            parent_id = current_folder_id

        return current_folder_id
    except Exception as e:
        print(f"Error al crear/obtener carpeta: {e}")
        return None

def upload_to_drive(file_data, filename):
    """Sube un archivo a Google Drive y devuelve su URL."""
    try:
        folder_id = UPLOAD_FOLDER_ID

        # Asegurarse de que el archivo sea una imagen válida y convertirla a JPEG
        try:
            image = Image.open(io.BytesIO(file_data))
            # Convertir a JPEG
            buffered = io.BytesIO()
            image.convert('RGB').save(buffered, format="JPEG")
            file_data = buffered.getvalue()
        except Exception as e:
            print(f"Error al procesar imagen: {e}")
            return None, None, None

        # Preparar el archivo para subir
        fh = io.BytesIO(file_data)
        media = MediaIoBaseUpload(fh, mimetype='image/jpeg', resumable=True)

        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }

        # Subir el archivo
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')

        # Crear el enlace compartido
        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()

        # Generar ambas URLs
        view_url = f"https://drive.google.com/file/d/{file_id}/view"
        download_url = get_direct_download_url(file_id)
        
        return view_url, download_url, file_id

    except Exception as e:
        print(f"Error al subir archivo: {e}")
        return None, None, None

def add_image_to_sheet(filename, url):
    """Agrega una nueva imagen a la hoja de enlaces."""
    try:
        # Generar ID único
        unique_id = len(link_sheet.get_all_records()) + 1
        
        # Agregar nueva fila
        link_sheet.append_row([
            unique_id,
            filename,
            url
        ])
        
        return unique_id
    except Exception as e:
        print(f"Error al agregar imagen a la hoja: {e}")
        return None

@app.route('/upload', methods=['POST'])
def upload_file():
    global image_links
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400

        if file:
            # Leer el archivo y verificar que sea una imagen válida
            file_data = file.read()
            try:
                Image.open(io.BytesIO(file_data))
            except Exception as e:
                return jsonify({'success': False, 'error': 'Archivo no es una imagen válida'}), 400

            # Subir a Google Drive
            view_url, download_url, file_id = upload_to_drive(file_data, file.filename)
            if not view_url:
                return jsonify({'success': False, 'error': 'Error uploading to Drive'}), 500

            # Agregar a la hoja de cálculo (usar view_url para almacenar)
            image_id = add_image_to_sheet(file.filename, view_url)
            if not image_id:
                return jsonify({'success': False, 'error': 'Error adding to sheet'}), 500

            # Esperar un momento para que la hoja se actualice
            time.sleep(2)
            
            # Obtener los datos exactos de la imagen recién subida
            current_image = get_image_by_id(image_id)
            if not current_image:
                return jsonify({'success': False, 'error': 'Error retrieving image data from sheet'}), 500

            # Obtener los datos de la imagen para mostrarla
            image_data, width, height = get_image_data(drive_to_direct_link(current_image['url']))
            
            if not image_data:
                # Si falla, intentar usar los datos originales del archivo
                try:
                    image = Image.open(io.BytesIO(file_data))
                    w, h = image.size
                    buffered = io.BytesIO()
                    image.save(buffered, format="JPEG")
                    image_data = base64.b64encode(buffered.getvalue()).decode()
                    width, height = w, h
                except Exception as e:
                    print(f"Error al usar datos originales: {e}")
                    return jsonify({'success': False, 'error': 'Error processing image data'}), 500

            # Actualizar image_links después de subir la nueva imagen
            image_links = refresh_image_links()

            # Devolver los datos exactos de la imagen recién subida
            return jsonify({
                'success': True,
                'image_id': current_image['id'],
                'filename': current_image['file_name'],
                'url': current_image['url'],
                'image_data': image_data,
                'width': width,
                'height': height,
                'redirect_url': f'/?image_id={current_image["id"]}'  # URL para redirección
            })

    except Exception as e:
        print(f"Error en upload_file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
