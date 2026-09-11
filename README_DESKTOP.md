# Amigurumi AI Desktop v0.6.2

Questa versione trasforma l'MVP web in una vera applicazione desktop: il backend FastAPI viene avviato localmente e l'interfaccia viene mostrata in una finestra nativa tramite pywebview.

## Avvio sviluppo

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-desktop.txt
python desktop.py
```

Non serve aprire il browser o lanciare uvicorn manualmente.

## API key

Nell'app apri **Impostazioni AI**, inserisci la OpenAI API key e premi **Salva chiave**. La chiave viene salvata nel file di configurazione dell'utente:

- Windows: `%APPDATA%\\AmigurumiAI\\config.json`
- macOS: `~/Library/Application Support/AmigurumiAI/config.json`
- Linux: `~/.config/AmigurumiAI/config.json`

La variabile d'ambiente `OPENAI_API_KEY`, se presente, ha priorità.

## Windows installer

Prerequisiti sulla macchina di build:
- Python 3.11/3.12
- Inno Setup 6

Apri PowerShell nella cartella del progetto e lancia:

```powershell
.\\packaging\\build_windows.ps1
```

Output:
- `dist/AmigurumiAI.exe`
- `dist/installer/AmigurumiAI-Setup-0.6.2.2.exe`

Il PC dell'utente finale non deve avere Python installato: PyInstaller incorpora il runtime e le dipendenze.

## macOS

```bash
./packaging/build_macos.sh
```

Per distribuire pubblicamente su macOS, firma e notarizza l'app con un Developer ID Apple.

## Linux

```bash
./packaging/build_linux.sh
```

L'eseguibile risultante è in `dist/AmigurumiAI`. Per un pacchetto `.deb`/AppImage aggiungere un passaggio di packaging della distribuzione target.

## Architettura

```text
AmigurumiAI.exe / .app
        |
        +-- pywebview (finestra desktop)
        |
        +-- FastAPI locale (127.0.0.1)
        |
        +-- Shape Graph
        +-- Profile Fitter
        +-- Depth & Pose
        +-- Crochet Geometry Engine
        +-- UI HTML/CSS/JS
```

La chiave API non viene inviata a un server proprietario dell'app: viene usata dal backend locale per chiamare il provider configurato.
