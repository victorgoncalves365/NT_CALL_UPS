import time
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
from flask import Flask
from datetime import datetime

# --- CONFIGURAÇÃO DO TELEGRAM ---
CHAT_ID = "1470850500" # COLOQUE O ID DO SEU GRUPO AQUI
URL_TELEGRAM_DIRETA = "https://api.telegram.org/bot9074266295:AAET9Ne2DczZHRqX-NrC-vtDxEWca6DyOSY/sendMessage"

# --- CONFIGURAÇÃO DA DATA FIFA ATUAL ---
JANELA_FIFA_ATUAL = "November 2026"

# Adicione todas as variações de escrita que você perceber aqui
FRASES_GATILHO_WIKIPEDIA = [
    "november 2026, respectively",
    "november 2026 respectively",
    ", 2026 respectively"
]

# --- LISTA DE SELEÇÕES (Para evitar mensagens repetidas) ---
# Esquerda: Nome Bonito pro Cache. Direita: Palavras que o bot vai procurar nos textos.
# Você pode adicionar quantas seleções quiser seguindo esse padrão!
SELECOES_MONITORADAS = {
    
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
    "Ucrânia": ["ucrânia", "ucrania", "ukraine"],
    
    # --- AFC (Ásia) ---
    "Arábia Saudita": ["arábia saudita", "arabia saudita", "saudi arabia"],
    "Bahrein": ["bahrein", "bahrain"],
    "Catar": ["catar", "qatar"],
    "China": ["china"],
    "Coreia do Sul": ["coreia do sul", "south korea", "korea republic"],
    "Emirados Árabes": ["emirados árabes", "emirados arabes", "uae", "united arab emirates"],
    "Índia": ["índia", "india"],
    "Indonésia": ["indonésia", "indonesia"],
    "Irã": ["irã", "ira", "iran"],
    "Iraque": ["iraque", "iraq"],
    "Japão": ["japão", "japao", "japan"],
    "Jordânia": ["jordânia", "jordania", "jordan"],
    "Líbano": ["líbano", "libano", "lebanon"],
    "Malásia": ["malásia", "malasia", "malaysia"],
    "Omã": ["omã", "oma", "oman"],
    "Palestina": ["palestina", "palestine"],
    "Quirguistão": ["quirguistão", "quirguistao", "kyrgyzstan"],
    "Tailândia": ["tailândia", "tailandia", "thailand"],
    "Tajiquistão": ["tajiquistão", "tajiquistao", "tajikistan"],
    "Uzbequistão": ["uzbequistão", "uzbequistao", "uzbekistan"],

    # --- CAF (África) ---
    "África do Sul": ["áfrica do sul", "africa do sul", "south africa", "bafana bafana"],
    "Angola": ["angola"],
    "Argélia": ["argélia", "argelia", "algeria"],
    "Benim": ["benim", "benin"],
    "Botsuana": ["botsuana", "botswana"],
    "Burkina Faso": ["burkina faso"],
    "Burundi": ["burundi"],
    "Cabo Verde": ["cabo verde", "cape verde"],
    "Camarões": ["camarões", "camaroes", "cameroon"],
    "Comores": ["comores", "comoros"],
    "Congo": ["república do congo", "republica do congo", "republic of the congo", "congo"],
    "Costa do Marfim": ["costa do marfim", "ivory coast", "cote d'ivoire", "cote d ivoire"],
    "Egito": ["egito", "egypt"],
    "Etiópia": ["etiópia", "etiopia", "ethiopia"],
    "Gabão": ["gabão", "gabao", "gabon"],
    "Gâmbia": ["gâmbia", "gambia"],
    "Gana": ["gana", "ghana"],
    "Guiné": ["guiné", "guine", "guinea"],
    "Guiné Equatorial": ["guiné equatorial", "guine equatorial", "equatorial guinea"],
    "Guiné-Bissau": ["guiné-bissau", "guine-bissau", "guinea-bissau"],
    "Lesoto": ["lesoto", "lesotho"],
    "Libéria": ["libéria", "liberia"],
    "Líbia": ["líbia", "libia", "libya"],
    "Madagascar": ["madagascar"],
    "Malaui": ["malaui", "malawi"],
    "Mali": ["mali"],
    "Marrocos": ["marrocos", "morocco"],
    "Mauritânia": ["mauritânia", "mauritania"],
    "Moçambique": ["moçambique", "mocambique", "mozambique"],
    "Namíbia": ["namíbia", "namibia"],
    "Níger": ["níger", "niger"],
    "Nigéria": ["nigéria", "nigeria", "super eagles"],
    "RD Congo": ["rd congo", "dr congo", "congo dr", "república democrática do congo", "democratic republic of the congo"],
    "República Centro-Africana": ["república centro-africana", "republica centro-africana", "central african republic"],
    "Ruanda": ["ruanda", "rwanda"],
    "São Tomé e Príncipe": ["são tomé", "sao tome", "sao tome and principe"],
    "Senegal": ["senegal"],
    "Serra Leoa": ["serra leoa", "sierra leone"],
    "Sudão do Sul": ["sudão do sul", "sudao do sul", "south sudan"],
    "Tanzânia": ["tanzânia", "tanzania"],
    "Togo": ["togo"],
    "Tunísia": ["tunísia", "tunisia"],
    "Uganda": ["uganda"],
    "Zâmbia": ["zâmbia", "zambia"],

    # --- CONMEBOL (América do Sul) ---
    "Argentina": ["argentina", "albiceleste"],
    "Brasil": ["brasil", "brazil", "seleção brasileira", "cbf"],
    "Bolívia": ["bolívia", "bolivia"],
    "Chile": ["chile"],
    "Colômbia": ["colômbia", "colombia", "los cafeteros"],
    "Equador": ["equador", "ecuador", "la tri"],
    "Paraguai": ["paraguai", "paraguay", "albirroja"],
    "Peru": ["peru", "bicolor"],
    "Uruguai": ["uruguai", "uruguay", "celeste"],
    "Venezuela": ["venezuela", "vinotinto"],

    # --- CONCACAF (América do Norte e Central) ---
    "Canadá": ["canadá", "canada"],
    "Costa Rica": ["costa rica", "los ticos"],
    "Cuba": ["cuba"],
    "Curaçao": ["curaçao", "curacao"],
    "El Salvador": ["el salvador"],
    "Estados Unidos": ["estados unidos", "usa", "united states", "usmnt", "team usa"],
    "Guatemala": ["guatemala"],
    "Haiti": ["haiti"],
    "Honduras": ["honduras"],
    "Jamaica": ["jamaica", "reggae boyz"],
    "México": ["méxico", "mexico", "el tri"],
    "Nicarágua": ["nicarágua", "nicaragua"],
    "Panamá": ["panamá", "panama"],
    "Porto Rico": ["porto rico", "puerto rico"],
    "República Dominicana": ["república dominicana", "republica dominicana", "dominican republic"],
    "Trinidad e Tobago": ["trinidad e tobago", "trinidad and tobago"],

     # --- OFC (Oceania) ---
    "Australia": ["australia", "austrália"],
    "Nova Zelândia": ["nova zelandia", "nova zelândia", "new zealand", "new zeland"], 
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
     # --- UEFA (Europa) ---
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
    
    # --- AFC (Ásia) ---
    "https://en.wikipedia.org/wiki/Bahrain_national_football_team",
    "https://en.wikipedia.org/wiki/China_national_football_team",
    "https://en.wikipedia.org/wiki/India_national_football_team",
    "https://en.wikipedia.org/wiki/Indonesia_national_football_team",
    "https://en.wikipedia.org/wiki/Iran_national_football_team",
    "https://en.wikipedia.org/wiki/Iraq_national_football_team",
    "https://en.wikipedia.org/wiki/Japan_national_football_team",
    "https://en.wikipedia.org/wiki/Jordan_national_football_team",
    "https://en.wikipedia.org/wiki/Kyrgyzstan_national_football_team",
    "https://en.wikipedia.org/wiki/Lebanon_national_football_team",
    "https://en.wikipedia.org/wiki/Malaysia_national_football_team",
    "https://en.wikipedia.org/wiki/Oman_national_football_team",
    "https://en.wikipedia.org/wiki/Palestine_national_football_team",
    "https://en.wikipedia.org/wiki/Qatar_national_football_team",
    "https://en.wikipedia.org/wiki/Saudi_Arabia_national_football_team",
    "https://en.wikipedia.org/wiki/South_Korea_national_football_team",
    "https://en.wikipedia.org/wiki/Tajikistan_national_football_team",
    "https://en.wikipedia.org/wiki/Thailand_national_football_team",
    "https://en.wikipedia.org/wiki/United_Arab_Emirates_national_football_team",
    "https://en.wikipedia.org/wiki/Uzbekistan_national_football_team",

    # --- CAF (África) ---
    "https://en.wikipedia.org/wiki/Algeria_national_football_team",
    "https://en.wikipedia.org/wiki/Angola_national_football_team",
    "https://en.wikipedia.org/wiki/Benin_national_football_team",
    "https://en.wikipedia.org/wiki/Botswana_national_football_team",
    "https://en.wikipedia.org/wiki/Burkina_Faso_national_football_team",
    "https://en.wikipedia.org/wiki/Burundi_national_football_team",
    "https://en.wikipedia.org/wiki/Cameroon_national_football_team",
    "https://en.wikipedia.org/wiki/Cape_Verde_national_football_team",
    "https://en.wikipedia.org/wiki/Central_African_Republic_national_football_team",
    "https://en.wikipedia.org/wiki/Comoros_national_football_team",
    "https://en.wikipedia.org/wiki/DR_Congo_national_football_team",
    "https://en.wikipedia.org/wiki/Egypt_national_football_team",
    "https://en.wikipedia.org/wiki/Equatorial_Guinea_national_football_team",
    "https://en.wikipedia.org/wiki/Ethiopia_national_football_team",
    "https://en.wikipedia.org/wiki/Gabon_national_football_team",
    "https://en.wikipedia.org/wiki/Gambia_national_football_team",
    "https://en.wikipedia.org/wiki/Ghana_national_football_team",
    "https://en.wikipedia.org/wiki/Guinea_national_football_team",
    "https://en.wikipedia.org/wiki/Guinea-Bissau_national_football_team",
    "https://en.wikipedia.org/wiki/Ivory_Coast_national_football_team",
    "https://en.wikipedia.org/wiki/Lesotho_national_football_team",
    "https://en.wikipedia.org/wiki/Liberia_national_football_team",
    "https://en.wikipedia.org/wiki/Libya_national_football_team",
    "https://en.wikipedia.org/wiki/Madagascar_national_football_team",
    "https://en.wikipedia.org/wiki/Malawi_national_football_team",
    "https://en.wikipedia.org/wiki/Mali_national_football_team",
    "https://en.wikipedia.org/wiki/Mauritania_national_football_team",
    "https://en.wikipedia.org/wiki/Morocco_national_football_team",
    "https://en.wikipedia.org/wiki/Mozambique_national_football_team",
    "https://en.wikipedia.org/wiki/Namibia_national_football_team",
    "https://en.wikipedia.org/wiki/Niger_national_football_team",
    "https://en.wikipedia.org/wiki/Nigeria_national_football_team",
    "https://en.wikipedia.org/wiki/Republic_of_the_Congo_national_football_team",
    "https://en.wikipedia.org/wiki/Rwanda_national_football_team",
    "https://en.wikipedia.org/wiki/Sao_Tome_and_Principe_national_football_team",
    "https://en.wikipedia.org/wiki/Senegal_national_football_team",
    "https://en.wikipedia.org/wiki/Sierra_Leone_national_football_team",
    "https://en.wikipedia.org/wiki/South_Africa_national_football_team",
    "https://en.wikipedia.org/wiki/South_Sudan_national_football_team",
    "https://en.wikipedia.org/wiki/Tanzania_national_football_team",
    "https://en.wikipedia.org/wiki/Togo_national_football_team",
    "https://en.wikipedia.org/wiki/Tunisia_national_football_team",
    "https://en.wikipedia.org/wiki/Uganda_national_football_team",
    "https://en.wikipedia.org/wiki/Zambia_national_football_team",

    # --- OFC (Oceania) ---
    "https://en.wikipedia.org/wiki/Australia_men%27s_national_soccer_team",
    "https://en.wikipedia.org/wiki/New_Zealand_men's_national_football_team",

    # --- CONMEBOL (América do Sul) ---
    "https://en.wikipedia.org/wiki/Argentina_national_football_team",
    "https://en.wikipedia.org/wiki/Brazil_national_football_team",
    "https://en.wikipedia.org/wiki/Bolivia_national_football_team",
    "https://en.wikipedia.org/wiki/Chile_national_football_team",
    "https://en.wikipedia.org/wiki/Colombia_national_football_team",
    "https://en.wikipedia.org/wiki/Ecuador_national_football_team",
    "https://en.wikipedia.org/wiki/Paraguay_national_football_team",
    "https://en.wikipedia.org/wiki/Peru_national_football_team",
    "https://en.wikipedia.org/wiki/Uruguay_national_football_team",
    "https://en.wikipedia.org/wiki/Venezuela_national_football_team",

    # --- CONCACAF (América do Norte e Central) ---
    "https://en.wikipedia.org/wiki/Canada_national_football_team",
    "https://en.wikipedia.org/wiki/Costa_Rica_national_football_team",
    "https://en.wikipedia.org/wiki/Cuba_national_football_team",
    "https://en.wikipedia.org/wiki/Curacao_national_football_team",
    "https://en.wikipedia.org/wiki/Dominican_Republic_national_football_team",
    "https://en.wikipedia.org/wiki/El_Salvador_national_football_team",
    "https://en.wikipedia.org/wiki/Guatemala_national_football_team",
    "https://en.wikipedia.org/wiki/Haiti_national_football_team",
    "https://en.wikipedia.org/wiki/Honduras_national_football_team",
    "https://en.wikipedia.org/wiki/Jamaica_national_football_team",
    "https://en.wikipedia.org/wiki/Mexico_national_football_team",
    "https://en.wikipedia.org/wiki/Nicaragua_national_football_team",
    "https://en.wikipedia.org/wiki/Panama_national_football_team",
    "https://en.wikipedia.org/wiki/Puerto_Rico_national_football_team",
    "https://en.wikipedia.org/wiki/Trinidad_and_Tobago_national_football_team",
    "https://en.wikipedia.org/wiki/United_States_men%27s_national_soccer_team",
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
    selecoes_encontradas = []
    
    # 1. Encontra TODAS as seleções mencionadas e anota a posição exata delas na frase
    for nome_oficial, apelidos in SELECOES_MONITORADAS.items():
        for apelido in apelidos:
            posicao = texto_min.find(apelido)
            if posicao != -1:
                selecoes_encontradas.append((posicao, nome_oficial))
                break # Já achou o país, pula para verificar o próximo do dicionário
                
    # Se achou algum país, pega EXATAMENTE o que foi falado primeiro (menor posição no texto)
    selecao_encontrada = None
    if selecoes_encontradas:
        selecoes_encontradas.sort(key=lambda x: x[0]) # Ordena da primeira palavra até a última
        selecao_encontrada = selecoes_encontradas[0][1] # Pega o vencedor
        
    # 2. Descobre se é sobre corte/substituição
    termos_corte = ["corte", "cortado", "desconvocado", "substitui", "substituto", "replacement", "replaced", "withdraw", "change for", "out:"]
    eh_corte = any(termo in texto_min for termo in termos_corte)
    
    return selecao_encontrada, eh_corte

# --- MOTOR DE BUSCA ---
def executar_varredura():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    print("\n==============================================")
    print(f"[{agora}] Iniciando varredura com Desduplicação de Entidades...")
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
                
                # Procura se ALGUMA das frases da sua lista está no parágrafo
                gatilho_encontrado = False
                for frase in FRASES_GATILHO_WIKIPEDIA:
                    if frase.lower() in texto_min:
                        gatilho_encontrado = True
                        break # Achou uma das frases! Pode parar de procurar
                
                if gatilho_encontrado:
                    selecao, _ = classificar_noticia(url) # Busca o nome do país direto na URL
                    
                    if selecao:
                        id_unico = f"CONVOCACAO_PRINCIPAL_{selecao}_{JANELA_FIFA_ATUAL.replace(' ', '_')}"
                    else:
                        # Agora usamos a JANELA_FIFA como trava para evitar repetição se alguém mudar a vírgula no site
                        id_unico = f"{url}__{JANELA_FIFA_ATUAL.replace(' ', '_')}"
                    
                    if id_unico not in historico_enviados and id_unico not in enviados_nesta_rodada:
                        print(f" 🎉 Wikipedia atualizada: {url}")
                        enviar_telegram(f"📚 *WIKIPEDIA ATUALIZADA!*\n\n📢 A página da seleção confirmou o elenco oficial!\n🔗 [Ver o Elenco]({url}#Current_squad)")
                        salvar_no_cache(id_unico)
                        enviados_nesta_rodada.add(id_unico)
                        break
        except Exception: pass

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
