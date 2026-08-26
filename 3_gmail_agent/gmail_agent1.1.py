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
    function_tool,
    set_tracing_disabled,
)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# ============================================================
# 1. HLAVNÍ NASTAVENÍ
# ============================================================

# Dostupné režimy:
#
# cleanup
#   - historická pošta
#   - postupně zpracovává vše bez AI_PROCESSED
#
# live
#   - zpracuje nové nezpracované zprávy v Inboxu
#
# chat
#   - interaktivní rozhovor nad Gmail schránkou
#
MODE = "cleanup"


# Používá se pro cleanup/live.
#
# True  = pouze simulace změn Gmailu
# False = skutečné změny
#
DRY_RUN = False


# Velikost dávky pro cleanup/live
BATCH_SIZE = 100


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


# ============================================================
# 2. INTERNÍ LLM
# ============================================================

OLLAMA_URL = "http://10.165.200.27:11434/v1"
OLLAMA_MODEL = "llama3.1:8b"


# ============================================================
# 3. AI ŠTÍTKY
# ============================================================

PROCESSED_LABEL_NAME = "AI_PROCESSED"

CATEGORY_LABEL_NAMES = {
    "IMPORTANT": "AI_IMPORTANT",
    "NORMAL": "AI_NORMAL",
    "ADVERTISEMENT": "AI_ADVERTISEMENT",
    "UNCERTAIN": "AI_UNCERTAIN",
}


# ============================================================
# 4. LOGOVÁNÍ
# ============================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / (
    f"gmail_agent_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"
)

logger = logging.getLogger("gmail_agent")
logger.setLevel(logging.INFO)
logger.handlers.clear()

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler(
    LOG_FILE,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


# ============================================================
# 5. STATISTIKY
# ============================================================

stats = {
    "processed": 0,

    "IMPORTANT": 0,
    "NORMAL": 0,
    "ADVERTISEMENT": 0,
    "UNCERTAIN": 0,

    "rules": 0,
    "llm": 0,

    "tool_calls": 0,
    "tool_retries": 0,
    "tool_blocked": 0,
    "fallback_actions": 0,

    "errors": 0,
}


# ============================================================
# 6. RUNTIME CONTEXT
# ============================================================

runtime = {
    "service": None,

    "processed_label_id": None,
    "category_label_ids": {},

    "current_message_id": None,
    "current_category": None,

    "tool_called": False,
    "tool_success": False,
    "tool_name": None,
}


# ============================================================
# 7. POMOCNÉ FUNKCE
# ============================================================

def format_duration(seconds: float) -> str:

    seconds = int(seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours} h {minutes} min {seconds} s"

    if minutes:
        return f"{minutes} min {seconds} s"

    return f"{seconds} s"


def shorten(text: str, max_length: int = 500) -> str:

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."


# ============================================================
# 8. GMAIL AUTH
# ============================================================

def get_gmail_service():

    creds = None

    if os.path.exists("token.json"):

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES,
        )

    if not creds or not creds.valid:

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            creds.refresh(Request())

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0
            )

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
# 9. GMAIL LABEL MANAGEMENT
# ============================================================

