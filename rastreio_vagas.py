import os
import time
import requests
import pandas as pd
import gspread
import schedule
from dotenv import load_dotenv

# === CONFIG ===
load_dotenv()

GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN_VAGAS")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_VAGAS")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

REMOTIVE_API = "https://remotive.io/api/remote-jobs"
ADZUNA_API_BASE = "https://api.adzuna.com/v1/api/jobs"

# === RECRIA credentials.json COM BASE NA ENV ===
if os.getenv("GOOGLE_CREDENTIALS_JSON"):
    with open("credentials.json", "w") as f:
        f.write(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === BUSCAS DEFINIDAS ===
REGIOES_INTERESSE = [
    "brazil", "latam", "latin america", "south america",
    "central america", "north america"
]

SEARCH_CONFIG = {
    "Frontend": ["Angular"],
    "Backend": ["NestJS", "Node.js", "Python"],
    "Fullstack": [
        "Node Angular", "Python Angular",
        "Node.js Angular", "Python + Angular"
    ],
}

# === HELPERS ===
def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
            requests.post(url, data=data)
        except Exception as e:
            print(f"❌ Falha no Telegram: {e}")

def update_google_sheets(df):
    try:
        gc = gspread.service_account(filename="credentials.json")
        sheet = gc.open_by_url(GOOGLE_SHEETS_URL).sheet1
        sheet.clear()
        data = [df.columns.tolist()] + df.values.tolist()
        sheet.update(range_name="A1", values=data)
        print("✅ Planilha atualizada.")
    except Exception as e:
        print(f"❌ Falha ao atualizar Sheets: {e}")

def is_vaga_interessante(location):
    return any(r in location.lower() for r in REGIOES_INTERESSE)

def is_senioridade_interessante(texto):
    texto = texto.lower()

    palavras_excluidas = ["senior", "sênior", "sr", "especialista", "especialist", "expert", "lead"]
    palavras_incluidas = ["estágio", "trainee", "junior", "júnior", "jr", "pleno", "mid"]

    if any(p in texto for p in palavras_excluidas):
        return False
    return any(p in texto for p in palavras_incluidas)

# === REMOTIVE ===
def buscar_remotive(termo, tipo):
    print(f"🌐 Remotive: {tipo} - {termo}")
    try:
        r = requests.get(f"{REMOTIVE_API}?search={termo}")
        r.raise_for_status()
        vagas = []
        for job in r.json().get("jobs", []):
            loc = job.get("candidate_required_location", "")
            texto = job.get("title", "") + " " + job.get("description", "")
            if is_vaga_interessante(loc) and is_senioridade_interessante(texto):
                vagas.append({
                    "Origem": "Remotive",
                    "Tipo": tipo,
                    "Título": job["title"],
                    "Empresa": job["company_name"],
                    "Localidade": loc,
                    "Data Publicação": job["publication_date"][:10],
                    "Link": job["url"]
                })
        return vagas
    except Exception as e:
        print(f"⚠️ Erro Remotive: {e}")
        return []

# === ADZUNA ===
def buscar_adzuna(termo, tipo):
    print(f"🌐 Adzuna: {tipo} - {termo}")
    resultados = []
    countries = ["br", "us", "ca", "mx"]  # Países com suporte

    for country in countries:
        try:
            url = f"{ADZUNA_API_BASE}/{country}/search/1"
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "what": termo,
                "content-type": "application/json",
                "results_per_page": 20
            }
            res = requests.get(url, params=params)
            res.raise_for_status()
            data = res.json()

            for job in data.get("results", []):
                location = job.get("location", {}).get("display_name", "")
                descricao = job.get("description", "")
                titulo = job.get("title", "")
                texto = f"{titulo} {descricao}"

                if ("remote" in descricao.lower() or "remote" in location.lower()) and is_senioridade_interessante(texto):
                    resultados.append({
                        "Origem": "Adzuna",
                        "Tipo": tipo,
                        "Título": titulo,
                        "Empresa": job.get("company", {}).get("display_name", "N/A"),
                        "Localidade": location,
                        "Data Publicação": job.get("created", "")[:10],
                        "Link": job.get("redirect_url", ""),
                    })
        except Exception as e:
            print(f"⚠️ Erro Adzuna ({country}): {e}")
    return resultados

# === EXECUÇÃO PRINCIPAL ===
def executar_bot():
    print(f"\n🚀 Bot iniciado: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    todas_vagas = []

    for tipo, termos in SEARCH_CONFIG.items():
        for termo in termos:
            todas_vagas.extend(buscar_remotive(termo, tipo))
            time.sleep(2)
            todas_vagas.extend(buscar_adzuna(termo, tipo))
            time.sleep(2)

    df = pd.DataFrame(todas_vagas).drop_duplicates(subset=["Título", "Empresa", "Link"])
    print(f"\n📊 Total de vagas únicas: {len(df)}")

    if not df.empty:
        update_google_sheets(df)
        send_telegram(f"🎯 {len(df)} vagas remotas encontradas!\nStacks: Frontend, Backend, Fullstack.")
    else:
        send_telegram("⚠️ Nenhuma vaga remota encontrada no momento.")

    print("✅ Execução finalizada.\n" + "=" * 50)

# === LOOP AGENDADO ===
def main():
    executar_bot()
    schedule.every(72).hours.do(executar_bot)
    print("⏰ Agendado a cada 72h.")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
