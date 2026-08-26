import asyncio
import base64
import logging
import os
import re
import time

from datetime import datetime
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup
from pydantic import BaseModel

from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# ============================================================
# 1. HLAVNÍ NASTAVENÍ
# ============================================================

# Režimy:
#
# "cleanup"
#   Jednorázové vyčištění historické přijaté pošty.
#
# "live"
#   Zpracování pouze nových nezpracovaných zpráv v Inboxu.
#
MODE = "cleanup"


# True:
#   Agent pouze ukáže, co BY udělal.
#   E-maily se nemění.
#
# False:
#   Agent skutečně provede akce v Gmailu.
#
DRY_RUN = True


# Počet e-mailů zpracovaných v jedné dávce.
#
# Pro první test doporučuji:
# BATCH_SIZE = 20
#
# Pro následný cleanup:
# BATCH_SIZE = 100
#
BATCH_SIZE = 100


# Gmail oprávnění.
#
# gmail.modify dovoluje čtení,
# archivaci a práci se štítky.
#
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


# Interní LLM server.
#
# Ollama běží na samostatném PC ve firemní LAN.
#
OLLAMA_URL = "http://10.165.200.27:11434/v1"

OLLAMA_MODEL = "llama3.1:8b"


# Gmail štítek označující již zpracovaný e-mail.
#
PROCESSED_LABEL_NAME = "AI_PROCESSED"


# ============================================================
# 2. LOGOVÁNÍ
# ============================================================

# Vytvoří složku logs, pokud ještě neexistuje.
#
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


# Každé spuštění má vlastní log soubor.
#
LOG_FILE = LOG_DIR / (
    f"gmail_agent_"
    f"{datetime.now():%Y-%m-%d_%H-%M-%S}.log"
)


# Logger
#
logger = logging.getLogger("gmail_agent")
logger.setLevel(logging.INFO)


# Zabrání zdvojeným handlerům například při restartu
# skriptu ve stejném Python procesu.
#
logger.handlers.clear()


# Formát logu
#
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# Výpis do terminálu
#
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)


# Výpis do souboru
#
file_handler = logging.FileHandler(
    LOG_FILE,
    encoding="utf-8",
)

file_handler.setFormatter(formatter)


logger.addHandler(console_handler)
logger.addHandler(file_handler)


# ============================================================
# 3. STATISTIKY BĚHU
# ============================================================

stats = {
    "processed": 0,
    "IMPORTANT": 0,
    "NORMAL": 0,
    "ADVERTISEMENT": 0,
    "UNCERTAIN": 0,
    "rules": 0,
    "llm": 0,
    "errors": 0,
}


# ============================================================
# 4. POMOCNÉ FUNKCE PRO ČAS
# ============================================================

def format_duration(seconds: float) -> str:
    """
    Převede počet sekund na hezky čitelný formát.
    """

    seconds = int(seconds)

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    if hours:
        return (
            f"{hours} h "
            f"{minutes} min "
            f"{seconds} s"
        )

    if minutes:
        return (
            f"{minutes} min "
            f"{seconds} s"
        )

    return f"{seconds} s"


# ============================================================
# 5. GMAIL AUTH
# ============================================================

def get_gmail_service():
    """
    Přihlášení ke Gmail API pomocí OAuth.
    """

    creds = None

    if os.path.exists("token.json"):

        creds = (
            Credentials
            .from_authorized_user_file(
                "token.json",
                SCOPES,
            )
        )

    if not creds or not creds.valid:

        # Existující token expiroval,
        # ale lze jej obnovit.
        #
        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            creds.refresh(
                Request()
            )

        # Jinak proběhne nové přihlášení.
        #
        else:

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    "credentials.json",
                    SCOPES,
                )
            )

            creds = (
                flow.run_local_server(
                    port=0
                )
            )

        # Uloží nový OAuth token.
        #
        with open(
            "token.json",
            "w",
            encoding="utf-8",
        ) as token_file:

            token_file.write(
                creds.to_json()
            )

    return build(
        "gmail",
        "v1",
        credentials=creds,
    )


# ============================================================
# 6. GMAIL LABEL AI_PROCESSED
# ============================================================