def get_or_create_label(
    service,
    label_name: str,
):

    result = (
        service.users()
        .labels()
        .list(userId="me")
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


def initialize_ai_labels(service):

    logger.info(
        "Kontroluji AI Gmail štítky..."
    )

    processed_label_id = (
        get_or_create_label(
            service,
            PROCESSED_LABEL_NAME,
        )
    )

    category_label_ids = {}

    for category, label_name in (
        CATEGORY_LABEL_NAMES.items()
    ):

        category_label_ids[category] = (
            get_or_create_label(
                service,
                label_name,
            )
        )

    return (
        processed_label_id,
        category_label_ids,
    )


# ============================================================
# 10. EMAIL BODY
# ============================================================

def decode_body(data: str) -> str:

    if not data:
        return ""

    try:

        decoded = (
            base64.urlsafe_b64decode(
                data.encode("utf-8")
            )
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    except Exception:
        return ""


def html_to_text(html: str) -> str:

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


def extract_email_body(payload) -> str:

    mime_type = payload.get(
        "mimeType",
        "",
    )

    body_data = (
        payload
        .get("body", {})
        .get("data")
    )

    if (
        mime_type == "text/plain"
        and body_data
    ):

        return decode_body(body_data)

    if (
        mime_type == "text/html"
        and body_data
    ):

        return html_to_text(
            decode_body(body_data)
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
# 11. THREAD CONTEXT
# ============================================================

def get_thread_context(
    service,
    thread_id: str,
    current_message_id: str,
):

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

    return (
        "\n--- PREVIOUS MESSAGE ---\n"
        .join(
            context_parts[-3:]
        )
    )


# ============================================================
# 12. DETERMINISTICKÁ PRAVIDLA
# ============================================================

def deterministic_rule(email):
    """
    Pevná pravidla před LLM.

    DŮLEŽITÉ:
    obecný výskyt slova 'postmaster'
    už automaticky neznamená nedoručení.
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
    # 12.1 COOLKIT / EWELINK DEVICE STATUS
    #
    # Oprava systematické chyby z ostrého auditu.
    # --------------------------------------------------------

    if (
        (
            "coolkit.cc" in sender
            or "coolkit.cn" in sender
            or "ewelink.cc" in sender
        )
        and (
            "scene" in subject
            or "radiatory" in subject
            or "radiator" in subject
            or "is trigged" in subject
            or "is triggered" in subject
        )
    ):

        return {
            "category": "NORMAL",

            "reason": (
                "Automatická provozní notifikace "
                "chytré domácnosti bez požadavku na akci."
            ),
        }


    # --------------------------------------------------------
    # 12.2 DATOVÁ SCHRÁNKA
    # --------------------------------------------------------

    if (
        "mojedatovaschranka.cz"
        in sender
        and (
            "nová zpráva" in subject
            or "nova zprava" in subject
        )
    ):

        return {
            "category": "IMPORTANT",

            "reason": (
                "Oznámení o nové zprávě "
                "v datové schránce vyžaduje pozornost."
            ),
        }


    # --------------------------------------------------------
    # 12.3 SKUTEČNÉ NEDORUČENÍ
    # --------------------------------------------------------

    delivery_failure_signals = [
        "nedoručiteln",
        "delivery status notification",
        "delivery failed",
        "undelivered mail",
        "mail delivery failed",
        "failure notice",
        "returned mail",
        "could not be delivered",
        "message not delivered",
    ]

    has_delivery_failure = any(
        signal in subject
        or signal in body

        for signal
        in delivery_failure_signals
    )

    if has_delivery_failure:

        return {
            "category": "IMPORTANT",

            "reason": (
                "Systémová zpráva o nedoručení "
                "nebo problému s doručením."
            ),
        }


    # --------------------------------------------------------
    # 12.4 SECURITY
    # --------------------------------------------------------

    security_signals = [
        "verification code",
        "ověřovací kód",
        "security alert",
        "bezpečnostní upozornění",
        "new sign-in",
        "nové přihlášení",
        "new login",
        "suspicious activity",
        "podezřelá aktivita",
    ]

    if any(
        signal in subject
        or signal in body

        for signal
        in security_signals
    ):

        return {
            "category": "IMPORTANT",

            "reason": (
                "Bezpečnostní nebo přihlašovací "
                "upozornění účtu."
            ),
        }


    # --------------------------------------------------------
    # 12.5 BĚŽNÉ FAKTURY / STVRZENKY
    # --------------------------------------------------------

    receipt_signals = [
        "faktura",
        "invoice",
        "stvrzenka",
        "receipt",
        "potvrzení platby",
        "potvrzeni platby",
        "payment receipt",
    ]

    problem_signals = [
        "nezaplac",
        "po splatnosti",
        "overdue",
        "failed",
        "zamítnut",
        "declined",
        "problém",
        "problem",
        "nutná akce",
        "action required",
    ]

    is_receipt = any(
        signal in subject

        for signal
        in receipt_signals
    )

    has_problem = any(
        signal in subject
        or signal in body

        for signal
        in problem_signals
    )

    if (
        is_receipt
        and not has_problem
    ):

        return {
            "category": "NORMAL",

            "reason": (
                "Běžná faktura nebo potvrzení platby "
                "bez požadavku na další akci."
            ),
        }


    # --------------------------------------------------------
    # 12.6 LINKEDIN
    # --------------------------------------------------------

    linkedin_senders = [
        "messages-noreply@linkedin.com",
        "notifications-noreply@linkedin.com",
        "updates-noreply@linkedin.com",
        "newsletters-noreply@linkedin.com",
    ]

    if any(
        item in sender
        for item in linkedin_senders
    ):

        return {
            "category": "ADVERTISEMENT",

            "reason": (
                "Automatická LinkedIn notifikace "
                "nebo obsahová propagace."
            ),
        }


    # --------------------------------------------------------
    # 12.7 MARKETING
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
        "cashback",
        "bonus",
        "výhodná nabídka",
        "produktová nabídka",
    ]

    signal_count = sum(
        signal in subject
        or signal in body

        for signal
        in marketing_signals
    )

    has_mailing_list_headers = bool(
        list_unsubscribe
        or list_id
    )

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

    if signal_count >= 2:

        return {
            "category": "ADVERTISEMENT",

            "reason": (
                "Zpráva obsahuje více typických "
                "znaků marketingové komunikace."
            ),
        }

    return None


# ============================================================
# 13. CLEANUP / LIVE QUERY
# ============================================================

def build_query():

    if MODE == "cleanup":

        return (
            f'-label:"{PROCESSED_LABEL_NAME}" '
            '-in:sent '
            '-in:drafts '
            '-in:spam '
            '-in:trash'
        )

    if MODE == "live":

        return (
            f'in:inbox '
            f'-label:"{PROCESSED_LABEL_NAME}"'
        )

    raise ValueError(
        f"build_query() není určeno pro MODE={MODE}"
    )


# ============================================================
# 14. NAČTENÍ DÁVKY
# ============================================================

def get_email_batch(
    service,
    limit,
):

    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=build_query(),
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

        label_ids = set(
            message.get(
                "labelIds",
                [],
            )
        )

        if label_ids & {
            "SENT",
            "DRAFT",
            "SPAM",
            "TRASH",
        }:
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
                    get_thread_context(
                        service,
                        message["threadId"],
                        message["id"],
                    ),

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
# 15. STRUKTUROVANÁ KLASIFIKACE
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
# 16. LLM CLIENT
# ============================================================

set_tracing_disabled(
    disabled=True
)

client = AsyncOpenAI(
    base_url=OLLAMA_URL,
    api_key="ollama",
)

model = OpenAIChatCompletionsModel(
    model=OLLAMA_MODEL,
    openai_client=client,
)


# ============================================================
# 17. KLASIFIKAČNÍ AGENT
# ============================================================

classification_agent = Agent(

    name="Gmail Classification Agent",

    instructions="""
Jsi AI agent pro třídění Gmail zpráv.

Kategorie:

IMPORTANT
NORMAL
ADVERTISEMENT
UNCERTAIN


IMPORTANT:

- přímý dotaz
- úkol
- žádost o odpověď
- schválení
- rozhodnutí
- deadline
- problém
- chyba
- zrušení nebo změna schůzky
- datová schránka
- bezpečnostní upozornění
- nedoručení e-mailu


ADVERTISEMENT:

- reklama
- newsletter
- sleva
- promo
- marketing
- obchodní nabídka


NORMAL:

- běžná informace
- potvrzení bez nutné reakce
- běžná faktura
- běžná stvrzenka
- úspěšná platba
- běžné systémové oznámení
- provozní automatická notifikace


UNCERTAIN:

Použij pouze tehdy,
pokud skutečně nelze rozhodnout.


DŮLEŽITÁ PRAVIDLA:

Automatické oznámení samo o sobě
NEZNAMENÁ IMPORTANT.

Slovo postmaster samo o sobě
NEZNAMENÁ nedoručení.

Zpráva o zapnutí/vypnutí zařízení
není automaticky bezpečnostní upozornění.

Nevymýšlej problém,
který v e-mailu není uveden.

Pokud e-mail pouze informuje
a nic po uživateli nechce,
preferuj NORMAL.

Důvod napiš krátce.
""",

    model=model,
    output_type=EmailClassification,
)


async def classify_email(email):

    rule = deterministic_rule(
        email
    )

    if rule:

        stats["rules"] += 1

        return EmailClassification(
            category=rule["category"],
            reason=rule["reason"],
        )

    stats["llm"] += 1

    body = email["body"][:8000]

    context = (
        email["thread_context"][-6000:]
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


PŘEDCHOZÍ KONTEXT:
{context}
"""

    result = await Runner.run(
        classification_agent,
        input=prompt,
    )

    return result.final_output


# ============================================================
# 18. GMAIL MODIFY
# ============================================================

def gmail_modify_message(
    message_id,
    add_labels=None,
    remove_labels=None,
):

    body = {}

    if add_labels:

        body["addLabelIds"] = list(
            dict.fromkeys(
                add_labels
            )
        )

    if remove_labels:

        body["removeLabelIds"] = list(
            dict.fromkeys(
                remove_labels
            )
        )

    runtime[
        "service"
    ].users().messages().modify(
        userId="me",
        id=message_id,
        body=body,
    ).execute()


def get_ai_labels_for_category(
    category,
):

    return [
        runtime[
            "processed_label_id"
        ],

        runtime[
            "category_label_ids"
        ][category],
    ]


# ============================================================
# 19. TOOL SECURITY
# ============================================================

def validate_tool_call(
    message_id,
    allowed_categories,
    tool_name,
):

    if (
        message_id
        != runtime[
            "current_message_id"
        ]
    ):

        stats["tool_blocked"] += 1

        logger.error(
            "TOOL BLOCKED: nesprávné message_id"
        )

        return False

    if (
        runtime[
            "current_category"
        ]
        not in allowed_categories
    ):

        stats["tool_blocked"] += 1

        logger.error(
            "TOOL BLOCKED: nesprávná kategorie"
        )

        return False

    return True


# ============================================================
# 20. ACTION TOOLS
# ============================================================

@function_tool
def mark_email_as_important(
    message_id: str,
) -> str:

    runtime["tool_called"] = True
    runtime["tool_success"] = False
    runtime["tool_name"] = (
        "mark_email_as_important"
    )

    stats["tool_calls"] += 1

    if not validate_tool_call(
        message_id,
        {"IMPORTANT"},
        runtime["tool_name"],
    ):
        return "BLOCKED"

    if not DRY_RUN:

        gmail_modify_message(
            message_id,

            add_labels=[
                "IMPORTANT",
                *get_ai_labels_for_category(
                    "IMPORTANT"
                ),
            ],
        )

    runtime["tool_success"] = True

    logger.info(
        "AKCE: %sIMPORTANT + AI_IMPORTANT + AI_PROCESSED.",
        "[DRY RUN] " if DRY_RUN else "",
    )

    return "OK"


@function_tool
def archive_advertisement_email(
    message_id: str,
) -> str:

    runtime["tool_called"] = True
    runtime["tool_success"] = False
    runtime["tool_name"] = (
        "archive_advertisement_email"
    )

    stats["tool_calls"] += 1

    if not validate_tool_call(
        message_id,
        {"ADVERTISEMENT"},
        runtime["tool_name"],
    ):
        return "BLOCKED"

    if not DRY_RUN:

        gmail_modify_message(
            message_id,

            add_labels=(
                get_ai_labels_for_category(
                    "ADVERTISEMENT"
                )
            ),

            remove_labels=[
                "INBOX"
            ],
        )

    runtime["tool_success"] = True

    logger.info(
        "AKCE: %sArchivováno + AI_ADVERTISEMENT + AI_PROCESSED.",
        "[DRY RUN] " if DRY_RUN else "",
    )

    return "OK"


@function_tool
def leave_email_unchanged(
    message_id: str,
) -> str:

    runtime["tool_called"] = True
    runtime["tool_success"] = False
    runtime["tool_name"] = (
        "leave_email_unchanged"
    )

    stats["tool_calls"] += 1

    category = (
        runtime[
            "current_category"
        ]
    )

    if not validate_tool_call(
        message_id,
        {
            "NORMAL",
            "UNCERTAIN",
        },
        runtime["tool_name"],
    ):
        return "BLOCKED"

    if not DRY_RUN:

        gmail_modify_message(
            message_id,

            add_labels=(
                get_ai_labels_for_category(
                    category
                )
            ),
        )

    runtime["tool_success"] = True

    logger.info(
        "AKCE: %sBeze změny + %s + AI_PROCESSED.",
        "[DRY RUN] " if DRY_RUN else "",
        CATEGORY_LABEL_NAMES[
            category
        ],
    )

    return "OK"


# ============================================================
# 21. ACTION AGENT
# ============================================================

action_agent = Agent(

    name="Gmail Action Agent",

    instructions="""
Dostaneš MESSAGE_ID a CATEGORY.

CATEGORY nepřehodnocuj.

IMPORTANT
-> mark_email_as_important

ADVERTISEMENT
-> archive_advertisement_email

NORMAL
-> leave_email_unchanged

UNCERTAIN
-> leave_email_unchanged

Musíš zavolat právě jeden tool.
""",

    model=model,

    tools=[
        mark_email_as_important,
        archive_advertisement_email,
        leave_email_unchanged,
    ],
)


# ============================================================
# 22. FALLBACK
# ============================================================

def execute_fallback_action(
    email,
    classification,
):

    stats[
        "fallback_actions"
    ] += 1

    message_id = email["id"]
    category = classification.category

    logger.warning(
        "Používám FALLBACK pro %s",
        category,
    )

    if DRY_RUN:
        return

    if category == "IMPORTANT":

        gmail_modify_message(
            message_id,

            add_labels=[
                "IMPORTANT",
                *get_ai_labels_for_category(
                    "IMPORTANT"
                ),
            ],
        )

    elif category == "ADVERTISEMENT":

        gmail_modify_message(
            message_id,

            add_labels=(
                get_ai_labels_for_category(
                    "ADVERTISEMENT"
                )
            ),

            remove_labels=[
                "INBOX"
            ],
        )

    else:

        gmail_modify_message(
            message_id,

            add_labels=(
                get_ai_labels_for_category(
                    category
                )
            ),
        )


async def execute_action_with_tools(
    email,
    classification,
):

    category = (
        classification.category
    )

    runtime[
        "current_message_id"
    ] = email["id"]

    runtime[
        "current_category"
    ] = category

    runtime["tool_success"] = False
    runtime["tool_called"] = False
    runtime["tool_name"] = None

    prompt = f"""
MESSAGE_ID:
{email['id']}

CATEGORY:
{category}

Zavolej odpovídající tool.
"""

    await Runner.run(
        action_agent,
        input=prompt,
    )

    if runtime[
        "tool_success"
    ]:
        return

    stats[
        "tool_retries"
    ] += 1

    logger.warning(
        "Tool nebyl zavolán. RETRY."
    )

    runtime["tool_success"] = False
    runtime["tool_called"] = False
    runtime["tool_name"] = None

    await Runner.run(
        action_agent,

        input=(
            prompt
            + "\nMUSÍŠ okamžitě zavolat tool."
        ),
    )

    if runtime[
        "tool_success"
    ]:
        return

    execute_fallback_action(
        email,
        classification,
    )


# ============================================================
# 23. CLEANUP / LIVE PROCESSING
# ============================================================

async def process_batch(
    service,
    batch_number,
):

    batch_start = (
        time.perf_counter()
    )

    emails = get_email_batch(
        service,
        BATCH_SIZE,
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

            await execute_action_with_tools(
                email,
                classification,
            )

            stats[
                classification.category
            ] += 1

            stats["processed"] += 1

            logger.info(
                "ČAS EMAILU: %.2f s",
                (
                    time.perf_counter()
                    - email_start
                ),
            )

        except Exception:

            stats["errors"] += 1

            logger.exception(
                "CHYBA při zpracování e-mailu."
            )

    logger.info(
        "DÁVKA %d DOKONČENA | %s",
        batch_number,
        format_duration(
            time.perf_counter()
            - batch_start
        ),
    )

    return len(emails)


# ============================================================
# 24. GMAIL SEARCH HELPERS PRO CHAT
# ============================================================

def gmail_search_messages(
    query: str,
    limit: int = 20,
):

    service = runtime["service"]

    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            q=query,
            maxResults=min(
                max(limit, 1),
                100,
            ),
        )
        .execute()
    )

    return result.get(
        "messages",
        [],
    )


def gmail_count_messages(
    query: str,
):
    """
    Přesné počítání přes všechny stránky.
    """

    service = runtime["service"]

    total = 0
    page_token = None

    while True:

        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=500,
                pageToken=page_token,
            )
            .execute()
        )

        total += len(
            result.get(
                "messages",
                [],
            )
        )

        page_token = (
            result.get(
                "nextPageToken"
            )
        )

        if not page_token:
            break

    return total


