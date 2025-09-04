import streamlit as st
import datetime
import os
import sqlite3
import sqlalchemy
from abc import ABC, abstractmethod
from typing import List
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

#
# 1. Abstracción del Reproductor de Música (Music Player)
#
class IMusicPlayer(ABC):
    """Interfaz para un reproductor de música."""
    @abstractmethod
    def play(self, song_title: str):
        pass

class SpotifyPlayer(IMusicPlayer):
    """Implementación concreta para un reproductor de Spotify."""
    def play(self, song_title: str):
        st.info(f"Reproduciendo: **{song_title}** en Spotify...")
        st.warning("Oops, el servicio de Spotify no está disponible en este momento.")

class LocalMusicPlayerWithMetadata(IMusicPlayer):
    """Implementación que reproduce un archivo de audio local con metadatos."""
    def __init__(self):
        # Datos de canciones de ejemplo. Asegúrate de que los nombres y extensiones de los archivos coincidan.
        self.songs = [
            {"title": "The Last Point", "audio_path": "data/songs/cancion1.mp3", "album_art_path": "data/albums/album1.webp"},
            {"title": "Running Night", "audio_path": "data/songs/cancion2.mp3", "album_art_path": "data/albums/album2.webp"},
            {"title": "Retro Loungue", "audio_path": "data/songs/cancion3.mp3", "album_art_path": "data/albums/album3.webp"},
            {"title": "Vlog Beat Background", "audio_path": "data/songs/cancion4.mp3", "album_art_path": "data/albums/album4.jpg"},
            {"title": "Tell Me What", "audio_path": "data/songs/cancion5.mp3", "album_art_path": "data/albums/album5.webp"},
        ]
        
    def play(self, song_title: str):
        # Buscar la canción en los metadatos.
        song_data = next((song for song in self.songs if song["title"] == song_title), None)
        
        if song_data and os.path.exists(song_data["audio_path"]):
            st.info(f"Reproduciendo: **{song_data['title']}**")
            
            # Mostrar la imagen del álbum con un tamaño fijo para que no ocupe toda la pantalla.
            if os.path.exists(song_data["album_art_path"]):
                st.image(song_data["album_art_path"], caption=f"Álbum de {song_data['title']}", width=200)
            else:
                st.warning("Imagen del álbum no encontrada. Mostrando un marcador de posición.")
                st.image("https://placehold.co/400x400/1DB954/white?text=Sin+imagen", caption="Sin imagen de álbum", width=200)
            
            # Reproducir el audio.
            st.audio(song_data["audio_path"], format="audio/mp3", start_time=0, loop=False)
            
        else:
            st.warning(f"La canción '{song_title}' no fue encontrada o el archivo no existe.")

#
# 2. Abstracción del Repositorio de Historial (History Repository)
#
class IHistoryRepository(ABC):
    """Interfaz para un repositorio de historial de reproducciones."""
    @abstractmethod
    def save_playback(self, song_title: str):
        pass

    @abstractmethod
    def get_history(self) -> List[str]:
        pass

    @abstractmethod
    def clear_history(self):
        """Elimina todos los registros del historial."""
        pass

