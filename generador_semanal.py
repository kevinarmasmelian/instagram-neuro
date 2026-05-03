"""
Generador Semanal de Contenido para Instagram
Dr. Kevin Armas Melián — @kevinarmas_neurocirugiacanaria

Este script se ejecuta automáticamente cada semana via GitHub Actions.
Busca un artículo en PubMed, genera el contenido con IA y lo envía por email.
"""

import os
import re
import time
import requests
from groq import Groq
import resend

# ─────────────────────────────────────────────
# CONFIGURACIÓN — Se lee desde GitHub Secrets
# ─────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_DESTINO  = os.environ.get("EMAIL_DESTINO", "kevinarmasmelian@gmail.com")

# Lista de temas que rotan cada semana
TEMAS = [
    "minimally invasive spine surgery",
    "brain tumor glioblastoma treatment",
    "cervical disc herniation surgery",
    "deep brain stimulation Parkinson",
    "intracranial aneurysm endovascular",
    "artificial intelligence neurosurgery",
    "lumbar stenosis endoscopic treatment",
    "neuroscience chronic pain mechanisms",
    "robotic spine surgery outcomes",
    "trigeminal neuralgia microsurgery",
    "spinal cord injury rehabilitation",
    "Chiari malformation surgery",
    "normal pressure hydrocephalus treatment",
    "vestibular schwannoma radiosurgery",
    "carpal tunnel syndrome treatment",
]

# Seleccionar tema según la semana del año (rota automáticamente)
from datetime import datetime
TEMA_MANUAL = os.environ.get("TEMA_MANUAL", "").strip()

if TEMA_MANUAL:
    TEMA = TEMA_MANUAL
    print(f"✏️  Tema elegido manualmente: {TEMA}")
else:
    semana_del_año = datetime.now().isocalendar()[1]
    TEMA = TEMAS[semana_del_año % len(TEMAS)]
    print(f"🗓️  Semana {semana_del_año} — Tema automático: {TEMA}")
print(f"🗓️  Semana {semana_del_año} — Tema: {TEMA}")


# ─────────────────────────────────────────────
# FUNCIÓN 1: Buscar paper en PubMed
# ─────────────────────────────────────────────
def buscar_paper_pubmed(tema):
    print(f"\n🔍 Buscando en PubMed: '{tema}'...")
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed", "term": tema, "retmax": 5,
        "sort": "pub+date", "retmode": "json",
        "datetype": "pdat", "reldate": 730
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        ids = r.json()["esearchresult"]["idlist"]
        if not ids:
            print("❌ No se encontraron artículos.")
            return None
        print(f"✅ {len(ids)} artículos encontrados")

        for pubmed_id in ids:
            r2 = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params={"db": "pubmed", "id": pubmed_id, "rettype": "abstract", "retmode": "xml"},
                timeout=15
            )
            xml = r2.text
            def limpiar(t): return re.sub(r"<[^>]+>", "", t).strip()
            titulo    = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", xml, re.DOTALL)
            abstracts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.DOTALL)
            autores   = re.findall(r"<LastName>(.*?)</LastName>", xml)
            año       = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", xml, re.DOTALL)
            revista   = re.search(r"<ISOAbbreviation>(.*?)</ISOAbbreviation>", xml, re.DOTALL)
            abstract_txt = " ".join([limpiar(a) for a in abstracts]) if abstracts else ""
            if not abstract_txt:
                continue
            paper = {
                "id": pubmed_id,
                "titulo": limpiar(titulo.group(1)) if titulo else "Sin título",
                "abstract": abstract_txt,
                "autores": ", ".join(autores[:3]) + (" et al." if len(autores) > 3 else "") if autores else "Desconocidos",
                "año": año.group(1) if año else "2025",
                "revista": limpiar(revista.group(1)) if revista else "Revista científica",
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
            }
            print(f"📄 Paper: {paper['titulo'][:70]}...")
            return paper
            time.sleep(0.4)
    except Exception as e:
        print(f"❌ Error PubMed: {e}")
    return None