def gmail_get_message_summary(
    message_id: str,
):

    service = runtime["service"]

    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full",
        )
        .execute()
    )

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

    return {
        "id":
            message_id,

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
            shorten(
                body,
                1200,
            ),

        "labels":
            message.get(
                "labelIds",
                [],
            ),
    }


# ============================================================
# 25. CHAT TOOLS
# ============================================================

@function_tool
def count_emails(
    query: str,
) -> str:
    """
    Spočítá e-maily podle Gmail search query.

    Příklad:
    newer_than:30d
    from:seznam.cz
    label:AI_ADVERTISEMENT
    after:2026/07/01 before:2026/08/01
    """

    count = gmail_count_messages(
        query
    )

    return (
        f"Gmail query: {query}\n"
        f"Počet e-mailů: {count}"
    )


@function_tool
def search_emails(
    query: str,
    limit: int = 10,
) -> str:
    """
    Vyhledá zprávy podle Gmail query
    a vrátí přehled nalezených e-mailů.
    """

    messages = gmail_search_messages(
        query,
        limit,
    )

    if not messages:
        return "Nenalezeny žádné e-maily."

    output = []

    for index, item in enumerate(
        messages,
        start=1,
    ):

        email = gmail_get_message_summary(
            item["id"]
        )

        output.append(
            f"""
[{index}]
ID: {email['id']}
OD: {email['from']}
DATUM: {email['date']}
PŘEDMĚT: {email['subject']}
TEXT: {shorten(email['body'], 350)}
"""
        )

    return "\n".join(output)


