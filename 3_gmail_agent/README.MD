# Gmail AI Agent

AI agent pro automatické třídění Gmailu a jednoduchý chat nad e-mailovou
schránkou. Projekt vznikl jako úkol v rámci kurzu **AI agenti**.

## Co agent umí

Agent propojuje **Python + Gmail API + OpenAI Agents SDK + lokální LLM
(Ollama / Llama 3.1 8B)**.

Má tři režimy:

-   **cleanup** -- projde historickou poštu a roztřídí ji.
-   **live** -- zpracuje nové, dosud nezpracované zprávy v Inboxu.
-   **chat** -- umožní přirozené dotazy nad Gmailem, například „Kolik
    e-mailů mi přišlo za posledních 30 dní?" nebo „Najdi posledních 5
    důležitých e-mailů."

Chat je záměrně **read-only** -- vyhledává a analyzuje, ale nemění
poštu.

## Jak klasifikace funguje

Každý e-mail dostane jednu kategorii:

  -----------------------------------------------------------------------
  Kategorie               Význam                  Akce
  ----------------------- ----------------------- -----------------------
  `IMPORTANT`             vyžaduje pozornost,     označení jako důležité
                          odpověď nebo rozhodnutí 

  `NORMAL`                běžná informační zpráva bez změny

  `ADVERTISEMENT`         reklama, newsletter,    archivace
                          marketing               

  `UNCERTAIN`             agent si není           bez změny, určeno k
                          dostatečně jistý        auditu
  -----------------------------------------------------------------------

Každá zpracovaná zpráva dostane `AI_PROCESSED` a klasifikační štítek
`AI_IMPORTANT`, `AI_NORMAL`, `AI_ADVERTISEMENT` nebo `AI_UNCERTAIN`.

**Reklamy se nemažou.** Pouze se odstraní z Inboxu a zůstávají dostupné
ve „Všechny zprávy" a pod štítkem `AI_ADVERTISEMENT`.

## Jak agent rozhoduje

Klasifikace je hybridní:

``` text
Gmail → Python → pravidla / LLM → kategorie → AI agent → tool → Gmail API
```

Jednoznačné případy řeší deterministická pravidla. Složitější zprávy
jsou předány lokálnímu LLM. Agent může využít také kontext e-mailového
vlákna.

Pro Gmail akce používá skutečné **function tools**. Součástí řešení je
kontrola správného toolu, retry mechanismus a deterministický fallback.

## Chat nad Gmailem

V režimu `chat` agent používá read-only tools pro počítání e-mailů,
vyhledávání zpráv, načtení detailu e-mailu a statistiky AI klasifikace.

Příklady:

``` text
Kolik e-mailů mi přišlo za posledních 30 dní?
Kolik reklam agent našel?
Najdi posledních 5 důležitých e-mailů.
Najdi e-maily od České spořitelny.
Ukaž posledních 10 AI_UNCERTAIN zpráv.
```

Uživatel nemusí znát Gmail query syntax -- potřebný dotaz sestaví agent.

## Použité technologie

-   Python 3.12+
-   Gmail API + Google OAuth 2.0
-   OpenAI Agents SDK
-   Ollama + Llama 3.1 8B
-   OpenAI-compatible API
-   Pydantic
-   BeautifulSoup
-   asyncio / logging
-   VS Code

## Instalace

Vytvoření prostředí a instalace závislostí:

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Do složky projektu vlož vlastní Google OAuth soubor:

``` text
credentials.json
```

Při prvním spuštění proběhne autorizace Gmailu a vytvoří se
`token.json`.

Je také nutné nastavit dostupný OpenAI-compatible LLM endpoint a model.
Projekt byl testován s **Ollama + llama3.1:8b**.

> `credentials.json`, `token.json`, `.venv`, `.env` a logy nejsou
> součástí GitHub repozitáře.

## Spuštění

``` powershell
python gmail_agent.py
```

V `gmail_agent.py` zvol režim:

``` python
MODE = "cleanup"   # historická pošta
MODE = "live"      # nové zprávy
MODE = "chat"      # chat nad Gmailem
```

Pro první bezpečný test:

``` python
MODE = "cleanup"
DRY_RUN = True
BATCH_SIZE = 20
```

`DRY_RUN = True` klasifikuje a ukáže plánované akce, ale Gmail skutečně
nezmění. Po ověření lze nastavit `DRY_RUN = False`.

## Logování a audit

Každý běh vytváří log ve složce `logs/`. Obsahuje klasifikaci, důvod,
provedenou akci, chyby, retry/fallback a dobu zpracování.

Audit lze dělat přímo v Gmailu:

``` text
label:AI_IMPORTANT
label:AI_ADVERTISEMENT
label:AI_UNCERTAIN
```

Cleanup lze kdykoliv ukončit pomocí `Ctrl+C`. Již zpracované zprávy
zůstávají označené `AI_PROCESSED`, takže další spuštění pokračuje pouze
s nezpracovanými e-maily.

## Bezpečnost

Projekt používá:

-   `DRY_RUN` pro testování,
-   kontrolu `message_id` a kategorie,
-   validaci tool callů,
-   retry + fallback,
-   žádné automatické mazání,
-   read-only chat,
-   logování.

## Struktura projektu

``` text
3_gmail_agent/
├── gmail_agent1.1.py
├── README.md
├── requirements.txt
├── .gitignore
├── credentials.json    # lokální, není v GitHubu
├── token.json          # lokální, není v GitHubu
└── logs/               # lokální, není v GitHubu
```

## Shrnutí

Projekt demonstruje skutečného AI agenta nad reálným externím systémem:

``` text
LLM + Agent + Tools + Gmail API + reálná data
```

Agent umí historický cleanup, průběžné zpracování nové pošty a read-only
chat nad Gmail schránkou. Nejde tedy pouze o LLM klasifikátor -- agent
používá nástroje a podle výsledku rozhodování provádí řízené Gmail
operace.

### Poznámka k MCP

MCP bylo při návrhu zvažováno, ale pro tento úkol byly zvoleny nativní
tools OpenAI Agents SDK. Pro rozsah projektu jde o jednodušší způsob,
jak demonstrovat agentní rozhodování a tool calling nad Gmail API.