def get_or_create_label(
    service,
    label_name: str,
):
    """
    Najde Gmail label.
    Pokud neexistuje, vytvoří ho.
    """

    result = (
        service.users()
        .labels()
        .list(
            userId="me"
        )
        .execute()
    )

    for label in result.get(
        "labels",
        [],
    ):

        if label.get("name") == label_name:

            return label["id"]

    logger.info(
        "Vytvářím Gmail label: %s",
        label_name,
    )

    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )

    return created["id"]


# ============================================================
# 7. DEKÓDOVÁNÍ TĚLA E-MAILU
# ============================================================

def decode_body(data: str) -> str:
    """
    Gmail posílá tělo e-mailu v base64url formátu.
    """

    if not data:
        return ""

    try:

        decoded = (
            base64
            .urlsafe_b64decode(
                data.encode("utf-8")
            )
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    except Exception:

        return ""


# ============================================================
# 8. HTML -> ČISTÝ TEXT
# ============================================================

def html_to_text(html: str) -> str:
    """
    Odstraní HTML, CSS a další nepotřebné části.
    """

    if not html:
        return ""

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    for tag in soup([
        "script",
        "style",
        "head",
        "meta",
        "noscript",
    ]):

        tag.decompose()

    text = soup.get_text(
        separator="\n"
    )

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line,
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


# ============================================================
# 9. EXTRAKCE TĚLA E-MAILU
# ============================================================

def extract_email_body(payload) -> str:
    """
    Preferuje text/plain.

    Pokud není dostupný,
    převede HTML na čistý text.
    """

    mime_type = payload.get(
        "mimeType",
        "",
    )

    body_data = (
        payload
        .get("body", {})
        .get("data")
    )

    # Přímý text/plain
    #
    if (
        mime_type == "text/plain"
        and body_data
    ):

        return decode_body(
            body_data
        )

    # Přímý text/html
    #
    if (
        mime_type == "text/html"
        and body_data
    ):

        return html_to_text(
            decode_body(
                body_data
            )
        )

    parts = payload.get(
        "parts",
        [],
    )

    plain_parts = []
    html_parts = []

    for part in parts:

        part_mime = part.get(
            "mimeType",
            "",
        )

        part_data = (
            part
            .get("body", {})
            .get("data")
        )

        if (
            part_mime == "text/plain"
            and part_data
        ):

            plain_parts.append(
                decode_body(
                    part_data
                )
            )

        elif (
            part_mime == "text/html"
            and part_data
        ):

            html_parts.append(
                decode_body(
                    part_data
                )
            )

        # E-mail může obsahovat další vnořený multipart.
        #
        if part.get("parts"):

            nested = extract_email_body(
                part
            )

            if nested:

                plain_parts.append(
                    nested
                )

    if plain_parts:

        return "\n".join(
            plain_parts
        )

    if html_parts:

        return html_to_text(
            "\n".join(
                html_parts
            )
        )

    return ""


# ============================================================
# 10. KONTEXT EMAILOVÉHO VLÁKNA
# ============================================================

def get_thread_context(
    service,
    thread_id: str,
    current_message_id: str,
):
    """
    Vrátí maximálně 3 zprávy,
    které v threadu předcházely aktuálnímu mailu.

    Budoucí zprávy z threadu se nepoužívají.
    """

    thread = (
        service.users()
        .threads()
        .get(
            userId="me",
            id=thread_id,
            format="full",
        )
        .execute()
    )

    context_parts = []

    for message in thread.get(
        "messages",
        [],
    ):

        # Jakmile narazíme na aktuální mail,
        # skončíme.
        #
        if (
            message["id"]
            == current_message_id
        ):

            break

        headers = {
            h["name"].lower():
            h["value"]

            for h
            in message[
                "payload"
            ][
                "headers"
            ]
        }

        body = extract_email_body(
            message["payload"]
        )

        # Chráníme context window LLM.
        #
        if len(body) > 2500:

            body = body[:2500]

        context_parts.append(
            f"""
FROM:
{headers.get('from', '')}

SUBJECT:
{headers.get('subject', '')}

BODY:
{body}
"""
        )

    if not context_parts:

        return ""

    # Použijeme pouze poslední 3 zprávy.
    #
    return (
        "\n--- PREVIOUS MESSAGE ---\n"
        .join(
            context_parts[-3:]
        )
    )


# ============================================================
# 11. DETERMINISTICKÁ PRAVIDLA
# ============================================================

def deterministic_rule(email):
    """
    Některé typy zpráv dokážeme vyhodnotit
    spolehlivěji a rychleji bez LLM.

    Funkce vrací:
        dict -> pokud pravidlo rozhodlo

        None -> e-mail musí vyhodnotit LLM
    """

    sender = (
        email["from"]
        .lower()
    )

    subject = (
        email["subject"]
        .lower()
    )

    body = (
        email["body"]
        .lower()
    )

    list_unsubscribe = (
        email
        .get(
            "list_unsubscribe",
            "",
        )
        .lower()
    )

    list_id = (
        email
        .get(
            "list_id",
            "",
        )
        .lower()
    )


    # --------------------------------------------------------
    # 11.1 NEDORUČENÝ EMAIL
    # --------------------------------------------------------

    if (
        "postmaster@" in sender
        or "mailer-daemon@" in sender
        or "nedoručiteln" in subject
        or "delivery status notification" in subject
        or "delivery failed" in subject
    ):

        return {
            "category": "IMPORTANT",

            "reason": (
                "Systémová zpráva o nedoručení "
                "nebo problému s doručením."
            ),
        }


    # --------------------------------------------------------
    # 11.2 LINKEDIN AUTOMATICKÉ NOTIFIKACE
    # --------------------------------------------------------

    if (
        "messages-noreply@linkedin.com"
        in sender

        or

        "notifications-noreply@linkedin.com"
        in sender
    ):

        return {
            "category": "ADVERTISEMENT",

            "reason": (
                "Automatická LinkedIn notifikace "
                "nebo obsahová propagace."
            ),
        }


    # --------------------------------------------------------
    # 11.3 MARKETING
    # --------------------------------------------------------

    marketing_signals = [
        "unsubscribe",
        "odhlásit odběr",
        "odhlásit se",
        "newsletter",
        "sleva",
        "slevový kód",
        "promo",
        "special offer",
        "akční nabídka",
        "výprodej",
        "nabídka služeb",
        "nabídka produktů",
        "půjčka",
        "úvěr",
        "spoření",
        "pojištění",
        "investice",
        "výhody",
        "odměna",
        "bonus",
        "cashback",
        "produktová nabídka",
        "výhodná nabídka",
    ]

    signal_count = sum(
        (
            signal in subject
            or signal in body
        )

        for signal
        in marketing_signals
    )


    has_mailing_list_headers = bool(
        list_unsubscribe
        or list_id
    )


    # Mailing-list + alespoň jeden
    # marketingový signál.
    #
    if (
        has_mailing_list_headers
        and signal_count >= 1
    ):

        return {
            "category": "ADVERTISEMENT",

            "reason": (
                "Hromadná obchodní komunikace "
                "s marketingovým obsahem."
            ),
        }


    # Více marketingových znaků
    # i bez speciálních mail headerů.
    #
    if signal_count >= 2:

        return {
            "category": "ADVERTISEMENT",

            "reason": (
                "Zpráva obsahuje více typických "
                "znaků marketingové komunikace."
            ),
        }


    # Pravidlo nerozhodlo.
    #
    return None


# ============================================================
# 12. GMAIL QUERY PODLE REŽIMU
# ============================================================

def build_query():
    """
    Vrací Gmail search query podle MODE.
    """

    if MODE == "cleanup":

        # Historická přijatá pošta.
        #
        # Nechceme:
        # - odeslané
        # - koncepty
        # - spam
        # - koš
        # - již zpracované
        #
        return (
            f'-label:"{PROCESSED_LABEL_NAME}" '
            '-in:sent '
            '-in:drafts '
            '-in:spam '
            '-in:trash'
        )

    if MODE == "live":

        # Pouze nové maily v Inboxu.
        #
        return (
            f'in:inbox '
            f'-label:"{PROCESSED_LABEL_NAME}"'
        )

    raise ValueError(
        f"Neznámý MODE: {MODE}"
    )


# ============================================================
# 13. NAČTENÍ JEDNÉ DÁVKY
# ============================================================

def get_email_batch(
    service,
    limit,
):
    """
    Načte jednu dávku nezpracovaných mailů.
    """

    query = build_query()

    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=query,
            maxResults=limit,
        )
        .execute()
    )

    emails = []

    for item in result.get(
        "messages",
        [],
    ):

        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="full",
            )
            .execute()
        )


        # ----------------------------------------------------
        # Bezpečnostní ochrana podle Gmail labelIds
        # ----------------------------------------------------

        label_ids = set(
            message.get(
                "labelIds",
                [],
            )
        )

        forbidden_labels = {
            "SENT",
            "DRAFT",
            "SPAM",
            "TRASH",
        }

        if (
            label_ids
            & forbidden_labels
        ):

            continue


        headers = {
            h["name"].lower():
            h["value"]

            for h
            in message[
                "payload"
            ][
                "headers"
            ]
        }


        body = extract_email_body(
            message["payload"]
        )


        thread_context = (
            get_thread_context(
                service=service,

                thread_id=
                    message[
                        "threadId"
                    ],

                current_message_id=
                    message[
                        "id"
                    ],
            )
        )


        emails.append(
            {
                "id":
                    message["id"],

                "thread_id":
                    message["threadId"],

                "from":
                    headers.get(
                        "from",
                        "",
                    ),

                "subject":
                    headers.get(
                        "subject",
                        "",
                    ),

                "date":
                    headers.get(
                        "date",
                        "",
                    ),

                "body":
                    body,

                "thread_context":
                    thread_context,

                "list_unsubscribe":
                    headers.get(
                        "list-unsubscribe",
                        "",
                    ),

                "list_id":
                    headers.get(
                        "list-id",
                        "",
                    ),
            }
        )

    return emails