@function_tool
def get_email_details(
    message_id: str,
) -> str:
    """
    Vrátí podrobnosti konkrétní zprávy
    podle Gmail message ID.
    """

    email = gmail_get_message_summary(
        message_id
    )

    return f"""
ID:
{email['id']}

OD:
{email['from']}

DATUM:
{email['date']}

PŘEDMĚT:
{email['subject']}

ŠTÍTKY:
{email['labels']}

OBSAH:
{email['body']}
"""


@function_tool
def get_ai_statistics() -> str:
    """
    Vrátí počty zpráv podle AI štítků.
    """

    processed = (
        gmail_count_messages(
            'label:"AI_PROCESSED"'
        )
    )

    important = (
        gmail_count_messages(
            'label:"AI_IMPORTANT"'
        )
    )

    normal = (
        gmail_count_messages(
            'label:"AI_NORMAL"'
        )
    )

    advertisement = (
        gmail_count_messages(
            'label:"AI_ADVERTISEMENT"'
        )
    )

    uncertain = (
        gmail_count_messages(
            'label:"AI_UNCERTAIN"'
        )
    )

    return f"""
AI_PROCESSED: {processed}
AI_IMPORTANT: {important}
AI_NORMAL: {normal}
AI_ADVERTISEMENT: {advertisement}
AI_UNCERTAIN: {uncertain}
"""


