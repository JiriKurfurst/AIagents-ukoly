import json
import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# 1. ZÁKLADNÍ NASTAVENÍ
# ============================================================

# Načte proměnné ze souboru .env.
load_dotenv()

# Vytvoří klienta pro komunikaci s OpenAI API.
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Sem vlož URL stránky, která ti funguje.
URL = "https://vkolo.cz/rohy/2671-rohy-m-wave-anatom-cerne-matne-4015493404156.html"

# Model lze změnit také přes soubor .env.
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")


# ============================================================
# 2. PYTHON FUNKCE – TOOL
# ============================================================

def calculate_score(scores: list[int]) -> dict:
    """
    Spočítá celkové body a procentuální hodnocení.

    LLM této funkci předá například:
    [3, 2, 3, 2, 1]
    """

    print("\n[PYTHON TOOL] Spouštím calculate_score()")
    print(f"[PYTHON TOOL] Přijaté známky: {scores}")

    total = sum(scores)
    maximum = len(scores) * 3
    percentage = round(total / maximum * 100, 1)

    result = {
        "total": total,
        "maximum": maximum,
        "percentage": percentage,
    }

    print(f"[PYTHON TOOL] Výsledek funkce: {result}")

    return result


# ============================================================
# 3. POPIS TOOLU PRO LLM
# ============================================================

# Toto funkci nespouští.
# Je to pouze popis, podle kterého LLM pozná:
# - jak se tool jmenuje,
# - co dělá,
# - jaká data má předat.
tools = [
    {
        "type": "function",
        "name": "calculate_score",
        "description": (
            "Spočítá celkové body a procentuální hodnocení "
            "produktové stránky."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "description": (
                        "Pět známek produktové stránky, "
                        "každá v rozsahu 0 až 3."
                    ),
                    "items": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3,
                    },
                }
            },
            "required": ["scores"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


# ============================================================
# 4. STAŽENÍ WEBOVÉ STRÁNKY
# ============================================================

print("=" * 60)
print("KROK 1: STAHUJI WEBOVOU STRÁNKU")
print("=" * 60)
print(f"URL: {URL}")

web_response = requests.get(
    URL,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
    },
    timeout=20,
)

# Pokud web vrátí například 403 nebo 404,
# program se zde zastaví a vypíše chybu.
web_response.raise_for_status()

print(f"HTTP stav: {web_response.status_code}")
print("Stránka byla úspěšně stažena.")


# ============================================================
# 5. PŘEVOD HTML NA ČITELNÝ TEXT
# ============================================================

print("\n" + "=" * 60)
print("KROK 2: PŘEVÁDÍM HTML NA TEXT")
print("=" * 60)

soup = BeautifulSoup(
    web_response.text,
    "html.parser",
)

# Odstraníme části stránky, které nechceme posílat LLM.
for element in soup(["script", "style", "noscript"]):
    element.decompose()

page_text = soup.get_text(
    separator=" ",
    strip=True,
)

# Omezíme délku kvůli tokenům.
page_text = page_text[:8_000]

print(f"Počet znaků posílaných LLM: {len(page_text)}")

print("\nPrvních 5000 znaků textu:")
print("-" * 60)
print(page_text[:5000])
print("-" * 60)


# ============================================================
# 6. PRVNÍ VOLÁNÍ LLM
# ============================================================

print("\n" + "=" * 60)
print("KROK 3: PRVNÍ VOLÁNÍ LLM")
print("=" * 60)
print("LLM má stránku vyhodnotit a požádat o vhodný tool.")

response = client.responses.create(
    model=MODEL,
    tools=tools,
    input=f"""
Analyzuj produktovou stránku.

Ohodnoť následující kritéria známkami 0–3:

- srozumitelnost produktu
- úplnost informací
- možnost nákupu
- důvěryhodnost
- podpora rozhodování zákazníka

Pro výpočet celkového skóre použij vhodný dostupný nástroj.

Prosím o shrnutí a jedno doporučení pro zlepšení stránky. 

URL:
{URL}

Text stránky:
{page_text}
""",
)

