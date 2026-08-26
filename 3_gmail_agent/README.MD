# Gmail AI Agent

Třetí úkol v rámci kurzu **AI agenti**.

Cílem projektu je vytvořit AI agenta, který pracuje s reálnou Gmail schránkou, analyzuje příchozí e-maily pomocí LLM a podle jejich obsahu automaticky rozhoduje o další akci.

Agent je vytvořen v Pythonu a využívá Gmail API a lokálně provozovaný LLM.

---

## Co agent umí

Agent:

1. Připojí se k Gmailu pomocí Gmail API a OAuth 2.0.
2. Načte nové, dosud nezpracované e-maily.
3. Získá z e-mailu odesílatele, předmět a obsah zprávy.
4. Předá obsah LLM ke klasifikaci.
5. Rozhodne o kategorii e-mailu.
6. Podle výsledku provede odpovídající akci v Gmailu.
7. Označí e-mail štítkem `AI_PROCESSED`, aby nebyl při dalším spuštění zpracován znovu.
8. Průběh zpracování zapisuje do terminálu a log souboru.
9. Po dokončení zobrazí celkovou dobu běhu.

---

## Kategorie e-mailů

Agent používá následující kategorie:

### IMPORTANT

E-mail vyžaduje pozornost uživatele, například:

- žádost o rozhodnutí,
- žádost o schválení,
- přímý úkol nebo otázka,
- důležitá změna,
- zrušení schůzky,
- problém s doručením zprávy.

**Akce:** e-mail je označen jako důležitý.

### ADVERTISEMENT

Reklamní, marketingové nebo automatické obsahové zprávy, například:

- newslettery,
- reklamní nabídky,
- slevové kampaně,
- marketingové e-maily,
- vybrané automatické notifikace sociálních sítí.

**Akce:** e-mail je archivován.

### NORMAL

Běžná informační komunikace, která nevyžaduje konkrétní rozhodnutí nebo akci.

**Akce:** e-mail zůstává beze změny.

### UNCERTAIN

Agent nemá dostatek informací pro spolehlivé rozhodnutí.

**Akce:** e-mail zůstává beze změny.

---

## Architektura

Zjednodušený princip:

```text
Gmail
  │
  ▼
Gmail API
  │
  ▼
Python Gmail AI Agent
  │
  ├── načtení e-mailu
  │
  ▼
LLM
  │
  ├── IMPORTANT
  ├── ADVERTISEMENT
  ├── NORMAL
  └── UNCERTAIN
  │
  ▼
Rozhodnutí agenta
  │
  ├── označit IMPORTANT
  ├── archivovat
  └── ponechat beze změny
  │
  ▼
Gmail API
  │
  ▼
AI_PROCESSED
```

Díky štítku `AI_PROCESSED` agent při dalším spuštění zpracovává pouze zprávy, které ještě nebyly vyhodnoceny.

---

## Použitý LLM

Projekt byl během vývoje testován s lokálně provozovaným modelem:

```text
llama3.1:8b
```

LLM server poskytuje OpenAI-compatible API.

Příklad:

```text
http://<LLM_SERVER>:11434/v1
```

Konkrétní IP adresa interního LLM serveru není součástí repozitáře.

---

## Gmail API

Pro komunikaci s Gmailem je použito:

- Gmail API
- OAuth 2.0
- Desktop OAuth Client

Uživatel při prvním spuštění autorizuje aplikaci ve svém Google účtu.

Projekt používá oprávnění umožňující čtení a úpravu zpráv, protože agent provádí akce jako označení důležitého e-mailu nebo archivace.

---

## Instalace

Doporučená verze:

```text
Python 3.12
```

Vytvoření virtuálního prostředí:

```powershell
python -m venv .venv
```

Aktivace ve Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalace závislostí:

```powershell
pip install -r requirements.txt
```

---

## Google OAuth credentials