# ============================================================
# 14. STRUKTUROVANÝ VÝSTUP LLM
# ============================================================

class EmailClassification(
    BaseModel
):

    category: Literal[
        "IMPORTANT",
        "NORMAL",
        "ADVERTISEMENT",
        "UNCERTAIN",
    ]

    reason: str


# ============================================================
# 15. INTERNÍ LLM
# ============================================================

# Nepoužíváme OpenAI cloud tracing.
#
set_tracing_disabled(
    disabled=True
)


# Async OpenAI client pouze používá
# OpenAI-compatible endpoint Ollamy.
#
client = AsyncOpenAI(
    base_url=OLLAMA_URL,
    api_key="ollama",
)


model = OpenAIChatCompletionsModel(
    model=OLLAMA_MODEL,
    openai_client=client,
)


# ============================================================
# 16. OPENAI AGENTS SDK AGENT
# ============================================================

agent = Agent(

    name="Gmail Classification Agent",

    instructions="""
Jsi AI agent pro třídění e-mailové schránky.

Každý e-mail klasifikuj do právě jedné kategorie:

IMPORTANT
NORMAL
ADVERTISEMENT
UNCERTAIN


IMPORTANT:

- přímá otázka
- žádost o odpověď
- žádost o schválení
- rozhodnutí
- úkol
- požadavek na akci
- deadline nebo termín
- problém nebo chyba
- změna nebo zrušení schůzky
- bezpečnostní upozornění
- nedoručení
- zpráva vyžadující pozornost


ADVERTISEMENT:

- reklama
- newsletter
- promo akce
- marketing
- sleva
- obchodní nabídka
- propagace produktu nebo služby
- automatická obsahová propagace


NORMAL:

- běžná informační zpráva
- potvrzení bez další akce
- informace bez požadavku na rozhodnutí


UNCERTAIN:

- chybí dostatek kontextu
- obsah není jednoznačný
- nejsi si jistý


PRAVIDLA:

1.
Použij také předchozí kontext vlákna.

2.
Krátká odpověď typu "Souhlasím"
může být IMPORTANT,
pokud předchozí zpráva žádala o rozhodnutí.

3.
Samotné "Re:" neznamená,
že zpráva není důležitá.

4.
Pokud si nejsi jistý mezi
IMPORTANT a NORMAL,
použij UNCERTAIN.

5.
Nevymýšlej informace.

6.
Evidentní reklama nebo newsletter
patří do ADVERTISEMENT.

7.
Marketingový newsletter banky není IMPORTANT
jen proto, že obsahuje slova jako půjčka,
úvěr, pojištění, odměna nebo výhody.

8.
Bezpečnostní upozornění banky,
změna schůzky, blokace účtu
nebo problém s platbou
může být IMPORTANT.

9.
Důvod napiš jednou krátkou větou.
""",

    model=model,

    output_type=EmailClassification,
)


