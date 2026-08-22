from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

COMPOSE_FILE = PROJECT_DIR / "compose.yaml"
DATABASE_DIR = PROJECT_DIR / "database"

SCHEMA_FILE = DATABASE_DIR / "01-schema.sql"
SAMPLE_DATA_FILE = DATABASE_DIR / "02-sample-data.sql"

POSTGRES_CONTAINER = "no-code-agent-postgres"

POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = 5432

ADMINER_URL = "http://127.0.0.1:8080"

LANGFLOW_HOST = "127.0.0.1"
LANGFLOW_PORT = 7860
LANGFLOW_URL = "http://127.0.0.1:7860"

MAX_POSTGRES_WAIT_SECONDS = 60
MAX_LANGFLOW_WAIT_SECONDS = 180


# ============================================================
# WINDOWS PATHS
# ============================================================

LOCALAPPDATA = os.environ.get("LOCALAPPDATA")
APPDATA = os.environ.get("APPDATA")

if not LOCALAPPDATA or not APPDATA:
    print("Tento start script je určen pro Windows.")
    sys.exit(1)

LANGFLOW_LOCAL_DIR = Path(LOCALAPPDATA) / "com.LangflowDesktop"
LANGFLOW_ROAMING_DIR = Path(APPDATA) / "com.LangflowDesktop"

LANGFLOW_VENV = LANGFLOW_LOCAL_DIR / ".langflow-venv"

LANGFLOW_EXE = (
    LANGFLOW_VENV
    / "Scripts"
    / "langflow.exe"
)

LANGFLOW_PYTHON = (
    LANGFLOW_VENV
    / "Scripts"
    / "python.exe"
)

UV_EXE = (
    LANGFLOW_LOCAL_DIR
    / "uv"
    / "uv.exe"
)

LANGFLOW_DATABASE_FILE = (
    LANGFLOW_ROAMING_DIR
    / "data"
    / "database.db"
)

LANGFLOW_REQUIREMENTS_FILE = (
    LANGFLOW_ROAMING_DIR
    / "data"
    / "requirements.txt"
)

LANGFLOW_LOG_FILE = (
    PROJECT_DIR
    / "langflow-start.log"
)

BUNDLED_LANGFLOW_WHEEL = Path(
    r"C:\Program Files\Langflow\resources\langflow-1.10.0-py3-none-any.whl"
)


# ============================================================
# HELPERS
# ============================================================