print(f"ID první odpovědi: {response.id}")


# ============================================================
# 7. AGENTNÍ LOOP
# ============================================================

# Loop dovoluje následující průběh:
#
# LLM → tool → LLM → případně další tool → LLM → konečný text
#
# V našem příkladu očekáváme většinou:
# 1. volání LLM,
# 2. jeden tool,
# 3. druhé volání LLM,
# 4. konečnou odpověď.

iteration = 1

while True:

    print("\n" + "=" * 60)
    print(f"KROK 4: ZPRACOVÁNÍ ODPOVĚDI LLM – ITERACE {iteration}")
    print("=" * 60)

    tool_calls = []

    # Projdeme všechny položky, které LLM vrátilo.
    for item in response.output:

        print(f"Typ položky od LLM: {item.type}")

        # Zajímá nás položka typu function_call.
        if item.type == "function_call":
            tool_calls.append(item)

    # --------------------------------------------------------
    # LLM NECHCE ŽÁDNÝ TOOL
    # --------------------------------------------------------
    #
    # To znamená, že už vytvořilo finální textovou odpověď.
    if not tool_calls:

        print("\nLLM už nepožaduje další tool.")
        print("Agentní loop končí.")

        print("\n" + "=" * 60)
        print("FINÁLNÍ ODPOVĚĎ LLM")
        print("=" * 60)

        print(response.output_text)

        break

    # --------------------------------------------------------
    # LLM POŽADUJE JEDEN NEBO VÍCE TOOLŮ
    # --------------------------------------------------------

    tool_outputs = []

    for tool_call in tool_calls:

        print("\nLLM požaduje spuštění toolu:")
        print(f"Název: {tool_call.name}")
        print(f"Argumenty jako JSON: {tool_call.arguments}")

        # Arguments přichází z LLM jako JSON text.
        # json.loads() jej převede na Python slovník.
        arguments = json.loads(tool_call.arguments)

        print("\nArgumenty převedené na Python:")
        print(
            json.dumps(
                arguments,
                indent=2,
                ensure_ascii=False,
            )
        )

        # ----------------------------------------------------
        # VÝBĚR A SPUŠTĚNÍ PYTHON FUNKCE
        # ----------------------------------------------------

        if tool_call.name == "calculate_score":

            tool_result = calculate_score(
                scores=arguments["scores"]
            )

        else:
            # Ochrana pro případ, že LLM požádá o neznámý tool.
            tool_result = {
                "error": f"Neznámý tool: {tool_call.name}"
            }

        print("\nVýsledek, který vrátíme zpět LLM:")
        print(
            json.dumps(
                tool_result,
                indent=2,
                ensure_ascii=False,
            )
        )

        # Připravíme výsledek ve formátu,
        # který očekává Responses API.
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": json.dumps(
                    tool_result,
                    ensure_ascii=False,
                ),
            }
        )

    # ========================================================
    # 8. DALŠÍ VOLÁNÍ LLM S VÝSLEDKEM TOOLU
    # ========================================================

    print("\n" + "=" * 60)
    print("KROK 5: VRACÍM VÝSLEDEK TOOLU ZPĚT DO LLM")
    print("=" * 60)

    response = client.responses.create(
        model=MODEL,

        # Propojení s předchozí odpovědí.
        previous_response_id=response.id,

        # Výsledek nebo výsledky Python toolů.
        input=tool_outputs,

    # Jasný úkol pro druhou fázi.
    instructions="""
Na základě hodnocení stránky a výsledku nástroje vytvoř
stručnou finální odpověď v češtině.

Uveď:
- procentuální výsledek,
- stručné shrnutí a jedno konkrétní doporučení pro zlepšení stránky.

Nevolej další nástroj.
""",

        # LLM by teoreticky mohlo požádat o další tool.
        tools=tools,
    )

    print(f"ID nové odpovědi: {response.id}")

    iteration += 1

    # Ochrana proti nekonečnému loopu.
    if iteration > 5:
        raise RuntimeError(
            "Agent překročil maximální počet 5 iterací."
        )