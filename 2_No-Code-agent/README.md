# No-Code AI Agent – Motor Database

Projekt demonstruje AI agenta vytvořeného v **LangFlow**, který dokáže pomocí přirozeného jazyka pracovat s PostgreSQL databází elektromotorů.

Uživatel položí otázku v běžném jazyce. AI Agent vyhodnotí požadavek, v případě potřeby použije SQL Database Tool, vytvoří SQL dotaz nad PostgreSQL databází a výsledek převede zpět do přirozeného jazyka.

Projekt používá:

- LangFlow
- OpenAI API
- PostgreSQL
- SQLAlchemy / psycopg2
- Podman
- Adminer
- Python

---

# Architektura

```text
User
  │
  ▼
Chat Input
  │
  ▼
LangFlow Agent
  │
  ├── OpenAI LLM
  │
  └── SQL Database Tool
          │
          ▼
      PostgreSQL
          │
          ▼
        Podman
  │
  ▼
Chat Output
```

PostgreSQL a Adminer běží v kontejnerech pomocí Podman Compose.

LangFlow běží lokálně na hostitelském počítači.

Agent používá SQL Database Tool jako nástroj a sám rozhoduje, kdy je pro zodpovězení otázky potřeba databázový dotaz.

---

# Quick Start

## 1. Požadavky

Na počítači musí být nainstalováno:

- Python 3
- Podman Desktop
- LangFlow Desktop
- webový prohlížeč

Pro používání AI agenta je potřeba vlastní **OpenAI API Key**.

API klíč není součástí projektu.

---

## 2. Stažení projektu

Projekt lze stáhnout pomocí Git:

```bash
git clone <URL_REPOZITARE>
cd No-Code-agent
```

Případně lze repozitář stáhnout z GitHubu jako ZIP a rozbalit.

---

## 3. Spuštění Podman Desktop

Před spuštěním projektu spusťte **Podman Desktop**.

Počkejte, dokud nebude Podman připraven.

---

## 4. Spuštění projektu

V kořenové složce projektu spusťte:

```bash
python start.py
```

`start.py` automaticky:

1. zkontroluje strukturu projektu,
2. zkontroluje dostupnost Podmanu,
3. spustí PostgreSQL a Adminer,
4. počká na inicializaci PostgreSQL,
5. zkontroluje instalaci LangFlow,
6. zkontroluje potřebné Python dependencies,
7. spustí LangFlow backend,
8. počká na dostupnost LangFlow na portu `7860`,
9. otevře LangFlow a Adminer v prohlížeči.

Po úspěšném spuštění jsou služby dostupné na:

```text
LangFlow: http://127.0.0.1:7860
Adminer:  http://127.0.0.1:8080
```

---

# První spuštění LangFlow workflow

Při prvním spuštění projektu na novém počítači je potřeba do LangFlow importovat připravený workflow.

Importujte soubor:

```text
langflow/no-code-agent.json
```

Exportovaný JSON obsahuje připravené komponenty agenta, jejich konfiguraci a propojení.

Základní flow:

```text
Chat Input
     │
     ▼
   Agent ◄──── SQL Database Tool
     │
     ▼
Chat Output
```

SQL Database komponenta funguje jako nástroj agenta.

---

# Nastavení OpenAI API Key

OpenAI API Key není z bezpečnostních důvodů uložen v projektu ani v exportovaném LangFlow workflow.

Po importu workflow:

1. otevřete komponentu **Agent**,
2. najděte pole **API Key**,
3. vložte vlastní OpenAI API Key,
4. uložte změnu komponenty / workflow,
5. otevřete **Playground**.

Agent je následně připraven k použití.

API klíč nikdy neukládejte přímo do Git repozitáře.

Po nastavení API klíče není při běžném dalším spuštění projektu potřeba workflow znovu importovat.

---

# Struktura projektu

```text
No-Code-agent/
│
├── compose.yaml
├── start.py
├── README.md
├── .gitignore
│
├── database/
│   ├── 01-schema.sql
│   └── 02-sample-data.sql
│
└── langflow/
    └── no-code-agent.json
```

## Význam hlavních souborů

### `compose.yaml`