Pro spuštění je nutné vytvořit vlastní OAuth 2.0 credentials v Google Cloud Console.

Postup:

1. vytvořit Google Cloud projekt,
2. aktivovat Gmail API,
3. nastavit OAuth consent screen,
4. vytvořit OAuth Client ID typu **Desktop app**,
5. stáhnout JSON credentials,
6. uložit soubor do adresáře projektu jako:

```text
credentials.json
```

Při prvním spuštění se otevře autorizace Google účtu.

Po úspěšné autorizaci vznikne lokální:

```text
token.json
```

### Bezpečnost

Soubory

```text
credentials.json
token.json
.env
```

jsou uvedeny v `.gitignore` a **nejsou součástí GitHub repozitáře**.

Každý uživatel projektu musí použít vlastní Google OAuth credentials.

---

## Spuštění

Agent se spouští:

```powershell
python gmail_agent.py
```

V terminálu se zobrazí například:

```text
======================================
GMAIL AI AGENT
DRY RUN: False
LLM: llama3.1:8b
LLM SERVER: http://<LLM_SERVER>:11434/v1
======================================

Nalezeno nezpracovaných e-mailů: 3
```

Následně agent postupně vypisuje klasifikaci jednotlivých zpráv:

```text
KLASIFIKACE:
CATEGORY: IMPORTANT
REASON: Žádost o rozhodnutí.

AKCE: Označeno jako IMPORTANT + AI_PROCESSED.
```

---

## DRY RUN

Pro bezpečné testování je možné použít režim:

```python
DRY_RUN = True
```

V tomto režimu agent e-maily analyzuje a vypisuje plánované akce, ale Gmail schránku skutečně neupravuje.

Například:

```text
AKCE: [DRY RUN] Archivoval bych a přidal AI_PROCESSED.
```

Pro skutečné provádění akcí:

```python
DRY_RUN = False
```

Před prvním ostrým spuštěním doporučuji vždy provést test v režimu `DRY_RUN = True`.

---

## Logování

Agent ukládá informace o průběhu běhu také do adresáře:

```text
logs/
```

Log obsahuje například:

- čas spuštění,
- konfiguraci agenta,
- počet zpracovaných zpráv,
- odesílatele,
- předmět,
- klasifikaci,
- důvod rozhodnutí,
- provedenou akci,
- případné chyby,
- celkovou dobu běhu.

Adresář `logs/` je uveden v `.gitignore`, takže osobní obsah e-mailů ani provozní logy nejsou nahrávány na GitHub.

---

## Struktura projektu

```text
3_gmail_agent/
│
├── gmail_agent.py
├── requirements.txt
├── README.MD
├── .gitignore
│
├── credentials.json     # pouze lokálně
├── token.json           # pouze lokálně
├── logs/                # pouze lokálně
└── .venv/               # pouze lokálně
```

---

## Bezpečnost

Repozitář neobsahuje:

- Gmail OAuth credentials,
- OAuth token,
- hesla,
- obsah Gmail schránky,
- logy zpracovaných e-mailů,
- interní adresu LLM serveru.

Citlivé soubory jsou vyloučeny pomocí `.gitignore`.

---

## Použité technologie

- Python 3.12
- Gmail API
- Google OAuth 2.0
- OpenAI-compatible API
- lokální LLM
- llama3.1:8b
- VS Code
- Git / GitHub

---

## Výsledek

Výsledkem je funkční AI agent napojený na reálnou Gmail schránku.

Agent kombinuje:

**Gmail API → Python → LLM → rozhodnutí → nástroj/akce → Gmail**

Nejde tedy pouze o klasifikaci textu pomocí LLM. Model rozhoduje o významu zprávy a agent na základě tohoto rozhodnutí provede odpovídající akci v externím systému.

Projekt byl nejprve ověřen v režimu `DRY_RUN` a následně úspěšně otestován i při skutečných změnách v Gmail schránce.