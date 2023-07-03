# SongSearchAPI
## Descripción

Este proyecto es una API que integra tres servicios de música distintos: Spotify, iTunes y Genius. Permite buscar canciones y proporciona información relevante de las canciones de estos tres proveedores.

## Instalación

Para ejecutar este proyecto localmente usando Docker, sigue estos pasos:

1. Clona este repositorio en tu máquina local.
2. Asegúrate de tener Docker instalado en tu sistema. Puedes descargar Docker desde [aquí](https://www.docker.com/products/docker-desktop/).
3. Crea un archivo .env en el directorio raíz del proyecto y agrega las siguientes variables de entorno con los valores apropiados:
```bash
SECRET_KEY=<secret key>
SPOTIFY_CLIENT_ID=<tu client id de Spotify>
SPOTIFY_CLIENT_SECRET=<tu client secret de Spotify>
GENIUS_CLIENT_ID=<tu client id de Genius>
GENIUS_CLIENT_SECRET=<tu client secret de Genius>
```

1. Construye la imagen de Docker con el comando
```bash
docker build -t song-search-api .
```

2. ecuta el contenedor de Docker con el comando
```bash
docker run -p 8000:8000 song-search-api
```
La API debería estar disponible en ***localhost:8000***.

## API reference
Puedes encontrarlo en 
```bash
http://localhost:8000/api/docs/
```

## Uso
Para buscar canciones, realiza una solicitud GET a la ruta ***api/song*** con el parámetro de consulta *search_term*. Por ejemplo, para buscar canciones que se llamen 'sailing', puedes usar la URL 
```bash
http://localhost:8000/api/song?search_term=sailing
```

También puedes filtrar las canciones por el álbum y el género utilizando los parámetros de consulta:

*album* 
```bash
http://localhost:8000/api/song/?search_term=Sailing&album=Christopher Cross
```
*genre*

```bash
http://localhost:8000/api/song/?search_term=Sailing&genre=soft rock
```
*ambos*
```bash
http://localhost:8000/api/song/?search_term=Sailing&album=Christopher Cross&genre=soft rock
```