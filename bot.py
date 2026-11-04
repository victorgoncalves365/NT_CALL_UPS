import time
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
from flask import Flask

# --- CONFIGURAÇÃO DO TELEGRAM ---
CHAT_ID = "1470850500" # COLOQUE O ID DO SEU GRUPO AQUI
URL_TELEGRAM_DIRETA = "https://api.telegram.org/bot9074266295:AAET9Ne2DczZHRqX-NrC-vtDxEWca6DyOSY/sendMessage"

# --- CONFIGURAÇÃO DA DATA FIFA ATUAL ---
JANELA_FIFA_ATUAL = "November 2026"
FRASE_GATILHO_WIKIPEDIA = "November 2026, respectively"

# --- LISTA DE SELEÇÕES (Para evitar mensagens repetidas) ---
# Esquerda: Nome Bonito pro Cache. Direita: Palavras que o bot vai procurar nos textos.
# Você pode adicionar quantas seleções quiser seguindo esse padrão!
SELECOES_MONITORADAS = {
    "Brasil": ["brasil", "brazil", "seleção brasileira", "cbf"],
    
    # --- UEFA (Europa) ---
    "Albânia": ["albânia", "albania"],
    "Alemanha": ["alemanha", "germany", "dfb"],
    "Andorra": ["andorra"],
    "Armênia": ["armênia", "armenia"],
    "Áustria": ["áustria", "austria"],
    "Azerbaijão": ["azerbaijão", "azerbaijao", "azerbaijan"],
    "Bélgica": ["bélgica", "belgica", "belgium"],
    "Bielorrússia": ["bielorrússia", "bielorrussia", "belarus"],
    "Bósnia e Herzegovina": ["bósnia", "bosnia", "bosnia herzegovina", "bosnia and herzegovina"],
    "Bulgária": ["bulgária", "bulgaria"],
    "Cazaquistão": ["cazaquistão", "cazaquistao", "kazakhstan"],
    "Chipre": ["chipre", "cyprus"],
    "Croácia": ["croácia", "croacia", "croatia"],
    "Dinamarca": ["dinamarca", "denmark", "dbu"],
    "Escócia": ["escócia", "escocia", "scotland"],
    "Eslováquia": ["eslováquia", "eslovaquia", "slovakia"],
    "Eslovênia": ["eslovênia", "eslovenia", "slovenia"],
    "Espanha": ["espanha", "spain", "la roja"],
    "Estônia": ["estônia", "estonia"],
    "Faroe Islands": ["ilhas faroé", "ilhas faroe", "faroe islands"],
    "Finlândia": ["finlândia", "finlandia", "finland"],
    "França": ["frança", "franca", "france", "les bleus"],
    "Gales": ["gales", "wales", "país de gales", "pais de gales"],
    "Geórgia": ["geórgia", "georgia"],
    "Gibraltar": ["gibraltar"],
    "Grécia": ["grécia", "grecia", "greece"],
    "Holanda": ["holanda", "netherlands", "países baixos", "paises baixos", "dutch"],
    "Hungria": ["hungria", "hungary"],
    "Inglaterra": ["inglaterra", "england", "three lions"],
    "Irlanda": ["irlanda", "ireland", "republic of ireland"],
    "Irlanda do Norte": ["irlanda do norte", "northern ireland"],
    "Islândia": ["islândia", "islandia", "iceland"],
    "Israel": ["israel"],
    "Itália": ["itália", "italia", "italy", "azzurri"],
    "Kosovo": ["kosovo"],
    "Letônia": ["letônia", "letonia", "latvia"],
    "Liechtenstein": ["liechtenstein"],
    "Lituânia": ["lituânia", "lituania", "lithuania"],
    "Luxemburgo": ["luxemburgo", "luxembourg"],
    "Macedônia do Norte": ["macedônia do norte", "macedonia do norte", "north macedonia"],
    "Malta": ["malta"],
    "Moldávia": ["moldávia", "moldavia", "moldova"],
    "Montenegro": ["montenegro"],
    "Noruega": ["noruega", "norway"],
    "Polônia": ["polônia", "polonia", "poland"],
    "Portugal": ["portugal", "seleção portuguesa", "fpf"],
    "República Tcheca": ["república tcheca", "republica tcheca", "czech republic", "czechia", "chéquia", "chequia"],
    "Romênia": ["romênia", "romenia", "romania"],
    "Rússia": ["rússia", "russia"],
    "San Marino": ["san marino"],
    "Sérvia": ["sérvia", "servia", "serbia"],
    "Suécia": ["suécia", "suecia", "sweden"],
    "Suíça": ["suíça", "suica", "switzerland", "swiss"],
    "Turquia": ["turquia", "turkey", "türkiye"],
    "Ucrânia": ["ucrânia", "ucrania", "ukraine"]
}

