import html
import json
import os
import re
import sys
import threading
import time
import unicodedata
from datetime import datetime
from urllib.parse import unquote, urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from flask import Flask

# COMO LER ESTE ARQUIVO
# 1. As regulagens do dia a dia ficam aqui em cima: janela da FIFA, pausa e palavras.
# 2. No meio está a sua lista de seleções e os sites.
# 3. Embaixo está o motor. No dia a dia você não precisa mexer nele.
# O token do Telegram fica nas variáveis do Render, não neste arquivo.

# Mês em inglês, igual ao texto da Wikipedia. Exemplo da próxima janela: "March 2027".
JANELA_FIFA_ATUAL = "November 2026"

# 900 segundos = 15 minutos. A pausa começa depois que a varredura termina.
INTERVALO_SEGUNDOS = 900

# True também bloqueia sub-17, sub-20, sub-21 e sub-23.
# Deixei False porque uma matéria da seleção principal às vezes cita a base.
BLOQUEAR_SELECOES_DE_BASE = False

# Frases extras da Wikipedia. A janela de cima já entra na busca.
FRASES_GATILHO_WIKIPEDIA = [
    "november 2026, respectively",
    "november 2026 respectively",
    ", 2026 respectively",
]

# Palavras que fazem o bot prestar atenção.
TERMOS_CONVOCACAO = [
    "convocados", "convocado", "convocadas", "convocada",
    "convocação", "convocações", "convoca", "convocou", "convocaram",
    "convocatoria", "convocatorias", "convoque", "convocation",
    "squad", "roster", "call-up", "call-ups", "callup", "called up",
    "corte", "cortado", "cortados", "cortou", "cortaram",
    "desconvocado", "desconvocados", "desconvocou",
    "substitui", "substituiu", "substituição", "substituído", "substituídos",
    "substituto", "substitutos",
    "replacement", "replaced", "replaces", "withdrawn", "withdraws", "withdrew", "withdraw",
    "relacionados", "relacionado", "elenco",
    "pré-lista", "pré-convocação", "lista final", "lista definitiva", "lista preliminar",
    "chamado", "chamados", "desfalque", "desfalques", "desfalca",
]

# Se o título tiver uma destas palavras, ele fica de fora.
TERMOS_FEMININO = [
    "feminino", "feminina", "feminine", "feminin",
    "femenina", "femenino", "femminile", "frauen", "mulheres",
    "women", "womens", "woman", "womans", "female",
    "uswnt", "lionesses", "lioness", "matildas", "nwsl", "shebelieves", "bleues",
]

TERMOS_OUTROS_ESPORTES = [
    "basquete", "basketball", "nba", "nbb", "wnba",
    "vôlei", "volei", "volleyball",
    "tênis", "tenis", "tennis",
    "fórmula 1", "formula 1", "automobilismo",
    "natação", "natacao", "atletismo",
    "handebol", "handball", "rugby", "cricket", "ipl",
    "baseball", "beisebol", "mlb",
    "hóquei", "hoquei", "hockey", "nhl",
    "golfe", "golf", "ciclismo",
    "ufc", "mma", "boxe", "boxing",
    "nfl", "touchdown", "quarterback", "super bowl", "college football",
    "futsal", "futebol de areia", "beach soccer",
    "esports", "e-sports", "valorant", "counter-strike", "league of legends",
]

TERMOS_RUMOR = [
    "entrevista", "entrevistas", "opinião", "rumor", "rumores",
    "especulação", "especulações", "provável", "possível", "expectativa",
    "interview", "rumour", "rumors", "opinion", "predicted", "prediction", "possible",
]

TERMOS_BASE = [
    "sub-17", "sub-20", "sub-21", "sub-23",
    "under-17", "under-20", "under-21", "under-23",
    "u-17", "u-20", "u-21", "u-23",
    "u17", "u20", "u21", "u23",
]

# Estas palavras não travam a seleção inteira: cada matéria de corte pode ser avisada.
TERMOS_CORTE = [
    "corte", "cortado", "cortados", "cortou", "cortaram",
    "desconvocado", "desconvocados", "desconvocou",
    "substitui", "substituiu", "substituição", "substituído", "substituídos",
    "substituto", "substitutos",
    "replacement", "replaced", "replaces", "withdrawn", "withdraws", "withdrew", "withdraw",
    "desfalque", "desfalques", "desfalca", "ruled out", "out of the squad",
]