Definuje kontejnery projektu.

Pomocí Podman Compose spouští:

- PostgreSQL
- Adminer

### `start.py`

Hlavní startovací skript projektu.

Automatizuje kontrolu prostředí a spuštění PostgreSQL, Admineru a LangFlow.

### `database/01-schema.sql`

Obsahuje definici struktury demonstrační PostgreSQL databáze.

### `database/02-sample-data.sql`

Naplní databázi demonstračními daty.

### `langflow/no-code-agent.json`

Export hotového LangFlow workflow.

Obsahuje konfiguraci AI agenta a SQL Database Tool, ale neobsahuje OpenAI API Key.

---

# PostgreSQL

Projekt používá PostgreSQL databázi:

```text
Host:     127.0.0.1
Port:     5432
Database: motor_sales
User:     motor_admin
Password: motor_password
```

LangFlow SQL Database komponenta používá SQLAlchemy connection string:

```text
postgresql+psycopg2://motor_admin:motor_password@127.0.0.1:5432/motor_sales
```

---

# Adminer

Adminer slouží k vizuální kontrole PostgreSQL databáze.

Po spuštění projektu je dostupný na:

```text
http://127.0.0.1:8080
```

Pro přihlášení použijte:

```text
System:   PostgreSQL
Server:   postgres
Username: motor_admin
Password: motor_password
Database: motor_sales
```

## Rozdíl mezi připojením LangFlow a Admineru

LangFlow běží na hostitelském počítači, proto se k PostgreSQL připojuje přes:

```text
127.0.0.1
```

Adminer běží uvnitř stejné kontejnerové sítě jako PostgreSQL, proto používá hostname:

```text
postgres
```

Tento rozdíl je záměrný.

---

# Databázový model

Demonstrační PostgreSQL databáze obsahuje tabulky:

```text
motors
customers
orders
order_items
motor_prices
inventory
```

## `motors`

Obsahuje informace o jednotlivých typech elektromotorů.

## `customers`

Obsahuje zákazníky.

## `orders`

Obsahuje objednávky zákazníků.

## `order_items`

Obsahuje jednotlivé položky objednávek a vazbu mezi objednávkami a motory.

## `motor_prices`

Obsahuje cenové informace k motorům.

## `inventory`

Obsahuje informace o skladových zásobách.

---

# Vyhodnocování prodejů

Databáze neobsahuje samostatnou tabulku:

```text
sales
```

Informace o prodejích se získávají propojením tabulek:

```text
motors
   │
   ▼
order_items
   │
   ▼
orders
```

Pro skutečně dodané / prodané množství se používá:

```text
order_items.delivered_quantity
```

a objednávky se stavem:

```text
orders.order_status = 'DELIVERED'
```

Agent má tuto logiku uvedenou ve svých instrukcích, aby při práci s databází nevytvářel neexistující tabulky nebo sloupce.

---

# LangFlow workflow

Workflow se skládá z komponent:

```text
Chat Input
Agent
SQL Database
Chat Output
```

Propojení:

```text
Chat Input ─────► Agent ─────► Chat Output
                    ▲
                    │
             SQL Database
                 Toolset
```

SQL Database komponenta má zapnutý:

```text
Tool Mode
```

Její výstup `Toolset` je připojen do:

```text
Agent → Tools
```

Agent proto může SQL nástroj automaticky použít v okamžiku, kdy otázka vyžaduje informace z databáze.

---

# Instrukce AI agenta

Agent je nakonfigurován pro práci s databází motorů.

Jeho instrukce obsahují zejména:

- popis databázového schématu,
- názvy tabulek a důležitých sloupců,
- pravidla pro výpočet prodejů,
- informaci, že tabulka `sales` neexistuje,
- pravidlo používat SQL Database Tool pro otázky nad databázovými hodnotami,
- zákaz vymýšlení neexistujících tabulek nebo sloupců.

Díky tomu agent nejprve vyhodnotí otázku a následně vytvoří odpovídající SQL dotaz nad dostupnými tabulkami.

---

# Příklady dotazů

Po otevření LangFlow Playground lze agenta testovat například otázkami:

