import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, FrameBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.pdfgen import canvas as rl_canvas
import random
import io

CLIENT_ID     = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
REDIRECT_URI  = st.secrets["SPOTIFY_REDIRECT_URI"]

SCOPE = "playlist-read-private playlist-read-collaborative"


def get_spotify_client():
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=spotipy.cache_handler.MemoryCacheHandler(
            token_info=st.session_state.get("token_info")
        ),
        show_dialog=False
    )

    query_params = st.query_params
    if "code" in query_params and "token_info" not in st.session_state:
        code = query_params["code"]
        token_info = auth_manager.get_access_token(code, as_dict=True, check_cache=False)
        st.session_state["token_info"] = token_info
        st.query_params.clear()
        st.rerun()

    if "token_info" not in st.session_state:
        auth_url = auth_manager.get_authorize_url()
        st.title("🎵 Generador de Bingo Musical")
        st.markdown("Per accedir a qualsevol playlist pública, cal que t'autentiquis amb Spotify.")
        st.link_button("🔗 Connectar amb Spotify", auth_url)
        st.stop()

    if auth_manager.is_token_expired(st.session_state["token_info"]):
        token_info = auth_manager.refresh_access_token(
            st.session_state["token_info"]["refresh_token"]
        )
        st.session_state["token_info"] = token_info

    return spotipy.Spotify(auth_manager=auth_manager)