SINAIS_ELENCO_WIKI = [
    "called up", "respectively", "preliminary",
    "named in", "named to", "convoked", "squad for", "squad list",
]

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()
CHAVE_CACHE = "memoria_convocacoes"
ARQUIVO_CACHE = "ultimas_noticias_cache.json"
ARQUIVO_CACHE_ANTIGO = "ultimas_noticias_cache.txt"

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
HEADERS_WIKI = {
    "User-Agent": "BotConvocacoesSelecoes/1.0 (avisos de elenco no Telegram; uso pessoal)"
}

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
    "Irã": ["irã", "iran"],
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
    "https://espn.com", "https://transfermarkt.com", "https://www.flashscore.com/news/", 
]

URLS_TWITTER_RSS = [
    "https://rss.app/feeds/9Dx2jq9WehxKkQQ1.xml",
    "https://rss.app/feeds/z9lY0FTLjVUazkIM.xml"
    # Adicione seus outros links válidos do RSS.app aqui
]

URLS_WIKIPEDIA = [
     # --- UEFA (Europa) ---
    "https://en.wikipedia.org/wiki/Albania_national_football_team",
    "https://en.wikipedia.org/wiki/Armenia_national_football_team",
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
    "https://en.wikipedia.org/wiki/Poland_national_football_team",
    "https://en.wikipedia.org/wiki/Portugal_national_football_team",
    "https://en.wikipedia.org/wiki/Romania_national_football_team",
    "https://en.wikipedia.org/wiki/Russia_national_football_team",
    "https://en.wikipedia.org/wiki/San_Marino_national_football_team",
    "https://en.wikipedia.org/wiki/Scotland_national_football_team",
    "https://en.wikipedia.org/wiki/Serbia_national_football_team",
    "https://en.wikipedia.org/wiki/Slovakia_national_football_team",
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
    "https://en.wikipedia.org/wiki/New_Zealand_men%27s_national_football_team",

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

def log(texto):
    try:
        print(texto, flush=True)
    except UnicodeEncodeError:
        print(str(texto).encode("ascii", "backslashreplace").decode("ascii"), flush=True)


def preparar_console():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def normalizar(texto):
    texto = unquote(str(texto or ""))
    texto = texto.lower().replace("_", " ").replace("-", " ")
    texto = re.sub("['\u2019\u2018\u00b4`]", "", texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    return re.sub(r"\s+", " ", texto).strip()


def contem_termo(texto_normalizado, termo):
    termo_n = normalizar(termo)
    if not termo_n:
        return False
    return re.search(r"\b" + re.escape(termo_n) + r"\b", texto_normalizado) is not None


def montar_busca():
    vistos = {}
    for nome, apelidos in SELECOES_MONITORADAS.items():
        for apelido in apelidos:
            chave = normalizar(apelido)
            if not chave or chave in vistos:
                continue
            vistos[chave] = nome
    pares = sorted(vistos.items(), key=lambda item: len(item[0]), reverse=True)
    padrao = re.compile("|".join(r"\b" + re.escape(chave) + r"\b" for chave, _ in pares))
    return padrao, dict(pares)


PADRAO_SELECOES, MAPA_SELECOES = montar_busca()


def motivo_bloqueio(texto_normalizado):
    if any(contem_termo(texto_normalizado, termo) for termo in TERMOS_FEMININO):
        return "feminino"
    if any(contem_termo(texto_normalizado, termo) for termo in TERMOS_OUTROS_ESPORTES):
        return "outro_esporte"
    if BLOQUEAR_SELECOES_DE_BASE and any(contem_termo(texto_normalizado, termo) for termo in TERMOS_BASE):
        return "base"
    if any(contem_termo(texto_normalizado, termo) for termo in TERMOS_RUMOR):
        return "rumor"
    return ""


def classificar_noticia(texto):
    texto_n = normalizar(texto)
    achado = PADRAO_SELECOES.search(texto_n)
    selecao = MAPA_SELECOES.get(achado.group(0)) if achado else None
    eh_corte = any(contem_termo(texto_n, termo) for termo in TERMOS_CORTE)
    return selecao, eh_corte


def avaliar_noticia(texto):
    texto_n = normalizar(texto)
    if not any(contem_termo(texto_n, termo) for termo in TERMOS_CONVOCACAO):
        return None, False, "sem_termo"
    motivo = motivo_bloqueio(texto_n)
    if motivo:
        return None, False, motivo
    selecao, eh_corte = classificar_noticia(texto)
    if not selecao:
        return None, False, "sem_selecao"
    return selecao, eh_corte, ""


def identificador(selecao, eh_corte, link):
    if eh_corte:
        return f"CORTE_{selecao}_{link}"
    janela = normalizar(JANELA_FIFA_ATUAL).replace(" ", "_")
    return f"CONVOCACAO_PRINCIPAL_{selecao}_{janela}"


def estado_vazio():
    return {"ids": set(), "seed_completo": False}


def estado_para_json(estado):
    return json.dumps(
        {"ids": sorted(estado["ids"]), "seed_completo": bool(estado["seed_completo"])},
        ensure_ascii=False,
    )


def estado_de_json(texto):
    dados = json.loads(texto)
    if not isinstance(dados, dict) or not isinstance(dados.get("ids", []), list):
        raise ValueError("caderno em formato desconhecido")
    return {
        "ids": {str(item) for item in dados.get("ids", []) if str(item).strip()},
        "seed_completo": bool(dados.get("seed_completo", False)),
    }


def ler_local():
    if os.path.exists(ARQUIVO_CACHE):
        with open(ARQUIVO_CACHE, encoding="utf-8") as arquivo:
            conteudo = arquivo.read().strip()
        if conteudo:
            return estado_de_json(conteudo)
    if os.path.exists(ARQUIVO_CACHE_ANTIGO):
        with open(ARQUIVO_CACHE_ANTIGO, encoding="utf-8") as arquivo:
            ids = {linha.strip() for linha in arquivo if linha.strip()}
        return {"ids": ids, "seed_completo": False}
    return estado_vazio()


def upstash_configurado():
    return bool(UPSTASH_URL and UPSTASH_TOKEN)


def upstash(comando):
    resposta = requests.post(
        UPSTASH_URL,
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
        json=comando,
        timeout=20,
    )
    try:
        dados = resposta.json()
    except Exception as exc:
        raise RuntimeError(f"resposta inválida ({resposta.status_code})") from exc
    if resposta.status_code != 200 or "error" in dados:
        raise RuntimeError(str(dados.get("error", resposta.status_code)))
    return dados.get("result")


def ler_remoto():
    try:
        resultado = upstash(["GET", CHAVE_CACHE])
    except Exception as exc:
        log(f"Não consegui ler o caderno online: {exc}")
        return None, False
    if not resultado:
        return estado_vazio(), True
    try:
        return estado_de_json(resultado), True
    except Exception as exc:
        log(f"O caderno online está ilegível: {exc}")
        return None, False


def salvar_estado(estado):
    with open(ARQUIVO_CACHE, "w", encoding="utf-8") as arquivo:
        arquivo.write(estado_para_json(estado))
    if not upstash_configurado():
        return False
    try:
        upstash(["SET", CHAVE_CACHE, estado_para_json(estado)])
        return True
    except Exception as exc:
        log(f"Não consegui gravar o caderno online: {exc}")
        return False


def carregar_estado():
    if not upstash_configurado():
        log("O caderno online ainda não está ligado.")
        log("No Render, crie UPSTASH_REDIS_REST_URL e UPSTASH_REDIS_REST_TOKEN.")
        log("Sem esse caderno, uma queda do Render apagaria a memória. Nesta volta não vou avisar o grupo.")
        return None
    remoto, ok = ler_remoto()
    if not ok:
        log("Não vou avisar o grupo nesta volta, para não repetir uma seleção já enviada.")
        return None
    local = ler_local()
    remoto["ids"].update(local["ids"])
    remoto["seed_completo"] = remoto["seed_completo"] or local["seed_completo"]
    return remoto


def enviar_telegram(mensagem):
    if not TOKEN or not CHAT_ID:
        log("Faltam TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID. Nada foi enviado.")
        return False
    try:
        resposta = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": mensagem,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
    except Exception:
        log("Erro de rede ao falar com o Telegram.")
        return False
    if resposta.status_code != 200:
        log(f"O Telegram recusou a mensagem: {resposta.status_code} {resposta.text[:180]}")
        return False
    return True


def mensagem_portal(titulo, link):
    return (
        "📰 <b>ATUALIZAÇÃO DE SELEÇÃO</b>\n\n"
        f"{html.escape(titulo)}\n\n"
        f'<a href="{html.escape(link, quote=True)}">Ler matéria</a>'
    )


def mensagem_twitter(texto, link):
    return (
        "🐦 <b>TWITTER</b>\n\n"
        f"{html.escape(texto)}\n\n"
        f'<a href="{html.escape(link, quote=True)}">Ver tweet</a>'
    )


def mensagem_wiki(selecao, url):
    endereco = html.escape(url, quote=True) + "#Current_squad"
    return (
        "📚 <b>WIKIPEDIA ATUALIZADA</b>\n\n"
        f"A página de {html.escape(selecao)} confirmou o elenco desta janela.\n"
        f'<a href="{endereco}">Ver o elenco</a>'
    )


ROTULOS_BLOQUEIO = {
    "feminino": "futebol feminino",
    "outro_esporte": "outro esporte",
    "base": "seleção de base",
    "rumor": "rumor ou opinião",
}


def entregar(estado, vistos, modo_semente, resumo, id_unico, mensagem, rotulo):
    if id_unico in estado["ids"] or id_unico in vistos:
        return
    if modo_semente:
        estado["ids"].add(id_unico)
        vistos.add(id_unico)
        resumo["anotados"] += 1
        log(f"  Anotado sem avisar ({rotulo})")
        return
    if enviar_telegram(mensagem):
        estado["ids"].add(id_unico)
        vistos.add(id_unico)
        resumo["enviados"] += 1
        log(f"  Enviado ({rotulo})")
        if not salvar_estado(estado):
            log("  A mensagem saiu, mas o caderno online não gravou.")


def publicar_texto(estado, vistos, modo_semente, resumo, origem, texto, link):
    texto = " ".join((texto or "").split())
    if len(texto) < 15 or len(texto) > 400 or not link:
        return
    selecao, eh_corte, motivo = avaliar_noticia(texto)
    if motivo in ("sem_termo", "sem_selecao"):
        return
    if motivo:
        log(f"  Ignorado ({ROTULOS_BLOQUEIO.get(motivo, motivo)}): {texto[:100]}")
        return
    if origem == "twitter":
        mensagem = mensagem_twitter(texto, link)
    else:
        mensagem = mensagem_portal(texto, link)
    entregar(
        estado, vistos, modo_semente, resumo,
        identificador(selecao, eh_corte, link),
        mensagem,
        selecao,
    )


def link_absoluto(base, link):
    if not link:
        return None
    link = link.strip()
    if link.startswith("/"):
        link = urljoin(base, link)
    if not link.startswith("http://") and not link.startswith("https://"):
        return None
    if " " in link:
        return None
    return link


def varrer_portais(estado, vistos, modo_semente, resumo):
    log(f"Lendo {len(URLS_PORTAIS)} portais...")
    for url in URLS_PORTAIS:
        try:
            resposta = requests.get(url, headers=HEADERS_WEB, timeout=20)
            resposta.raise_for_status()
            soup = BeautifulSoup(resposta.text, "html.parser")
            for item in soup.find_all(["a", "h2", "h3"]):
                titulo = item.get_text(" ", strip=True)
                if item.name == "a":
                    link = item.get("href")
                else:
                    pai = item.find_parent("a")
                    link = pai.get("href") if pai else None
                publicar_texto(
                    estado, vistos, modo_semente, resumo, "portal",
                    titulo, link_absoluto(url, link),
                )
        except Exception:
            log(f"  Falha ao ler o portal: {url}")


def varrer_twitter(estado, vistos, modo_semente, resumo):
    log(f"Lendo {len(URLS_TWITTER_RSS)} feeds...")
    for url in URLS_TWITTER_RSS:
        if "COLE_AQUI" in url:
            continue
        try:
            resposta = requests.get(url, headers=HEADERS_WEB, timeout=20)
            resposta.raise_for_status()
            feed = feedparser.parse(resposta.text)
            for post in feed.entries:
                publicar_texto(
                    estado, vistos, modo_semente, resumo, "twitter",
                    post.get("title", ""), post.get("link", ""),
                )
        except Exception:
            log(f"  Falha ao ler o feed: {url}")


def texto_do_elenco_atual(soup):
    alvo = soup.find(id="Current_squad")
    if alvo is None:
        return ""
    secao = alvo.find_parent("section")
    if secao is not None:
        return secao.get_text(" ", strip=True)
    titulo = alvo if alvo.name in ("h2", "h3", "h4") else alvo.find_parent(["h2", "h3", "h4"])
    if titulo is None:
        return ""
    partes = []
    for irmao in titulo.find_next_siblings():
        if irmao.name in ("h2", "h3", "h4"):
            break
        partes.append(irmao.get_text(" ", strip=True))
        if len(partes) >= 8:
            break
    return " ".join(partes)


def elenco_confirma_janela(texto):
    texto_n = normalizar(texto)
    if normalizar(JANELA_FIFA_ATUAL) not in texto_n:
        return False
    sinais = list(SINAIS_ELENCO_WIKI)
    sinais.extend(FRASES_GATILHO_WIKIPEDIA)
    return any(normalizar(sinal) and normalizar(sinal) in texto_n for sinal in sinais)


def varrer_wikipedia(estado, vistos, modo_semente, resumo):
    log(f"Lendo {len(URLS_WIKIPEDIA)} páginas da Wikipedia...")
    sucessos = 0
    sem_secao = 0
    for url in URLS_WIKIPEDIA:
        try:
            resposta = requests.get(url, headers=HEADERS_WIKI, timeout=20)
            resposta.raise_for_status()
            sucessos += 1
            soup = BeautifulSoup(resposta.text, "html.parser")
            texto = texto_do_elenco_atual(soup)
            if not texto:
                sem_secao += 1
            elif elenco_confirma_janela(texto):
                # O país sai do endereço. O texto da página cita os adversários primeiro.
                selecao, _ = classificar_noticia(url)
                if selecao:
                    entregar(
                        estado, vistos, modo_semente, resumo,
                        identificador(selecao, False, url),
                        mensagem_wiki(selecao, url),
                        selecao,
                    )
                else:
                    log(f"  País não reconhecido na página: {url}")
        except Exception as exc:
            resposta = getattr(exc, "response", None)
            codigo = f" (código {resposta.status_code})" if resposta is not None else ""
            log(f"  Falha na Wikipedia{codigo}: {url}")
        time.sleep(0.5)
    log(f"Wikipedia lida: {sucessos} de {len(URLS_WIKIPEDIA)}. Sem a seção do elenco: {sem_secao}.")
    return sucessos


def finalizar_semente(estado, sucessos_wiki):
    limite = max(1, int(len(URLS_WIKIPEDIA) * 0.8))
    if sucessos_wiki >= limite:
        estado["seed_completo"] = True
    gravou = salvar_estado(estado)
    if estado["seed_completo"] and gravou:
        log(f"Caderno inicial pronto, com {len(estado['ids'])} registros.")
        log("Daqui em diante, só o que for novidade vai para o Telegram.")
    elif sucessos_wiki >= limite:
        log("A leitura acabou, mas o caderno online não gravou. Continuo em silêncio na próxima volta.")
    else:
        log(f"A Wikipedia respondeu {sucessos_wiki} de {len(URLS_WIKIPEDIA)} páginas.")
        log("Ainda não vou avisar o grupo. Na próxima volta tento de novo.")


def executar_varredura():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    log("")
    log("==============================================")
    log(f"[{agora}] Iniciando varredura. Janela: {JANELA_FIFA_ATUAL}")
    if not TOKEN or not CHAT_ID:
        log("Faltam TELEGRAM_TOKEN e TELEGRAM_CHAT_ID nas variáveis do Render.")
        return
    estado = carregar_estado()
    if estado is None:
        return
    modo_semente = not estado["seed_completo"]
    if modo_semente:
        log("Primeira varredura completa: vou anotar o que já existe e ficar em silêncio.")
    else:
        log(f"Caderno carregado com {len(estado['ids'])} registros.")
    vistos = set()
    resumo = {"enviados": 0, "anotados": 0}
    varrer_portais(estado, vistos, modo_semente, resumo)
    varrer_twitter(estado, vistos, modo_semente, resumo)
    sucessos_wiki = varrer_wikipedia(estado, vistos, modo_semente, resumo)
    if modo_semente:
        finalizar_semente(estado, sucessos_wiki)
    log(f"Varredura encerrada. Enviados: {resumo['enviados']}. Anotados em silêncio: {resumo['anotados']}.")


app = Flask(__name__)


@app.route("/")
def vivo():
    return "O bot está no ar."


def manter_vivo():
    porta = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=porta, use_reloader=False)


if __name__ == "__main__":
    preparar_console()
    servidor = threading.Thread(target=manter_vivo, daemon=False)
    servidor.start()
    log("Bot iniciado.")
    log(f"Pausa entre varreduras: {INTERVALO_SEGUNDOS} segundos.")
    while True:
        try:
            executar_varredura()
        except Exception as exc:
            log(f"Erro inesperado na varredura: {type(exc).__name__}")
        time.sleep(INTERVALO_SEGUNDOS)