```text
Kolik motorů DS4-132-AA se prodalo mezi 2026-01-01 a 2026-06-30?
```

```text
Který typ motoru se prodával nejlépe?
```

```text
Který zákazník objednal nejvíce motorů?
```

```text
Jaké jsou skladové zásoby motoru DS4-132-AA?
```

```text
Jaká je cena motoru DS4-132-AA?
```

Agent by měl podle charakteru otázky automaticky použít SQL Database Tool a vrátit odpověď v přirozeném jazyce.

---

# Kontrola databázového připojení

Funkčnost připojení lze ověřit přímo v SQL Database komponentě.

Například:

```sql
SELECT current_database();
```

Očekávaný výsledek:

```text
motor_sales
```

Seznam dostupných tabulek lze ověřit:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

---

# Kontrola PostgreSQL kontejneru

Stav kontejnerů lze zobrazit:

```bash
podman ps
```

PostgreSQL kontejner by měl být ve stavu:

```text
healthy
```

---

# Zastavení projektu

Kontejnery PostgreSQL a Admineru lze zastavit příkazem:

```bash
podman compose down
```

Databázová data při tomto způsobu zůstanou zachována.

Při dalším spuštění projektu stačí znovu použít:

```bash
python start.py
```

---

# Reset databáze

Inicializační SQL soubory se automaticky provedou při prvním vytvoření PostgreSQL datového volume.

Pokud je potřeba databázi kompletně vytvořit znovu:

```bash
podman compose down -v
```

a následně:

```bash
python start.py
```

> **Upozornění:** `podman compose down -v` odstraní PostgreSQL volume a všechna data uložená v databázi projektu.

Databáze se při dalším spuštění znovu vytvoří z SQL souborů ve složce:

```text
database/
```

---

# Řešení problémů

## LangFlow se nespustí

Zkontrolujte log:

```text
langflow-start.log
```

`start.py` při problému se spuštěním LangFlow zobrazí také poslední řádky tohoto logu.

---

## PostgreSQL není dostupný

Ověřte kontejnery:

```bash
podman ps
```

Případně spusťte:

```bash
podman compose up -d
```

---

## Agent se nepřipojí k databázi

Zkontrolujte v komponentě SQL Database hodnotu:

```text
postgresql+psycopg2://motor_admin:motor_password@127.0.0.1:5432/motor_sales
```

a ověřte, že PostgreSQL kontejner běží.

---

## Chyba `No module named psycopg2`

`start.py` kontroluje potřebné Python dependencies pro LangFlow a v případě potřeby je do jeho prostředí doplní.

---

## Agent neodpovídá pomocí OpenAI

Zkontrolujte, zda byl v komponentě **Agent** nastaven platný vlastní OpenAI API Key.

API klíč není součástí projektu.

---

# Bezpečnost

Repozitář nesmí obsahovat skutečné API klíče, přístupové tokeny ani jiné citlivé údaje.

Exportovaný soubor:

```text
langflow/no-code-agent.json
```

obsahuje konfiguraci AI agenta, ale neobsahuje OpenAI API Key.

Každý uživatel projektu musí použít vlastní OpenAI API Key.

Doporučený `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
langflow-start.log
```

---

# Poznámka k datům

PostgreSQL databáze obsahuje demonstrační data vytvořená pouze pro účely tohoto projektu.

Nejedná se o skutečná výrobní, zákaznická ani obchodní data.

---

# Doporučený postup pro vyzkoušení projektu

Pro nové prostředí je doporučen následující postup:

```text
1. Stáhnout repozitář
        ↓
2. Spustit Podman Desktop
        ↓
3. Spustit python start.py
        ↓
4. Počkat na PostgreSQL a LangFlow
        ↓
5. Importovat langflow/no-code-agent.json
        ↓
6. V Agent komponentě vložit vlastní OpenAI API Key
        ↓
7. Otevřít Playground
        ↓
8. Položit otázku nad databází
        ↓
9. Agent použije SQL Database Tool
        ↓
10. Výsledek je vrácen v přirozeném jazyce
```

Po prvním importu workflow a nastavení API klíče stačí při běžném dalším použití spustit projekt pomocí:

```bash
python start.py
```