# ============================================================
# 17. KLASIFIKACE EMAILU
# ============================================================

async def classify_email(email):
    """
    Nejprve použije deterministická pravidla.

    Pokud pravidla nerozhodnou,
    použije OpenAI Agents SDK + interní LLM.
    """

    rule = deterministic_rule(
        email
    )


    # --------------------------------------------------------
    # Rozhodlo pevné pravidlo
    # --------------------------------------------------------

    if rule:

        stats["rules"] += 1

        return (
            EmailClassification(
                category=
                    rule["category"],

                reason=
                    rule["reason"],
            )
        )


    # --------------------------------------------------------
    # Musí rozhodnout LLM
    # --------------------------------------------------------

    stats["llm"] += 1


    body = email[
        "body"
    ]


    thread_context = (
        email[
            "thread_context"
        ]
    )


    # Chráníme context window.
    #
    if len(body) > 8000:

        body = body[:8000]


    if len(
        thread_context
    ) > 6000:

        thread_context = (
            thread_context[-6000:]
        )


    prompt = f"""
AKTUÁLNÍ E-MAIL

ODESÍLATEL:
{email['from']}

PŘEDMĚT:
{email['subject']}

DATUM:
{email['date']}

OBSAH:
{body}


PŘEDCHOZÍ KONTEXT VLÁKNA:
{thread_context}
"""


    result = await Runner.run(
        agent,
        input=prompt,
    )


    return result.final_output