# ─────────────────────────────────────────────
# FUNCIÓN 2: Generar contenido con Groq
# ─────────────────────────────────────────────
def generar_contenido(paper):
    print("\n🤖 Generando contenido con IA...")
    sistema = (
        "Eres el asistente del Dr. Kevin Armas Melián, neurocirujano en Las Palmas de Gran Canaria "
        "(@kevinarmas_neurocirugiacanaria). Crea contenido VIRAL para Instagram, riguroso científicamente "
        "y accesible al público general hispanohablante. NUNCA menciones pacientes ni datos privados. "
        "Responde SIEMPRE en español de España."
    )
    mensaje = f"""Paper de PubMed:
TÍTULO: {paper['titulo']}
AUTORES: {paper['autores']} ({paper['año']})
REVISTA: {paper['revista']}
ABSTRACT: {paper['abstract'][:2000]}

Genera en español:

---HOOK---
(Frase de máximo 12 palabras que detenga el scroll. Sin emojis.)

---CAPTION---
(150-200 palabras. Explica el hallazgo de forma sencilla con emojis estratégicos.
Termina con: «Fuente: {paper['revista']}, {paper['año']} | 🔗 Link en bio»
y luego: «¿Te ha sido útil? Guarda este post 💾 y compártelo.»)

---SLIDES---
Slide 1: [TÍTULO EN MAYÚSCULAS] | [2-3 frases explicativas]
Slide 2: [TÍTULO EN MAYÚSCULAS] | [2-3 frases explicativas]
Slide 3: [TÍTULO EN MAYÚSCULAS] | [2-3 frases explicativas]
Slide 4: [TÍTULO EN MAYÚSCULAS] | [2-3 frases explicativas]
Slide 5: [TÍTULO EN MAYÚSCULAS] | [2-3 frases explicativas]
Slide 6: [TÍTULO EN MAYÚSCULAS] | [conclusión y llamada a la acción]

---HASHTAGS---
(15 hashtags en español e inglés, mezcla de populares y de nicho)"""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": mensaje}
            ],
            max_tokens=1800, temperature=0.75
        )
        texto = resp.choices[0].message.content
        if texto and len(texto) > 200:
            print("✅ Contenido generado correctamente")
            return texto
    except Exception as e:
        print(f"❌ Error Groq: {e}")
    return None


# ─────────────────────────────────────────────
# FUNCIÓN 3: Enviar email con el contenido
# ─────────────────────────────────────────────
def enviar_email(contenido, paper):
    print("\n📧 Enviando email...")
    resend.api_key = RESEND_API_KEY

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px;">

      <h1 style="color: #6c3fc6;">🧠 Post semanal listo para Instagram</h1>
      <p style="color: #666;">Dr. Kevin Armas — @kevinarmas_neurocirugiacanaria</p>

      <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <strong>📰 Artículo base:</strong> {paper['titulo']}<br>
        <strong>📖 Revista:</strong> {paper['revista']} ({paper['año']})<br>
        <strong>🔗 PubMed:</strong> <a href="{paper['link']}">{paper['link']}</a>
      </div>

      <hr style="border: 1px solid #ddd; margin: 20px 0;">

      <div style="white-space: pre-wrap; background: #fff; padding: 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; line-height: 1.6;">
{contenido}
      </div>

      <hr style="border: 1px solid #ddd; margin: 20px 0;">

      <div style="background: #6c3fc6; color: white; padding: 15px; border-radius: 8px;">
        <strong>📋 Pasos a seguir:</strong><br><br>
        1. Copie el HOOK, CAPTION y HASHTAGS<br>
        2. Abra <strong>Postiz</strong> → Crear publicación<br>
        3. Pegue el texto y añada sus fotos<br>
        4. Programe la publicación y guarde como borrador<br>
        5. Revise y publique cuando quiera ✅
      </div>

    </div>
    """

    try:
        params = {
            "from": "neurocirugiacanarias@resend.dev",
            "to": [EMAIL_DESTINO],
            "subject": f"🧠 Post Instagram listo — {paper['titulo'][:50]}...",
            "html": html,
        }
        email = resend.Emails.send(params)
        print(f"✅ Email enviado a {EMAIL_DESTINO}")
        return True
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False


# ─────────────────────────────────────────────
# EJECUCIÓN PRINCIPAL
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  🧠 GENERADOR SEMANAL — Dr. Kevin Armas")
    print("=" * 55)

    # 1. Buscar paper
    paper = buscar_paper_pubmed(TEMA)
    if not paper:
        print("❌ No se encontró artículo. Terminando.")
        exit(1)

    # 2. Generar contenido
    contenido = generar_contenido(paper)
    if not contenido:
        print("❌ No se pudo generar contenido. Terminando.")
        exit(1)

    # 3. Mostrar contenido
    print("\n" + "=" * 55)
    print(contenido)
    print("=" * 55)

    # 4. Enviar email
    enviar_email(contenido, paper)

    print("\n🎊 ¡Proceso completado! Revise su email.")