class SqlHistoryRepository(IHistoryRepository):
    """
    Implementación concreta para un repositorio de historial basado en SQLite.
    """
    def __init__(self, db_name="playback_history.db"):
        self.conn = sqlite3.connect(db_name)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                song_title TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_playback(self, song_title: str):
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute("INSERT INTO history (song_title, timestamp) VALUES (?, ?)", (song_title, timestamp))
        self.conn.commit()
        st.success("Historial de reproducción guardado.")

    def get_history(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [f"'{row[0]}' - {row[1]}" for row in rows]
    
    def clear_history(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM history")
        self.conn.commit()
        st.success("Historial de SQLite eliminado exitosamente.")

class MySqlHistoryRepository(IHistoryRepository):
    """Implementación concreta para un repositorio de historial basado en MySQL."""
    def __init__(self, url: str):
        self.engine = None
        self.conn = None
        try:
            # Parsear la URL para manejar credenciales con caracteres especiales
            parsed_url = urlparse(url)
            # Reconstruir la URL con el driver pymysql y un formato seguro
            db_url_safe = f"mysql+pymysql://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
            
            # Crear engine con SQLAlchemy a partir de la URL
            self.engine = create_engine(db_url_safe)
            self.conn = self.engine.connect()
            self._create_table()
            st.success("Conexión a MySQL exitosa.")
        except Exception as err:
            st.error(f"Error al conectar a MySQL: {err}")

    def _create_table(self):
        """
        Crea la tabla de historial si no existe.
        No la borra para mantener los datos.
        """
        if not self.conn:
            st.error("No se pudo crear la tabla: no hay conexión a la base de datos.")
            return

        query = text("""
            CREATE TABLE IF NOT EXISTS `history` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `song_title` VARCHAR(255) NOT NULL,
                `timestamp` DATETIME NOT NULL
            )
        """)
        try:
            self.conn.execute(query)
            self.conn.commit()
            st.success("Tabla 'history' creada exitosamente o ya existía.")
        except Exception as err:
            st.error(f"Error al crear la tabla: {err}")

    def delete_table(self, table_name: str):
        """Método para eliminar una tabla de la base de datos."""
        if not self.conn:
            st.error("No se pudo eliminar la tabla: no hay conexión a la base de datos.")
            return

        query = text(f"DROP TABLE IF EXISTS `{table_name}`")
        try:
            self.conn.execute(query)
            self.conn.commit()
            st.success(f"Tabla '{table_name}' eliminada exitosamente.")
        except Exception as err:
            st.error(f"Error al eliminar la tabla: {err}")
    
    def save_playback(self, song_title: str):
        if not self.conn:
            st.error("No se pudo guardar el historial: no hay conexión a la base de datos.")
            return

        timestamp = datetime.datetime.now()
        query = text("INSERT INTO history (song_title, timestamp) VALUES (:title, :ts)")
        try:
            self.conn.execute(query, {"title": song_title, "ts": timestamp})
            self.conn.commit()
            st.success("Historial de reproducción guardado en MySQL.")
        except Exception as err:
            st.error(f"Error al guardar el historial: {err}")

    def get_history(self) -> List[str]:
        if not self.conn:
            return []

        query = text("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
        try:
            result = self.conn.execute(query)
            # Utiliza un enfoque más seguro para obtener los valores de la fila
            rows = []
            for row in result.all():
                song_title = row.song_title
                timestamp = row.timestamp
                rows.append(f"'{song_title}' - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            return rows
        except Exception as err:
            st.error(f"Error al obtener el historial: {err}")
            return []
    
    def clear_history(self):
        if not self.conn:
            st.error("No se pudo eliminar el historial: no hay conexión a la base de datos.")
            return
        
        query = text("DELETE FROM history")
        try:
            self.conn.execute(query)
            self.conn.commit()
            st.success("Historial de MySQL eliminado exitosamente.")
        except Exception as err:
            st.error(f"Error al eliminar el historial: {err}")

#
# 3. Abstracción del Logger (Logger)
#
class ILogger(ABC):
    """Interfaz para un servicio de registro de logs."""
    @abstractmethod
    def log(self, message: str):
        pass

class FileLogger(ILogger):
    """Implementación concreta para registrar logs en un archivo de texto."""
    def __init__(self, file_path="app_logs.txt"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                f.write(f"--- Log de la Aplicación de Música ---\n")

    def log(self, message: str):
        with open(self.file_path, "a") as f:
            f.write(f"[{datetime.datetime.now()}] {message}\n")
        st.info(f"Log guardado en '{self.file_path}'")

#
# Módulos de Alto Nivel
#
class MusicService:
    """Módulo de alto nivel que depende de abstracciones, no de implementaciones."""
    def __init__(self, player: IMusicPlayer, history_repo: IHistoryRepository, logger: ILogger):
        self.player = player
        self.history_repo = history_repo
        self.logger = logger

    def play_song(self, song_title: str):
        try:
            self.logger.log(f"Iniciando la reproducción de la canción: {song_title}")
            self.player.play(song_title)
            self.history_repo.save_playback(song_title)
            self.logger.log(f"Reproducción de '{song_title}' completada y registrada.")
        except Exception as e:
            self.logger.log(f"Error al reproducir la canción: {e}")
            st.error(f"Ocurrió un error: {e}")

    def get_playback_history(self) -> List[str]:
        return self.history_repo.get_history()

#
# Configuración e Interfaz de Streamlit
#
st.set_page_config(layout="wide")

st.markdown("""
<style>
.main-header {
    font-size: 2.5em;
    font-weight: bold;
    text-align: center;
    color: #1DB954;
    padding-bottom: 20px;
}
.stButton>button {
    background-color: #1DB954;
    color: white;
    font-weight: bold;
    border-radius: 25px;
    border: none;
    padding: 10px 24px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    transition: all 0.2s ease-in-out;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(0,0,0,0.2);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 16px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.1em;
    font-weight: bold;
    color: #B3B3B3;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #1DB954;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 20px;
}
.stExpander {
    border-radius: 10px;
}
.stExpander>div>div {
    border-radius: 10px;
    border: 1px solid #1DB954;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🎵 Aplicación de Música 🎵</h1>', unsafe_allow_html=True)

# Inicializar las dependencias
logger_implementation = FileLogger()

st.sidebar.title("Configuración")
db_selection = st.sidebar.radio(
    "Selecciona la Base de Datos",
    ("SQLite", "MySQL")
)
player_selection = st.sidebar.radio(
    "Selecciona el Reproductor",
    ("Local", "Spotify (no disponible)")
)

if db_selection == "MySQL":
    try:
        db_url = st.secrets["db_credentials"]["url"]
        history_implementation = MySqlHistoryRepository(url=db_url)
    except KeyError:
        st.error("No se encontró la URL de la base de datos en los secretos de Streamlit. Por favor, configura 'db_credentials.url'.")
        history_implementation = None
else:
    history_implementation = SqlHistoryRepository()

# Seleccionar la implementación del reproductor en función de la elección del usuario
if player_selection == "Local":
    player_implementation = LocalMusicPlayerWithMetadata()
else:
    player_implementation = SpotifyPlayer()


# Crear la instancia de MusicService para usar en las pestañas
music_app = MusicService(player=player_implementation,
                         history_repo=history_implementation,
                         logger=logger_implementation)


tab1, tab2, tab3 = st.tabs(["Reproductor", "Historial y Logs", "Ajustes"])

with tab1:
    st.subheader("Reproducir una canción")
    
    if player_selection == "Local":
        song_titles = [song["title"] for song in player_implementation.songs]
        song_title = st.selectbox("Elige una canción:", song_titles)
    else:
        song_title = st.text_input("Ingresa el título de la canción:", "Bohemian Rhapsody")

    if st.button("Reproducir"):
        music_app.play_song(song_title)
        
    st.markdown("---")
    st.markdown("**Créditos de las Canciones**")
    st.info(
        "Las canciones utilizadas en esta demostración son de dominio público y provienen de Pixabay. Los autores son:\n"
        "- raspberrymusic\n"
        "- Alex_MakeMusic\n"
        "- Bransboynd\n"
        "- Tunetank\n"
        "- Denys_Brodovskyi"
    )

with tab2:
    st.subheader("Historial de Reproducciones")
    history = music_app.get_playback_history()
    
    if history:
        st.success("Historial cargado. Aquí están tus últimas reproducciones:")
        for record in history:
            st.text(record)
    else:
        st.warning("Aún no has reproducido ninguna canción.")

    st.subheader("Logs de la Aplicación")
    if os.path.exists(logger_implementation.file_path):
        with open(logger_implementation.file_path, "r") as f:
            logs = f.read()
        st.text_area("Logs del Sistema", logs, height=300)
    else:
        st.info("El archivo de logs aún no se ha creado.")

with tab3:
    st.subheader("Opciones de la Base de Datos")
    
    if st.button("Eliminar todos los registros del historial"):
        if history_implementation:
            music_app.history_repo.clear_history()
        else:
            st.warning("No se pudo conectar a la base de datos. Por favor, verifica tu configuración en la barra lateral.")
    
    st.info("Esto eliminará todas las canciones guardadas, pero mantendrá la tabla intacta.")