# ============================================================
# 18. GMAIL AKCE
# ============================================================

def mark_as_important(
    service,
    message_id,
):
    """
    Přidá Gmail systémový label IMPORTANT.
    """

    service.users().messages().modify(
        userId="me",
        id=message_id,

        body={
            "addLabelIds": [
                "IMPORTANT"
            ]
        },

    ).execute()


def archive_email(
    service,
    message_id,
):
    """
    Archivace = odstranění label INBOX.

    E-mail se NESMAŽE.
    """

    service.users().messages().modify(
        userId="me",
        id=message_id,

        body={
            "removeLabelIds": [
                "INBOX"
            ]
        },

    ).execute()


def mark_as_processed(
    service,
    message_id,
    processed_label_id,
):
    """
    Přidá vlastní Gmail label AI_PROCESSED.
    """

    service.users().messages().modify(
        userId="me",
        id=message_id,

        body={
            "addLabelIds": [
                processed_label_id
            ]
        },

    ).execute()


# ============================================================
# 19. PROVEDENÍ AKCE
# ============================================================

def perform_action(
    service,
    email,
    classification,
    processed_label_id,
):
    """
    Podle výsledku klasifikace
    provede odpovídající Gmail akci.
    """

    category = (
        classification.category
    )


    # Započítání statistiky kategorií
    #
    stats[category] += 1


    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------

    if category == "IMPORTANT":

        if DRY_RUN:

            logger.info(
                "AKCE: [DRY RUN] "
                "Označil bych jako IMPORTANT "
                "+ AI_PROCESSED."
            )

        else:

            mark_as_important(
                service,
                email["id"],
            )

            mark_as_processed(
                service,
                email["id"],
                processed_label_id,
            )

            logger.info(
                "AKCE: Označeno jako IMPORTANT "
                "+ AI_PROCESSED."
            )


    # --------------------------------------------------------
    # ADVERTISEMENT
    # --------------------------------------------------------

    elif category == "ADVERTISEMENT":

        if DRY_RUN:

            logger.info(
                "AKCE: [DRY RUN] "
                "Archivoval bych "
                "+ AI_PROCESSED."
            )

        else:

            archive_email(
                service,
                email["id"],
            )

            mark_as_processed(
                service,
                email["id"],
                processed_label_id,
            )

            logger.info(
                "AKCE: Archivováno "
                "+ AI_PROCESSED."
            )


    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    elif category == "NORMAL":

        if DRY_RUN:

            logger.info(
                "AKCE: [DRY RUN] "
                "Ponechal bych e-mail beze změny "
                "+ AI_PROCESSED."
            )

        else:

            mark_as_processed(
                service,
                email["id"],
                processed_label_id,
            )

            logger.info(
                "AKCE: Beze změny "
                "+ AI_PROCESSED."
            )


    # --------------------------------------------------------
    # UNCERTAIN
    # --------------------------------------------------------

    elif category == "UNCERTAIN":

        if DRY_RUN:

            logger.info(
                "AKCE: [DRY RUN] "
                "Ponechal bych e-mail beze změny "
                "+ AI_PROCESSED."
            )

        else:

            mark_as_processed(
                service,
                email["id"],
                processed_label_id,
            )

            logger.info(
                "AKCE: Nejistá klasifikace, "
                "e-mail ponechán beze změny "
                "+ AI_PROCESSED."
            )