# ── PDF llista de cançons ─────────────────────────────────────────────────────
def generar_pdf(titol_event, cancons):
    buffer = io.BytesIO()
    page_w, page_h = A4
    marge = 2 * cm
    col_gap = 0.8 * cm
    col_w = (page_w - 2 * marge - col_gap) / 2
    titol_h = 2.5 * cm
    frame_titol = Frame(marge, page_h - marge - titol_h, page_w - 2*marge, titol_h, id='titol')
    col_h = page_h - 2*marge - titol_h - 0.3*cm
    frame_esq = Frame(marge, marge, col_w, col_h, id='col_esq')
    frame_dre = Frame(marge + col_w + col_gap, marge, col_w, col_h, id='col_dre')
    doc = BaseDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates([PageTemplate(id='TwoCol', frames=[frame_titol, frame_esq, frame_dre])])
    styles = getSampleStyleSheet()
    estil_titol = ParagraphStyle('Titol', parent=styles['Title'], fontSize=20, spaceAfter=0,
        textColor=colors.black, fontName='Helvetica-Bold')
    estil_canco = ParagraphStyle('Canco', parent=styles['Normal'], fontSize=9, leading=13, fontName='Helvetica')
    story = [Paragraph(titol_event, estil_titol), FrameBreak()]
    meitat = (len(cancons) + 1) // 2
    for i, nom in enumerate(cancons, 1):
        if ' – ' in nom:
            titol, artista = nom.split(' – ', 1)
            text = f"{i}. {titol} – <i>{artista}</i>"
        else:
            text = f"{i}. {nom}"
        story.append(Paragraph(text, estil_canco))
        if i == meitat:
            story.append(FrameBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer


# ── Helpers comuns per als cartrons ──────────────────────────────────────────
def _setup_cartro(page_w, page_h):
    COLS_GRID, FILES_GRID = 4, 4
    marge_ext = 0.8 * cm
    col_gap   = 0.4 * cm
    fila_gap  = 0.5 * cm
    capçalera = 0.45 * cm
    cartro_w = (page_w - 2 * marge_ext - col_gap) / 2
    cartro_h = (page_h - 2 * marge_ext - 2 * fila_gap - 3 * capçalera) / 3
    cel_w = cartro_w / COLS_GRID
    cel_h = cartro_h / FILES_GRID
    return COLS_GRID, FILES_GRID, marge_ext, col_gap, fila_gap, capçalera, cartro_w, cartro_h, cel_w, cel_h


def _posicio(slot, marge_ext, cartro_w, col_gap, capçalera, cartro_h, fila_gap, page_h):
    col_i  = slot % 2
    fila_i = slot // 2
    x0 = marge_ext + col_i * (cartro_w + col_gap)
    y0 = page_h - marge_ext - capçalera - (fila_i + 1) * cartro_h - fila_i * (fila_gap + capçalera)
    return x0, y0


def _genera_cartrons_unics(num_cancons, num_cartrons):
    cartrons_generats = set()
    cartrons = []
    for _ in range(num_cartrons):
        for _ in range(10000):
            nums = tuple(random.sample(range(1, num_cancons + 1), 16))
            clau = tuple(sorted(nums))
            if clau not in cartrons_generats:
                cartrons_generats.add(clau)
                cartrons.append(list(nums))
                break
    return cartrons


# ── PDF cartrons amb NÚMEROS ──────────────────────────────────────────────────
def generar_cartrons_nums(titol_event, num_cancons, num_cartrons):
    buffer = io.BytesIO()
    page_w, page_h = A4
    c = rl_canvas.Canvas(buffer, pagesize=A4)

    COLS_GRID, FILES_GRID, marge_ext, col_gap, fila_gap, capçalera, cartro_w, cartro_h, cel_w, cel_h = _setup_cartro(page_w, page_h)

    color_clar  = colors.HexColor('#dce9f7')
    color_fosc  = colors.HexColor('#b8d0ed')
    color_borde = colors.HexColor('#5a8fc2')
    color_petit = colors.HexColor('#5a8fc2')

    def dibuixa_cartro(c, x0, y0, numeros, num_cartro):
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(color_petit)
        c.drawString(x0, y0 + cartro_h + 2, f"Cartró nº {num_cartro}  |  {titol_event}")

        for idx, num in enumerate(numeros):
            ci = idx % COLS_GRID
            fi = idx // COLS_GRID
            cx = x0 + ci * cel_w
            cy = y0 + cartro_h - (fi + 1) * cel_h

            c.setFillColor(color_clar if (ci + fi) % 2 == 0 else color_fosc)
            c.rect(cx, cy, cel_w, cel_h, fill=1, stroke=0)
            c.setStrokeColor(color_borde)
            c.setLineWidth(0.5)
            c.rect(cx, cy, cel_w, cel_h, fill=0, stroke=1)

            mida_petit = 8
            c.setFillColor(color_petit)
            c.setFont('Helvetica', mida_petit)
            c.drawString(cx + 3, cy + cel_h - mida_petit - 2, str(num))

            mida_gran = int(cel_h * 0.55)
            c.setFont('Helvetica-Bold', mida_gran)
            c.setFillColor(colors.black)
            c.drawCentredString(cx + cel_w / 2, cy + (cel_h - mida_gran) / 2, str(num))

        c.setStrokeColor(color_borde)
        c.setLineWidth(1.5)
        c.rect(x0, y0, cartro_w, cartro_h, fill=0, stroke=1)

    cartrons = _genera_cartrons_unics(num_cancons, num_cartrons)
    for i, nums in enumerate(cartrons):
        slot = i % 6
        if slot == 0 and i > 0:
            c.showPage()
        x0, y0 = _posicio(slot, marge_ext, cartro_w, col_gap, capçalera, cartro_h, fila_gap, page_h)
        dibuixa_cartro(c, x0, y0, nums, i + 1)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ── PDF cartrons amb TÍTOLS de cançons ───────────────────────────────────────
def generar_cartrons_text(titol_event, cancons_tuples, num_cartrons):
    """cancons_tuples: llista de (nom, artista) en ordre de la playlist (index 0 = cançó 1)"""
    buffer = io.BytesIO()
    page_w, page_h = A4
    c = rl_canvas.Canvas(buffer, pagesize=A4)

    COLS_GRID, FILES_GRID, marge_ext, col_gap, fila_gap, capçalera, cartro_w, cartro_h, cel_w, cel_h = _setup_cartro(page_w, page_h)

    color_clar  = colors.HexColor('#dce9f7')
    color_fosc  = colors.HexColor('#b8d0ed')
    color_borde = colors.HexColor('#5a8fc2')
    color_cap   = colors.HexColor('#5a8fc2')

    num_cancons = len(cancons_tuples)

    def dibuixa_cartro_text(c, x0, y0, numeros, num_cartro):
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(color_cap)
        c.drawString(x0, y0 + cartro_h + 2, f"Cartró nº {num_cartro}  |  {titol_event}")

        for idx, num in enumerate(numeros):
            ci = idx % COLS_GRID
            fi = idx // COLS_GRID
            cx = x0 + ci * cel_w
            cy = y0 + cartro_h - (fi + 1) * cel_h

            c.setFillColor(color_clar if (ci + fi) % 2 == 0 else color_fosc)
            c.rect(cx, cy, cel_w, cel_h, fill=1, stroke=0)
            c.setStrokeColor(color_borde)
            c.setLineWidth(0.5)
            c.rect(cx, cy, cel_w, cel_h, fill=0, stroke=1)

            nom, artista = cancons_tuples[num - 1]

            padding = 4
            max_w = cel_w - 2 * padding
            mida_nom = 7.5
            mida_art = 6

            def wrap_text(text, font, mida, max_w):
                words = text.split()
                lines = []
                current = ''
                for word in words:
                    test = (current + ' ' + word).strip()
                    if c.stringWidth(test, font, mida) <= max_w:
                        current = test
                    else:
                        if current:
                            lines.append(current)
                        current = word
                if current:
                    lines.append(current)
                return lines

            nom_lines = wrap_text(nom, 'Helvetica-Bold', mida_nom, max_w)
            art_lines = wrap_text(artista, 'Helvetica', mida_art, max_w) if artista else []

            lh_nom = mida_nom + 1.5
            lh_art = mida_art + 1.5
            total_h = len(nom_lines) * lh_nom + (len(art_lines) * lh_art + 2 if art_lines else 0)

            y_start = cy + (cel_h + total_h) / 2

            c.setFont('Helvetica-Bold', mida_nom)
            c.setFillColor(colors.black)
            for line in nom_lines:
                y_start -= lh_nom
                c.drawCentredString(cx + cel_w / 2, y_start, line)

            if art_lines:
                y_start -= 2
                c.setFont('Helvetica', mida_art)
                c.setFillColor(colors.HexColor('#333333'))
                for line in art_lines:
                    y_start -= lh_art
                    c.drawCentredString(cx + cel_w / 2, y_start, line)

        c.setStrokeColor(color_borde)
        c.setLineWidth(1.5)
        c.rect(x0, y0, cartro_w, cartro_h, fill=0, stroke=1)

    cartrons = _genera_cartrons_unics(num_cancons, num_cartrons)
    for i, nums in enumerate(cartrons):
        slot = i % 6
        if slot == 0 and i > 0:
            c.showPage()
        x0, y0 = _posicio(slot, marge_ext, cartro_w, col_gap, capçalera, cartro_h, fila_gap, page_h)
        dibuixa_cartro_text(c, x0, y0, nums, i + 1)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ── Interfície Streamlit ──────────────────────────────────────────────────────
sp = get_spotify_client()

with st.sidebar:
    if st.button("🔓 Desconnectar Spotify"):
        del st.session_state["token_info"]
        st.rerun()

st.title("🎵 Generador de Bingo Musical")
st.write("Enganxa una playlist de Spotify i genera la llista i els cartrons de bingo.")

titol_event = st.text_input("Títol de l'esdeveniment:", placeholder="Ex: Vermut AEIG Sant Pius Xè")
st.info("⚠️ La playlist ha de ser de la teva biblioteca de Spotify (creada o guardada al teu compte). Les playlists d'altres usuaris no són accessibles per restriccions de l'API de Spotify.\nPer guardar-la al teu compte, fes clic als tres punts de la playlist -> Afegeix a una altra llista -> Nova llista")
playlist_url = st.text_input("URL de la Playlist de Spotify:")
if playlist_url:
    try:
        if 'cancons_editables' not in st.session_state or st.session_state.get('ultima_url') != playlist_url:
            cancons_raw = []
            cancons_tuples = []
            results = sp.playlist_items(playlist_url, market="ES")
            while results:
                for element in results['items']:
                    track = element.get('item') or element.get('track')
                    if track and track.get('type') == 'track':
                        nom = track.get('name', 'Desconegut')
                        artista = track['artists'][0]['name'] if track.get('artists') else ''
                        cancons_raw.append(f"{nom} – {artista}" if artista else nom)
                        cancons_tuples.append((nom, artista))
                results = sp.next(results) if results.get('next') else None
            st.session_state['cancons_editables'] = cancons_raw
            st.session_state['cancons_tuples']    = cancons_tuples
            st.session_state['ultima_url']         = playlist_url

        cancons = st.session_state['cancons_editables']
        st.success(f"S'han trobat {len(cancons)} cançons!")

        st.subheader("✏️ Edita la llista")
        st.caption("Pots modificar qualsevol nom abans de generar el PDF.")
        cancons_editades = []
        for i, nom in enumerate(cancons):
            nou_nom = st.text_input(f"{i+1}.", value=nom, key=f"canco_{i}", label_visibility="visible")
            cancons_editades.append(nou_nom)
        st.session_state['cancons_editables'] = cancons_editades

        st.divider()

        # PDF llista
        st.subheader("📄 PDF llista de cançons")
        if st.button("Generar PDF llista"):
            if not titol_event.strip():
                st.warning("Si us plau, escriu el títol de l'esdeveniment.")
            else:
                st.session_state['pdf_llista'] = generar_pdf(titol_event, cancons_editades).read()

        if 'pdf_llista' in st.session_state:
            st.download_button("⬇️ Descarregar llista PDF", data=st.session_state['pdf_llista'],
                file_name="llista_cancons_bingo.pdf", mime="application/pdf", key="dl_llista")

        st.divider()

        # Cartrons
        st.subheader("🎴 Generar cartrons de bingo")
        st.caption("Cada cartró té 16 caselles (graella 4×4). Surten 6 cartrons per pàgina.")
        num_cartrons = st.number_input("Quants cartrons?", min_value=1, max_value=500, value=12)

        if st.button("🎴 Generar cartrons"):
            if not titol_event.strip():
                st.warning("Si us plau, escriu el títol de l'esdeveniment.")
            elif len(cancons_editades) < 16:
                st.warning("Cal tenir almenys 16 cançons a la llista.")
            else:
                num_cancons = len(cancons_editades)
                cancons_tuples = st.session_state.get('cancons_tuples', [(c, '') for c in cancons_editades])
                st.session_state['pdf_nums'] = generar_cartrons_nums(titol_event, num_cancons, num_cartrons).read()
                st.session_state['pdf_text'] = generar_cartrons_text(titol_event, cancons_tuples, num_cartrons).read()

        if 'pdf_nums' in st.session_state:
            st.download_button("⬇️ Descarregar cartrons amb números", data=st.session_state['pdf_nums'],
                file_name="cartrons_numeros.pdf", mime="application/pdf", key="dl_nums")
        if 'pdf_text' in st.session_state:
            st.download_button("⬇️ Descarregar cartrons amb títols", data=st.session_state['pdf_text'],
                file_name="cartrons_titols.pdf", mime="application/pdf", key="dl_text")
    except Exception as e:
        st.error(f"Error: {e}")