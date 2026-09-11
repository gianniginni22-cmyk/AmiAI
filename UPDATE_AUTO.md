# Auto-update — Amigurumi AI

Amigurumi AI aggiorna automaticamente l'applicazione all'avvio quando viene pubblicata una versione superiore.

## Flusso

```text
Avvio AmigurumiAI.exe
        |
        v
legge manifest HTTPS pubblico
        |
        v
versione più recente > versione locale?
        |
      sì + URL HTTPS + SHA-256 valido
        |
        v
AmigurumiAI-Updater.exe
        |
        v
download installer -> verifica SHA-256
        |
        v
attende chiusura AmigurumiAI.exe
        |
        v
avvia installer in modalità silenziosa
        |
        v
installer aggiorna l'app
        |
        v
app riaperta dal postinstall di Inno Setup
```

## Manifest

Il manifest pubblico deve contenere:

```json
{
  "version": "0.7.3",
  "installer_url": "https://github.com/gianniginni22-cmyk/AmigurumiAI/releases/download/v0.7.3/AmigurumiAI-Setup-0.7.3.exe",
  "sha256": "<SHA256_DELL_INSTALLER>",
  "mandatory": false
}
```

Il client accetta esclusivamente URL `https://` e richiede uno SHA-256 esadecimale di 64 caratteri.

## Pubblicazione di una nuova versione

1. Incrementare `APP_VERSION` in `desktop.py`.
2. Aggiornare la versione Inno Setup in `packaging/AmigurumiAI.iss`.
3. Costruire il nuovo installer Windows.
4. Calcolare lo SHA-256 dell'installer.
5. Pubblicare installer e manifest su HTTPS pubblico.
6. Al successivo avvio, le installazioni precedenti rileveranno automaticamente la nuova versione.

Non serve distribuire manualmente un nuovo updater: l'updater è incluso nell'installazione e viene aggiornato insieme all'app.
