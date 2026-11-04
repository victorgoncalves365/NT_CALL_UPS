import time
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
from flask import Flask

# --- CONFIGURAÇÃO DO TELEGRAM ---
CHAT_ID = "-5514663870"
URL_TELEGRAM_DIRETA = "https://api.telegram.org/bot9074266295:AAET9Ne2DczZHRqX-NrC-vtDxEWca6DyOSY/sendMessage"

# --- 1. PORTAIS DE NOTÍCIAS ---
URLS_PORTAIS = [
    "https://reuters.com",
    "https://www.skysports.com/uefa-nations-league",
    "https://espn.com",
    "https://transfermarkt.com",
    "https://flashscore.com",
    "https://goal.com"
    "https://www.thefa.com/"
    "https://www.dfb.de/"
    "https://www.fff.fr/"
    "https://www.fpf.pt/pt/"
]

# --- 2. CONTAS DO TWITTER (CONVERTIDAS PARA RSS) ---
# DICA: Crie seus links gratuitos no site rss.app e cole aqui dentro das aspas.
URLS_TWITTER_RSS = [
    "https://rss.app/feeds/9Dx2jq9WehxKkQQ1.xml",
    "https://rss.app/feeds/z9lY0FTLjVUazkIM.xml",
    
]

# --- 3. PÁGINAS DA WIKIPEDIA ---
URLS_WIKIPEDIA = [
    "https://en.wikipedia.org/wiki/Denmark_national_football_team",
    "https://en.wikipedia.org/wiki/Brazil_national_football_team",
    "https://en.wikipedia.org/wiki/Albania_national_football_team",
    "https://en.wikipedia.org/wiki/Andorra_national_football_team",
    "https://en.wikipedia.org/wiki/Austria_national_football_team",
    "https://en.wikipedia.org/wiki/Azerbaijan_national_football_team",
    "https://en.wikipedia.org/wiki/Belarus_national_football_team",
    "https://en.wikipedia.org/wiki/Belgium_national_football_team",
    "https://en.wikipedia.org/wiki/Bosnia_and_Herzegovina_national_football_team"
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
    "https://en.wikipedia.org/wiki/Wales_national_football_team"
    # Lembre-se: use sempre os links em inglês (en.wikipedia.org)
]

# A FRASE EXATA QUE DIFERENCIA O ELENCO DO RESTO DA PÁGINA
FRASE_GATILHO_WIKIPEDIA = "November 2026, respectively"

ARQUIVO_CACHE = "ultimas_noticias_cache.txt"

def enviar_telegram(mensagem):
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
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

# --- FILTRO INTELIGENTE ATUALIZADO (SUPORTE AO INGLÊS) ---
def noticia_e_relevante(titulo):
    titulo_min = titulo.lower()

    # 1. AÇÃO: Chamados, cortes, substituições (em PT e EN)
    termos_principais = [
        "convocados", "convocação", "lista", "convoca", "convocado", 
        "squad", "roster", "call-up", "callup", "callups", "corte", "cortado", "desconvocado", 
        "substitui", "substituto", "chamado"
    ]
    tem_principal = any(termo in titulo_min for termo in termos_principais)

    # 2. CONTEXTO: Adicionados termos de futebol internacional em inglês
    termos_contexto = [
        "seleção", "oficial", "anuncia", "divulga", "national team", "fifa", "cbf",
        "nationsleague", "afcon", "friendly", "friendlies", "qualifiers", "qualifying",
        "championship", "cup", "face", "against"
    ]
    tem_contexto = any(termo in titulo_min for termo in termos_contexto)

    # REGRA ESPECIAL: Se o texto tiver uma dessas palavras cruciais em inglês, ganha aprovação direta
    palavras_fortes = ["squad", "roster", "call-up", "callup"]
    tem_palavra_forte = any(termo in titulo_min for termo in palavras_fortes)

    # 3. PROIBIDOS: Evita fofocas e entrevistas (em PT e EN)
    termos_proibidos = [
        "entrevista", "opinião", "coletiva", "rumor", "especulação", 
        "provável", "pode ser", "expectativa", "interview", "rumour", "opinion", "predicted"
    ]
    tem_proibido = any(termo in titulo_min for termo in termos_proibidos)

    # Aprova se (Ação + Contexto baterem OU tiver palavra forte) E NÃO for fofoca
    return ((tem_principal and tem_contexto) or tem_palavra_forte) and not tem_proibido