def header(text: str) -> None:
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def run_command(
    command: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:

    print("> " + " ".join(command))

    return subprocess.run(
        command,
        cwd=PROJECT_DIR,
        check=check,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def port_is_open(
    host: str,
    port: int,
    timeout: float = 1.0,
) -> bool:

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout,
        ):
            return True

    except OSError:
        return False


def wait_for_enter() -> None:
    try:
        input("\nStiskněte Enter pro ukončení startovacího okna...")
    except EOFError:
        pass


# ============================================================
# PROJECT FILES
# ============================================================

def check_project_files() -> None:

    header("1/8  KONTROLA PROJEKTU")

    required_files = [
        COMPOSE_FILE,
        SCHEMA_FILE,
        SAMPLE_DATA_FILE,
    ]

    missing = [
        file
        for file in required_files
        if not file.exists()
    ]

    if missing:

        print("Chybí tyto soubory:")

        for file in missing:
            print(f"  - {file}")

        raise RuntimeError(
            "Projekt není kompletní."
        )

    print("Projektové soubory: OK")


# ============================================================
# PODMAN
# ============================================================

def check_podman() -> None:

    header("2/8  KONTROLA PODMANU")

    if shutil.which("podman") is None:
        raise RuntimeError(
            "Podman nebyl nalezen.\n"
            "Nainstalujte a spusťte Podman Desktop."
        )

    result = run_command(
        ["podman", "--version"],
        capture_output=True,
    )

    print(result.stdout.strip())

    result = run_command(
        ["podman", "info"],
        check=False,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Podman je nainstalovaný, ale není připravený.\n"
            "Spusťte Podman Desktop a počkejte na spuštění Podman machine."
        )

    print("Podman: OK")


def start_containers() -> None:

    header("3/8  SPUŠTĚNÍ POSTGRESQL A ADMINERU")

    run_command(
        ["podman", "compose", "config"]
    )

    run_command(
        ["podman", "compose", "up", "-d"]
    )


def wait_for_postgres() -> None:

    header("4/8  ČEKÁM NA POSTGRESQL")

    started = time.time()

    while (
        time.time() - started
        < MAX_POSTGRES_WAIT_SECONDS
    ):

        result = run_command(
            [
                "podman",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                POSTGRES_CONTAINER,
            ],
            check=False,
            capture_output=True,
        )

        status = result.stdout.strip()

        print(f"PostgreSQL: {status}")

        if status == "healthy":

            if not port_is_open(
                POSTGRES_HOST,
                POSTGRES_PORT,
            ):
                raise RuntimeError(
                    "PostgreSQL je healthy, ale port 5432 není dostupný."
                )

            print(
                f"PostgreSQL: READY "
                f"({POSTGRES_HOST}:{POSTGRES_PORT})"
            )

            return

        time.sleep(2)

    raise RuntimeError(
        "PostgreSQL se nepodařilo spustit."
    )


# ============================================================
# LANGFLOW INSTALLATION
# ============================================================

def check_langflow_files() -> None:

    header("5/8  KONTROLA LANGFLOW")

    if not LANGFLOW_PYTHON.exists():
        raise RuntimeError(
            "LangFlow Desktop Python prostředí nebylo nalezeno.\n\n"
            "Spusťte alespoň jednou LangFlow Desktop, "
            "aby se vytvořilo jeho prostředí."
        )

    if not UV_EXE.exists():
        raise RuntimeError(
            "LangFlow UV nebyl nalezen."
        )

    print(f"Python:   {LANGFLOW_PYTHON}")
    print(f"LangFlow: {LANGFLOW_EXE}")
    print(f"UV:       {UV_EXE}")
    print(f"Flow DB:  {LANGFLOW_DATABASE_FILE}")


def langflow_launcher_works() -> bool:

    if not LANGFLOW_EXE.exists():
        return False

    result = subprocess.run(
        [
            str(LANGFLOW_EXE),
            "--version",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = result.stdout or ""

    if result.returncode != 0:
        return False

    return "langflow" in output.lower()


def repair_langflow_launcher() -> None:

    header("OPRAVA LANGFLOW LAUNCHERU")

    if not BUNDLED_LANGFLOW_WHEEL.exists():
        raise RuntimeError(
            "LangFlow launcher je poškozený a instalační WHL "
            "soubor nebyl nalezen:\n"
            f"{BUNDLED_LANGFLOW_WHEEL}"
        )

    print(
        "LangFlow launcher není funkční. "
        "Provádím automatickou opravu..."
    )

    run_command(
        [
            str(UV_EXE),
            "pip",
            "install",
            "--python",
            str(LANGFLOW_PYTHON),
            "--force-reinstall",
            str(BUNDLED_LANGFLOW_WHEEL),
        ]
    )

    if not langflow_launcher_works():
        raise RuntimeError(
            "LangFlow launcher se nepodařilo opravit."
        )

    print("LangFlow launcher opraven.")


# ============================================================
# LANGFLOW DEPENDENCIES
# ============================================================

def module_exists(module_name: str) -> bool:

    result = subprocess.run(
        [
            str(LANGFLOW_PYTHON),
            "-c",
            f"import {module_name}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return result.returncode == 0


def install_dependency(
    module_name: str,
    package_name: str,
) -> None:

    if module_exists(module_name):

        print(f"{module_name}: OK")
        return

    print(
        f"{module_name}: CHYBÍ -> instaluji {package_name}"
    )

    run_command(
        [
            str(UV_EXE),
            "pip",
            "install",
            "--python",
            str(LANGFLOW_PYTHON),
            package_name,
        ]
    )

    if not module_exists(module_name):
        raise RuntimeError(
            f"Nepodařilo se nainstalovat {package_name}."
        )

    print(f"{module_name}: OK")


def ensure_dependencies() -> None:

    header("6/8  KONTROLA LANGFLOW DEPENDENCIES")

    install_dependency(
        "langchain_openai",
        "langchain-openai",
    )

    install_dependency(
        "psycopg2",
        "psycopg2-binary",
    )


# ============================================================
# LANGFLOW ENVIRONMENT
# ============================================================

def build_langflow_environment() -> dict[str, str]:

    env = os.environ.copy()

    # Windows Unicode
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # SQL Database Tool smí komunikovat s lokálním PostgreSQL.
    env["LANGFLOW_SSRF_ALLOWED_HOSTS"] = (
        "localhost,127.0.0.1"
    )

    # Použije se interní DB LangFlow Desktop.
    # Díky tomu na našem PC zůstanou vidět uložené flows.
    database_url = (
        "sqlite:///"
        + LANGFLOW_DATABASE_FILE.as_posix()
    )

    env["LANGFLOW_DATABASE_URL"] = database_url

    return env


# ============================================================
# LANGFLOW START
# ============================================================

def start_langflow() -> subprocess.Popen | None:

    header("7/8  SPUŠTĚNÍ LANGFLOW")

    if port_is_open(
        LANGFLOW_HOST,
        LANGFLOW_PORT,
    ):

        print(
            "LangFlow již běží na portu 7860."
        )

        return None

    env = build_langflow_environment()

    command = [
        str(LANGFLOW_EXE),
        "run",
        "--host",
        LANGFLOW_HOST,
        "--port",
        str(LANGFLOW_PORT),
    ]

    print("> " + " ".join(command))
    print(f"Log: {LANGFLOW_LOG_FILE}")

    log_handle = open(
        LANGFLOW_LOG_FILE,
        "w",
        encoding="utf-8",
    )

    process = subprocess.Popen(
        command,
        cwd=PROJECT_DIR,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )

    print(f"LangFlow PID: {process.pid}")

    return process


def show_langflow_log() -> None:

    if not LANGFLOW_LOG_FILE.exists():
        return

    print()
    print("-" * 72)
    print("POSLEDNÍ ŘÁDKY LANGFLOW LOGU")
    print("-" * 72)

    lines = LANGFLOW_LOG_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    for line in lines[-40:]:
        print(line)


def wait_for_langflow(
    process: subprocess.Popen | None,
) -> None:

    started = time.time()

    while (
        time.time() - started
        < MAX_LANGFLOW_WAIT_SECONDS
    ):

        if port_is_open(
            LANGFLOW_HOST,
            LANGFLOW_PORT,
        ):

            print()
            print(
                "LangFlow backend: READY "
                "(127.0.0.1:7860)"
            )

            return

        if (
            process is not None
            and process.poll() is not None
        ):

            show_langflow_log()

            raise RuntimeError(
                f"LangFlow skončil s chybovým kódem "
                f"{process.returncode}."
            )

        print("Čekám na LangFlow...")

        time.sleep(2)

    show_langflow_log()

    raise RuntimeError(
        "LangFlow backend se nepodařilo spustit "
        "do 180 sekund."
    )


# ============================================================
# FINAL
# ============================================================

def open_interfaces() -> None:

    header("8/8  PROJEKT JE PŘIPRAVEN")

    print()
    print(f"LangFlow: {LANGFLOW_URL}")
    print(f"Adminer:  {ADMINER_URL}")

    print()
    print("PostgreSQL:")
    print("  Host:     127.0.0.1")
    print("  Port:     5432")
    print("  Database: motor_sales")
    print("  User:     motor_admin")

    print()
    print("LangFlow SQL Database URL:")
    print(
        "postgresql+psycopg2://"
        "motor_admin:motor_password@"
        "127.0.0.1:5432/motor_sales"
    )

    print()
    print(
        "Pokud se workflow v LangFlow ještě nenachází, "
        "importujte JSON ze složky langflow."
    )

    print(
        "OpenAI API Key musí uživatel vložit vlastní."
    )

    webbrowser.open(LANGFLOW_URL)

    time.sleep(1)

    webbrowser.open(ADMINER_URL)


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    header("NO-CODE AGENT - START")

    try:

        check_project_files()

        check_podman()

        start_containers()

        wait_for_postgres()

        check_langflow_files()

        if not langflow_launcher_works():
            repair_langflow_launcher()
        else:
            print("LangFlow launcher: OK")

        ensure_dependencies()

        process = start_langflow()

        wait_for_langflow(process)

        open_interfaces()

        return 0

    except subprocess.CalledProcessError as exc:

        header("CHYBA EXTERNÍHO PŘÍKAZU")

        print(
            f"Příkaz skončil s návratovým kódem "
            f"{exc.returncode}."
        )

        return 1

    except Exception as exc:

        header("CHYBA")

        print(exc)

        if LANGFLOW_LOG_FILE.exists():
            print()
            print(
                f"LangFlow log: {LANGFLOW_LOG_FILE}"
            )

        return 1


if __name__ == "__main__":

    exit_code = main()

    wait_for_enter()

    sys.exit(exit_code)