# ============================================================
# 26. CHAT AGENT
# ============================================================

chat_agent = Agent(

    name="Gmail Chat Assistant",

    instructions="""
Jsi osobní AI asistent nad skutečnou Gmail schránkou.

Máš READ-ONLY nástroje pro:

- počítání e-mailů
- vyhledávání e-mailů
- čtení konkrétního e-mailu
- statistiky AI klasifikace


Nikdy si nevymýšlej počet e-mailů
ani obsah zpráv.

Pokud lze odpověď získat pomocí toolu,
tool skutečně použij.


Gmail search syntax:

from:
to:
subject:
after:
before:
newer_than:
older_than:
label:
in:
is:


Příklady:

"Kolik mailů přišlo za posledních 30 dní?"
-> count_emails("newer_than:30d -in:sent")

"Kolik reklam mám?"
-> get_ai_statistics()
nebo
-> count_emails('label:"AI_ADVERTISEMENT"')

"Najdi zprávy od České spořitelny."
-> search_emails("from:csas.cz", 10)

"Najdi důležité zprávy za poslední týden."
-> search_emails(
     'label:"AI_IMPORTANT" newer_than:7d',
     10
   )

"Kolik e-mailů mi přišlo v červenci 2026?"
-> count_emails(
     "after:2026/07/01 before:2026/08/01 -in:sent"
   )


DŮLEŽITÉ:

Pokud uživatel říká "přišlo mi",
zpravidla vyluč odeslanou poštu pomocí:

-in:sent


Dnešní datum je:

2026-08-26

Odpovídej česky.

Buď stručný,
ale u výsledků vysvětli,
co bylo skutečně nalezeno.
""",

    model=model,

    tools=[
        count_emails,
        search_emails,
        get_email_details,
        get_ai_statistics,
    ],
)