def executar_varredura():
    print("\n==============================================")
    print("Iniciando varredura anti-duplicação e filtro inteligente...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    historico_enviados = ler_cache()
    enviados_nesta_rodada = set()
    
    # --- PARTE 1: PORTAIS ---
    print(f"[Portais] Checando {len(URLS_PORTAIS)} sites...")
    for url in URLS_PORTAIS:
        try:
            resposta = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resposta.text, "html.parser")
            links_noticias = soup.find_all(["a", "h2", "h3"])
            
            for item in links_noticias:
                titulo = item.get_text(strip=True)
                link = item.get("href") if item.name == "a" else item.find_parent("a").get("href") if item.find_parent("a") else None
                
                if len(titulo) < 15 or not link:
                    continue
                if link.startswith("/"):
                    link = urljoin(url, link)
                
                if noticia_e_relevante(titulo):
                    if link not in historico_enviados and link not in enviados_nesta_rodada:
                        print(f" 🎉 Nova atualização na seleção encontrada: {titulo}")
                        texto_alerta = f"📰 *ATUALIZAÇÃO DE SELEÇÃO!*\n\n📢 {titulo}\n\n🔗 [Ler Matéria]({link})"
                        enviar_telegram(texto_alerta)
                        
                        salvar_no_cache(link)
                        enviados_nesta_rodada.add(link)
        except Exception as e:
            print(f"Erro ao acessar portal {url}: {e}")

    # --- PARTE 2: TWITTER ---
    print(f"[Twitter] Checando {len(URLS_TWITTER_RSS)} contas via RSS...")
    for url_rss in URLS_TWITTER_RSS:
        if "COLE_AQUI" in url_rss:
            continue
            
        try:
            print(f" -> Tentando acessar: {url_rss}")
            
            # Tenta acessar o link
            resposta_rss = requests.get(url_rss, headers=headers, timeout=15)
            print(f" -> Status da conexão: {resposta_rss.status_code} (Se for 200, está tudo certo. Se for 403, o site bloqueou o robô)")
            
            # Tenta ler o conteúdo
            feed = feedparser.parse(resposta_rss.content)
            print(f" -> Quantidade de Tweets encontrados: {len(feed.entries)}")
            
            for post in feed.entries:
                texto_tweet = post.title
                link_tweet = post.link
                
                if len(texto_tweet) < 10:
                    continue
                
                if noticia_e_relevante(texto_tweet):
                    print(f" [APROVADO] {texto_tweet[:60]}...")
                    
                    if link_tweet not in historico_enviados and link_tweet not in enviados_nesta_rodada:
                        print(f" 🎉 Novo Tweet relevante encontrado!")
                        texto_alerta = f"🐦 *TWITTER (ATUALIZAÇÃO):*\n\n💬 _{texto_tweet}_\n\n🔗 [Ver Tweet original]({link_tweet})"
                        enviar_telegram(texto_alerta)
                        
                        salvar_no_cache(link_tweet)
                        enviados_nesta_rodada.add(link_tweet)
                else:
                    print(f" [REPROVADO PELO FILTRO] {texto_tweet[:60]}...")
                    
        except Exception as e:
            print(f" ❌ Erro ao acessar o feed do Twitter {url_rss}: {e}")

    # --- PARTE 3: WIKIPEDIA ---
    print(f"[Wikipedia] Checando {len(URLS_WIKIPEDIA)} páginas pela frase exata '{FRASE_GATILHO_WIKIPEDIA}'...")
    for url in URLS_WIKIPEDIA:
        try:
            resposta_wiki = requests.get(url, headers=headers, timeout=15)
            soup_wiki = BeautifulSoup(resposta_wiki.text, "html.parser")
            
            # Na Wiki, essa frase específica de elenco sempre fica em um parágrafo <p>
            textos_pagina = soup_wiki.find_all("p")
            
            for item in textos_pagina:
                texto_min = item.get_text().lower()
                gatilho_min = FRASE_GATILHO_WIKIPEDIA.lower()
                
                # A mágica acontece aqui: busca a sua frase exata no parágrafo
                if gatilho_min in texto_min:
                    
                    # Cria o "link falso" no cache (Removemos vírgulas e espaços para não bugar o bloco de notas)
                    identificador_wiki = f"{url}__{FRASE_GATILHO_WIKIPEDIA.replace(' ', '_').replace(',', '')}"
                    
                    if identificador_wiki not in historico_enviados and identificador_wiki not in enviados_nesta_rodada:
                        print(f" 🎉 Wikipedia atualizada encontrada: {url}")
                        
                        texto_alerta = (
                            f"📚 *WIKIPEDIA ATUALIZADA!*\n\n"
                            f"📢 A página da seleção confirmou o elenco oficial!\n"
                            f"📌 Gatilho encontrado: _{FRASE_GATILHO_WIKIPEDIA}_\n\n"
                            f"🔗 [Ver o Elenco]({url}#Current_squad)"
                        )
                        enviar_telegram(texto_alerta)
                        
                        salvar_no_cache(identificador_wiki)
                        enviados_nesta_rodada.add(identificador_wiki)
                        break # Achou a frase, para de ler esta página e vai pra próxima
        except Exception as e:
            print(f"Erro ao acessar Wikipedia {url}: {e}")
            
    print("\nVarredura concluída. Próxima em 15 minutos.")
    print("==============================================")

# --- O TRUQUE DO SITE FALSO PARA A NUVEM ---
app = Flask(__name__)

@app.route('/')
def vivo():
    return "O Bot de Convocações está online e vigiando 24 horas por dia!"

def manter_vivo():
    # O Render (nossa nuvem) usa a porta 10000 por padrão
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    print("Criando servidor de disfarce para a nuvem...")
    t = threading.Thread(target=manter_vivo)
    t.start()
    
    print("Bot de Convocações Iniciado!")
    while True:
        executar_varredura()
        time.sleep(900)
