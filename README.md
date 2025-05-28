# Sistema de Etiquetado de Infraestructura - SUNASS

Sistema web para el etiquetado y anotación de imágenes de infraestructura.

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación Local

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd captcha-labeler
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus valores
```

5. Ejecutar la aplicación:
```bash
flask run
```

## Despliegue en Render

1. Crear una nueva aplicación web en Render
2. Conectar con el repositorio de GitHub
3. Configurar las siguientes opciones:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c gunicorn_config.py app:app`
   - **Plan**: Free o superior

4. Configurar las variables de entorno en Render:
   - `FLASK_ENV`: production
   - `SECRET_KEY`: [tu-clave-secreta]
   - `UPLOAD_FOLDER`: uploads
   - `MAX_CONTENT_LENGTH`: 16777216

5. Hacer clic en "Create Web Service"

## Estructura del Proyecto

```
captcha-labeler/
├── app.py
├── gunicorn_config.py
├── Procfile
├── requirements.txt
├── .env
├── .gitignore
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── annotations.js
│       ├── upload.js
│       └── components.js
├── templates/
│   └── index.html
└── uploads/
    └── .gitkeep
```

## Variables de Entorno

Crear un archivo `.env` con las siguientes variables:

```
FLASK_ENV=development
FLASK_APP=app.py
SECRET_KEY=your-secret-key-here
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

## Mantenimiento

- Los logs se pueden ver en el dashboard de Render
- Las actualizaciones se despliegan automáticamente al hacer push al repositorio
- El servicio se reinicia automáticamente si hay problemas

## Seguridad

- No subir el archivo `.env` al repositorio
- Mantener el `SECRET_KEY` seguro y único para cada ambiente
- Revisar regularmente las dependencias por actualizaciones de seguridad 