import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
# ... (mantenir els altres imports de reportlab que ja tenies)

# 1. Credencials des dels Secrets de Streamlit
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

# 2. Configuració de l'OAuth per llegir la biblioteca
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-read-private playlist-read-collaborative",
    show_dialog=True
)

# --- LOGÍSTICA DE LOGIN ---
if "code" in st.query_params:
    token_info = sp_oauth.get_access_token(st.query_params["code"])
    st.session_state["access_token"] = token_info["access_token"]
    st.query_params.clear()
    st.rerun()

if "access_token" not in st.session_state:
    st.title("🎵 El teu Bingo Musical")
    st.write("Inicia sessió per veure les teves llistes de Spotify.")
    auth_url = sp_oauth.get_authorize_url()
    st.link_button("🔑 Entrar amb Spotify", auth_url)
    st.stop()

sp = spotipy.Spotify(auth=st.session_state["access_token"])

# --- INTERFÍCIE PRINCIPAL ---
st.title("🎯 Genera el teu Bingo")

try:
    # Obtenim les llistes de l'usuari loguejat
    user_playlists = sp.current_user_playlists()
    playlists_dict = {p['name']: p['id'] for p in user_playlists['items']}
    
    nom_llista = st.selectbox("Tria una de les teves llistes:", list(playlists_dict.keys()))
    playlist_id = playlists_dict[nom_llista]

    if st.button("Carregar cançons de la llista"):
        results = sp.playlist_items(playlist_id)
        # ... aquí aniria la teva lògica per extreure cançons i generar el PDF
        st.success(f"Llista '{nom_llista}' carregada!")
        
except Exception as e:
    st.error(f"Error al carregar la biblioteca: {e}")
    if st.button("Re-connectar"):
        del st.session_state["access_token"]
        st.rerun()