# ============================================================
# 27. CHAT LOOP
# ============================================================

async def run_chat():
    """
    Interaktivní terminálový chat.
    """

    print()
    print("=" * 70)
    print("GMAIL AI CHAT")
    print("=" * 70)

    print(
        "Můžeš se ptát například:"
    )

    print(
        "- Kolik mailů mi přišlo za poslední měsíc?"
    )

    print(
        "- Kolik reklam agent našel?"
    )

    print(
        "- Najdi důležité e-maily z posledních 7 dní."
    )

    print(
        "- Najdi e-maily od České spořitelny."
    )

    print(
        "- Ukaž posledních 5 AI_UNCERTAIN zpráv."
    )

    print()
    print(
        "Pro ukončení napiš: exit"
    )
    print("=" * 70)
    print()

    conversation = []

    while True:

        user_input = input(
            "Ty: "
        ).strip()

        if not user_input:
            continue

        if user_input.lower() in {
            "exit",
            "quit",
            "konec",
        }:

            print(
                "\nGmail AI Chat ukončen."
            )

            break

        try:

            # Jednoduchá krátkodobá historie konverzace.
            #
            # Llama díky tomu chápe např.:
            #
            # "Kolik jich bylo?"
            #
            # po předchozí otázce.
            #
            conversation.append(
                f"UŽIVATEL: {user_input}"
            )

            recent_context = "\n".join(
                conversation[-8:]
            )

            result = await Runner.run(
                chat_agent,

                input=f"""
DOSAVADNÍ KONVERZACE:
{recent_context}

AKTUÁLNÍ DOTAZ:
{user_input}
""",
            )

            answer = str(
                result.final_output
            )

            print()
            print(
                f"Agent: {answer}"
            )
            print()

            conversation.append(
                f"ASISTENT: {answer}"
            )

        except Exception as exc:

            logger.exception(
                "Chyba Gmail chatu."
            )

            print()
            print(
                f"Agent: Nastala chyba: {exc}"
            )
            print()