# ============================================================
# 20. ZPRACOVÁNÍ JEDNÉ DÁVKY
# ============================================================

async def process_batch(
    service,
    processed_label_id,
    batch_number,
):
    """
    Zpracuje jednu dávku e-mailů.

    Vrací počet zpracovaných mailů.
    """

    batch_start = (
        time.perf_counter()
    )


    emails = get_email_batch(
        service=service,
        limit=BATCH_SIZE,
    )


    if not emails:

        return 0


    logger.info(
        "DÁVKA %d | nalezeno %d e-mailů",
        batch_number,
        len(emails),
    )


    for index, email in enumerate(
        emails,
        start=1,
    ):

        email_start = (
            time.perf_counter()
        )


        logger.info(
            "=" * 70
        )


        logger.info(
            "[%d/%d] OD: %s",
            index,
            len(emails),
            email["from"],
        )


        logger.info(
            "PŘEDMĚT: %s",
            email["subject"],
        )


        logger.info(
            "DATUM: %s",
            email["date"],
        )


        try:

            classification = (
                await classify_email(
                    email
                )
            )


            logger.info(
                "CATEGORY: %s",
                classification.category,
            )


            logger.info(
                "REASON: %s",
                classification.reason,
            )


            perform_action(
                service=service,

                email=email,

                classification=
                    classification,

                processed_label_id=
                    processed_label_id,
            )


            stats["processed"] += 1


            email_elapsed = (
                time.perf_counter()
                - email_start
            )


            logger.info(
                "ČAS EMAILU: %.2f s",
                email_elapsed,
            )


        except Exception:

            stats["errors"] += 1


            logger.exception(
                "CHYBA při zpracování e-mailu."
            )


            logger.info(
                "AKCE: E-mail nebyl označen "
                "jako AI_PROCESSED."
            )


    batch_elapsed = (
        time.perf_counter()
        - batch_start
    )


    logger.info(
        "-" * 70
    )


    logger.info(
        "DÁVKA %d DOKONČENA",
        batch_number,
    )


    logger.info(
        "POČET EMAILŮ V DÁVCE: %d",
        len(emails),
    )


    logger.info(
        "DOBA DÁVKY: %s",
        format_duration(
            batch_elapsed
        ),
    )


    if emails:

        logger.info(
            "PRŮMĚR DÁVKY / EMAIL: %.2f s",
            (
                batch_elapsed
                / len(emails)
            ),
        )


    logger.info(
        "-" * 70
    )


    return len(emails)


# ============================================================
# 21. FINÁLNÍ SOUHRN
# ============================================================