# --- FONTES DE DADOS ---
URLS_PORTAIS = [
    "https://globo.com", "https://reuters.com", "https://skysports.com",
    "https://espn.com", "https://transfermarkt.com", "https://flashscore.com", "https://goal.com"
]

URLS_TWITTER_RSS = [
    "https://rss.app/feeds/9Dx2jq9WehxKkQQ1.xml",
    "https://rss.app/feeds/z9lY0FTLjVUazkIM.xml"
    # Adicione seus outros links válidos do RSS.app aqui
]

URLS_WIKIPEDIA = [
    "https://en.wikipedia.org/wiki/Albania_national_football_team",
    "https://en.wikipedia.org/wiki/Andorra_national_football_team",
    "https://en.wikipedia.org/wiki/Austria_national_football_team",
    "https://en.wikipedia.org/wiki/Azerbaijan_national_football_team",
    "https://en.wikipedia.org/wiki/Belarus_national_football_team",
    "https://en.wikipedia.org/wiki/Belgium_national_football_team",
    "https://en.wikipedia.org/wiki/Bosnia_and_Herzegovina_national_football_team",
    "https://en.wikipedia.org/wiki/Bulgaria_national_football_team",
    "https://en.wikipedia.org/wiki/Croatia_national_football_team",
    "https://en.wikipedia.org/wiki/Cyprus_national_football_team",
    "https://en.wikipedia.org/wiki/Czech_Republic_national_football_team",
    "https://en.wikipedia.org/wiki/Denmark_national_football_team",
    "https://en.wikipedia.org/wiki/England_national_football_team",
    "https://en.wikipedia.org/wiki/Estonia_national_football_team",
    "https://en.wikipedia.org/wiki/Faroe_Islands_national_football_team",
    "https://en.wikipedia.org/wiki/Finland_national_football_team",
    "https://en.wikipedia.org/wiki/France_national_football_team",
    "https://en.wikipedia.org/wiki/Georgia_national_football_team",
    "https://en.wikipedia.org/wiki/Germany_national_football_team",
    "https://en.wikipedia.org/wiki/Gibraltar_national_football_team",
    "https://en.wikipedia.org/wiki/Greece_national_football_team",
    "https://en.wikipedia.org/wiki/Hungary_national_football_team",
    "https://en.wikipedia.org/wiki/Iceland_national_football_team",
    "https://en.wikipedia.org/wiki/Republic_of_Ireland_national_football_team",
    "https://en.wikipedia.org/wiki/Israel_national_football_team",
    "https://en.wikipedia.org/wiki/Italy_national_football_team",
    "https://en.wikipedia.org/wiki/Kazakhstan_national_football_team",
    "https://en.wikipedia.org/wiki/Kosovo_national_football_team",
    "https://en.wikipedia.org/wiki/Latvia_national_football_team",
    "https://en.wikipedia.org/wiki/Liechtenstein_national_football_team",
    "https://en.wikipedia.org/wiki/Lithuania_national_football_team",
    "https://en.wikipedia.org/wiki/Luxembourg_national_football_team",
    "https://en.wikipedia.org/wiki/Malta_national_football_team",
    "https://en.wikipedia.org/wiki/Moldova_national_football_team",
    "https://en.wikipedia.org/wiki/Montenegro_national_football_team",
    "https://en.wikipedia.org/wiki/Netherlands_national_football_team",
    "https://en.wikipedia.org/wiki/North_Macedonia_national_football_team",
    "https://en.wikipedia.org/wiki/Northern_Ireland_national_football_team",
    "https://en.wikipedia.org/wiki/Norway_national_football_team",
    "https://en.wikipedia.org/wiki/Portugal_national_football_team",
    "https://en.wikipedia.org/wiki/Romania_national_football_team",
    "https://en.wikipedia.org/wiki/Russia_national_football_team",
    "https://en.wikipedia.org/wiki/San_Marino_national_football_team",
    "https://en.wikipedia.org/wiki/Scotland_national_football_team",
    "https://en.wikipedia.org/wiki/Serbia_national_football_team",
    "https://en.wikipedia.org/wiki/Slovenia_national_football_team",
    "https://en.wikipedia.org/wiki/Spain_national_football_team",
    "https://en.wikipedia.org/wiki/Sweden_national_football_team",
    "https://en.wikipedia.org/wiki/Switzerland_national_football_team",
    "https://en.wikipedia.org/wiki/Turkey_national_football_team",
    "https://en.wikipedia.org/wiki/Ukraine_national_football_team",
    "https://en.wikipedia.org/wiki/Wales_national_football_team",
    "https://en.wikipedia.org/wiki/Brazil_national_football_team",
]