# ============================================================
# 28. CLEANUP / LIVE MAIN
# ============================================================

async def run_processing():

    batch_number = 0

    while True:

        batch_number += 1

        logger.info(
            "START DÁVKY %d",
            batch_number,
        )

        count = await process_batch(
            runtime["service"],
            batch_number,
        )

        if count == 0:

            logger.info(
                "Žádné další nezpracované e-maily."
            )

            break

        if DRY_RUN:

            logger.info(
                "DRY RUN -> další dávka se nespouští."
            )

            break

        if MODE == "live":

            logger.info(
                "LIVE dávka dokončena."
            )

            break


# ============================================================
# 29. MAIN
# ============================================================

async def main():

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
        "LLM: %s",
        OLLAMA_MODEL,
    )

    logger.info(
        "LLM SERVER: %s",
        OLLAMA_URL,
    )

    logger.info(
        "FRAMEWORK: OpenAI Agents SDK"
    )

    logger.info(
        "LOG FILE: %s",
        LOG_FILE,
    )

    logger.info(
        "=" * 70
    )


    # Gmail připojení
    service = get_gmail_service()

    runtime[
        "service"
    ] = service


    # AI labels
    (
        processed_label_id,
        category_label_ids,
    ) = initialize_ai_labels(
        service
    )

    runtime[
        "processed_label_id"
    ] = processed_label_id

    runtime[
        "category_label_ids"
    ] = category_label_ids


    try:

        if MODE == "chat":

            await run_chat()

        elif MODE in {
            "cleanup",
            "live",
        }:

            await run_processing()

        else:

            raise ValueError(
                f"Neznámý MODE: {MODE}"
            )

    finally:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        logger.info(
            "CELKOVÁ DOBA BĚHU: %s",
            format_duration(
                elapsed
            ),
        )


# ============================================================
# 30. START PROGRAMU
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.warning(
            "Program ukončen uživatelem."
        )