def print_summary(
    elapsed_time,
):
    """
    Vypíše finální statistiku
    do terminálu i logu.
    """

    logger.info(
        "=" * 70
    )

    logger.info(
        "SOUHRN BĚHU"
    )

    logger.info(
        "=" * 70
    )


    logger.info(
        "MODE: %s",
        MODE,
    )


    logger.info(
        "DRY_RUN: %s",
        DRY_RUN,
    )


    logger.info(
        "CELKEM ZPRACOVÁNO: %d",
        stats["processed"],
    )


    logger.info(
        "IMPORTANT: %d",
        stats["IMPORTANT"],
    )


    logger.info(
        "NORMAL: %d",
        stats["NORMAL"],
    )


    logger.info(
        "ADVERTISEMENT: %d",
        stats["ADVERTISEMENT"],
    )


    logger.info(
        "UNCERTAIN: %d",
        stats["UNCERTAIN"],
    )


    logger.info(
        "CHYBY: %d",
        stats["errors"],
    )


    logger.info(
        "KLASIFIKACE PRAVIDLY: %d",
        stats["rules"],
    )


    logger.info(
        "KLASIFIKACE LLM: %d",
        stats["llm"],
    )


    logger.info(
        "CELKOVÁ DOBA: %s",
        format_duration(
            elapsed_time
        ),
    )


    if stats["processed"] > 0:

        logger.info(
            "PRŮMĚRNÝ ČAS / EMAIL: %.2f s",
            (
                elapsed_time
                / stats["processed"]
            ),
        )


    logger.info(
        "LOG FILE: %s",
        LOG_FILE,
    )


    logger.info(
        "=" * 70
    )


# ============================================================
# 22. MAIN
# ============================================================

async def main():
    """
    Hlavní běh programu.
    """

    start_time = (
        time.perf_counter()
    )


    logger.info(
        "=" * 70
    )


    logger.info(
        "GMAIL AI AGENT START"
    )


    logger.info(
        "MODE: %s",
        MODE,
    )


    logger.info(
        "DRY_RUN: %s",
        DRY_RUN,
    )


    logger.info(
        "BATCH_SIZE: %s",
        BATCH_SIZE,
    )


    logger.info(
        "LLM: %s",
        OLLAMA_MODEL,
    )


    logger.info(
        "LLM SERVER: %s",
        OLLAMA_URL,
    )


    logger.info(
        "LOG FILE: %s",
        LOG_FILE,
    )


    logger.info(
        "=" * 70
    )


    # Gmail API
    #
    service = (
        get_gmail_service()
    )


    # Gmail AI_PROCESSED label
    #
    processed_label_id = (
        get_or_create_label(
            service,
            PROCESSED_LABEL_NAME,
        )
    )


    batch_number = 0


    try:

        while True:

            batch_number += 1


            logger.info(
                "START DÁVKY %d",
                batch_number,
            )


            count = (
                await process_batch(
                    service=
                        service,

                    processed_label_id=
                        processed_label_id,

                    batch_number=
                        batch_number,
                )
            )


            # Nic dalšího nezbylo.
            #
            if count == 0:

                logger.info(
                    "Žádné další "
                    "nezpracované e-maily."
                )

                break


            # ------------------------------------------------
            # DRY RUN
            # ------------------------------------------------
            #
            # V dry-run režimu se nepřidává AI_PROCESSED.
            # Druhá dávka by tedy obsahovala stejné maily.
            #
            if DRY_RUN:

                logger.info(
                    "DRY RUN dokončen."
                )

                logger.info(
                    "Další dávka se nespouští, "
                    "protože e-maily nebyly "
                    "označeny AI_PROCESSED."
                )

                break


            # ------------------------------------------------
            # LIVE MODE
            # ------------------------------------------------
            #
            # Jeden běh = jedna aktuální várka nových mailů.
            #
            if MODE == "live":

                logger.info(
                    "LIVE dávka dokončena."
                )

                break


    finally:

        elapsed_time = (
            time.perf_counter()
            - start_time
        )


        print_summary(
            elapsed_time
        )


# ============================================================
# 23. START PROGRAMU
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )


    except KeyboardInterrupt:

        logger.warning(
            "Program byl ukončen uživatelem "
            "pomocí Ctrl+C."
        )


        logger.warning(
            "Již úspěšně zpracované e-maily "
            "zůstávají označené AI_PROCESSED."
        )


        logger.warning(
            "Při příštím spuštění agent "
            "automaticky pokračuje."
        )