ARQUIVO_CACHE = "ultimas_noticias_cache.txt"

# --- FUNÇÕES BÁSICAS ---
def enviar_telegram(mensagem):
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(URL_TELEGRAM_DIRETA, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def ler_cache():
    try:
        with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
            return set(linha.strip() for linha in f if linha.strip())
    except FileNotFoundError:
        return set()

def salvar_no_cache(identificador):
    with open(ARQUIVO_CACHE, "a", encoding="utf-8") as f:
        f.write(identificador + "\n")

# --- FILTROS INTELIGENTES ---
def noticia_e_relevante(titulo):
    titulo_min = titulo.lower()
    termos_principais = ["convocados", "convocação", "lista", "convoca", "convocado", "squad", "roster", "call-up", "callup", "corte", "cortado", "desconvocado", "substitui", "substituto", "chamado"]
    tem_principal = any(termo in titulo_min for termo in termos_principais)
    termos_contexto = ["seleção", "oficial", "anuncia", "divulga", "national team", "fifa", "cbf", "nationsleague", "afcon", "friendly", "qualifiers"]
    tem_contexto = any(termo in titulo_min for termo in termos_contexto)
    palavras_fortes = ["squad", "roster", "call-up", "callup"]
    tem_palavra_forte = any(termo in titulo_min for termo in palavras_fortes)
    termos_proibidos = ["entrevista", "opinião", "coletiva", "rumor", "especulação", "provável", "expectativa", "interview", "rumour", "opinion", "predicted"]
    tem_proibido = any(termo in titulo_min for termo in termos_proibidos)
    
    return ((tem_principal and tem_contexto) or tem_palavra_forte) and not tem_proibido

def classificar_noticia(texto):
    texto_min = texto.lower()
    selecao_encontrada = None
    
    # 1. Tenta descobrir de qual seleção estão falando
    for nome_oficial, apelidos in SELECOES_MONITORADAS.items():
        if any(apelido in texto_min for apelido in apelidos):
            selecao_encontrada = nome_oficial
            break
            
    # 2. Descobre se é sobre corte/substituição
    termos_corte = ["corte", "cortado", "desconvocado", "substitui", "substituto", "replacement", "replaced", "withdraw", "change for", "out:"]
    eh_corte = any(termo in texto_min for termo in termos_corte)
    
    return selecao_encontrada, eh_corte

# --- MOTOR DE BUSCA ---
def executar_varredura():
    print("\n==============================================")
    print("Iniciando varredura com Desduplicação de Entidades...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    historico_enviados = ler_cache()
    enviados_nesta_rodada = set()
    
    # --- PARTE 1: PORTAIS ---
    for url in URLS_PORTAIS:
        try:
            resposta = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resposta.text, "html.parser")
            for item in soup.find_all(["a", "h2", "h3"]):
                titulo = item.get_text(strip=True)
                link = item.get("href") if item.name == "a" else item.find_parent("a").get("href") if item.find_parent("a") else None
                if len(titulo) < 15 or not link: continue
                if link.startswith("/"): link = urljoin(url, link)
                
                if noticia_e_relevante(titulo):
                    selecao, eh_corte = classificar_noticia(titulo)
                    
                    # SEGREDO AQUI: Se for a lista principal, trava pelo nome do país. Se for corte, usa o link da matéria.
                    if selecao and not eh_corte:
                        id_unico = f"CONVOCACAO_PRINCIPAL_{selecao}_{JANELA_FIFA_ATUAL.replace(' ', '_')}"
                    else:
                        id_unico = link

                    if id_unico not in historico_enviados and id_unico not in enviados_nesta_rodada:
                        print(f" 🎉 Nova matéria: {titulo}")
                        enviar_telegram(f"📰 *ATUALIZAÇÃO DE SELEÇÃO!*\n\n📢 {titulo}\n\n🔗 [Ler Matéria]({link})")
                        salvar_no_cache(id_unico)
                        enviados_nesta_rodada.add(id_unico)
        except Exception: pass

    # --- PARTE 2: TWITTER ---
    for url_rss in URLS_TWITTER_RSS:
        if "COLE_AQUI" in url_rss: continue
        try:
            resposta_rss = requests.get(url_rss, headers=headers, timeout=15)
            feed = feedparser.parse(resposta_rss.text)
            for post in feed.entries:
                texto_tweet = post.title
                link_tweet = post.link
                if len(texto_tweet) < 10: continue
                
                if noticia_e_relevante(texto_tweet):
                    selecao, eh_corte = classificar_noticia(texto_tweet)
                    
                    if selecao and not eh_corte:
                        id_unico = f"CONVOCACAO_PRINCIPAL_{selecao}_{JANELA_FIFA_ATUAL.replace(' ', '_')}"
                    else:
                        id_unico = link_tweet

                    if id_unico not in historico_enviados and id_unico not in enviados_nesta_rodada:
                        print(f" 🎉 Novo Tweet: {texto_tweet[:60]}")
                        enviar_telegram(f"🐦 *TWITTER (ATUALIZAÇÃO):*\n\n💬 _{texto_tweet}_\n\n🔗 [Ver Tweet]({link_tweet})")
                        salvar_no_cache(id_unico)
                        enviados_nesta_rodada.add(id_unico)
        except Exception: pass

    # --- PARTE 3: WIKIPEDIA ---
    for url in URLS_WIKIPEDIA:
        try:
            resposta_wiki = requests.get(url, headers=headers, timeout=15)
            soup_wiki = BeautifulSoup(resposta_wiki.text, "html.parser")
            for item in soup_wiki.find_all("p"):
                texto_min = item.get_text().lower()
                
                if FRASE_GATILHO_WIKIPEDIA.lower() in texto_min:
                    selecao, _ = classificar_noticia(url) # Busca o nome do país direto na URL
                    
                    if selecao:
                        id_unico = f"CONVOCACAO_PRINCIPAL_{selecao}_{JANELA_FIFA_ATUAL.replace(' ', '_')}"
                    else:
                        id_unico = f"{url}__{FRASE_GATILHO_WIKIPEDIA.replace(' ', '_').replace(',', '')}"
                    
                    if id_unico not in historico_enviados and id_unico not in enviados_nesta_rodada:
                        print(f" 🎉 Wikipedia atualizada: {url}")
                        enviar_telegram(f"📚 *WIKIPEDIA ATUALIZADA!*\n\n📢 A página da seleção confirmou o elenco oficial!\n🔗 [Ver o Elenco]({url}#Current_squad)")
                        salvar_no_cache(id_unico)
                        enviados_nesta_rodada.add(id_unico)
                        break
        except Exception: pass

    print("Varredura concluída. Aguardando próximo ciclo...")

# --- O TRUQUE DO SITE FALSO PARA A NUVEM (Render) ---
app = Flask(__name__)
@app.route('/')
def vivo(): return "O Bot está online 24 horas por dia!"

def manter_vivo(): app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    t = threading.Thread(target=manter_vivo)
    t.start()
    print("Bot Iniciado!")
    while True:
        executar_varredura()
        time.sleep(900)
