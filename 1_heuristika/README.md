# Heuristická analýza produktové stránky pomocí LLM

Jednoduchý Python projekt vytvořený v rámci úkolu ze semináře **AI agenti**.

## Zadání

Vytvořit Python skript, který:

1. zavolá LLM API,
2. umožní LLM vybrat a zavolat dostupný nástroj (tool),
3. spustí odpovídající Python funkci,
4. vrátí výsledek nástroje zpět do LLM,
5. zobrazí finální odpověď.

## Jak projekt funguje

Skript stáhne skutečnou produktovou stránku pomocí `requests` a pomocí `BeautifulSoup` převede HTML na text.

LLM následně provede heuristickou analýzu podle pěti kritérií:

* srozumitelnost produktu,
* úplnost informací,
* možnost nákupu,
* důvěryhodnost,
* podpora rozhodování zákazníka.

Každé kritérium je hodnoceno **0–3 body**.

LLM má k dispozici tool:

`calculate_score`

Tool je implementován jako Python funkce, která z hodnocení vypočítá:

* celkový počet bodů,
* maximální počet bodů,
* procentuální skóre.

Výsledek Python funkce je následně vrácen zpět do LLM pro vytvoření finální odpovědi.

### Zjednodušený průběh

`Web → Python → LLM → Tool call → Python funkce → LLM → Výsledek`

Skript používá agentní loop, takže je připraven i na případné další požadavky LLM na použití nástrojů.

## Instalace

Potřebné knihovny:

```bash
pip install openai requests beautifulsoup4 python-dotenv
```

## OpenAI API klíč

Vytvořte soubor `.env`:

```text
OPENAI_API_KEY=your_api_key
```

Soubor `.env` není z bezpečnostních důvodů součástí repozitáře.

Volitelně lze v `.env` nastavit také použitý model:

```text
OPENAI_MODEL=gpt-5-mini
```

## Spuštění

```bash
python main_prog_2.py
```

URL analyzované produktové stránky lze změnit v proměnné `URL` na začátku skriptu.

## Poznámka

Projekt je záměrně vytvořen jako jednoduchý a čitelný příklad pro pochopení principu **LLM tool/function callingu**, nikoliv jako univerzální nástroj pro scraping e-shopů.
