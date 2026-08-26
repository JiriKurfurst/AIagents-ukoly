# Gmail AI Agent

AI agent pro automatickou klasifikaci a organizaci e-mailů v Gmailu.

Projekt vznikl jako úkol v rámci kurzu AI agentů.

## Co agent umí

Agent načítá e-maily pomocí Gmail API, analyzuje jejich obsah a kontext e-mailového vlákna a následně zprávu klasifikuje.

Používá čtyři kategorie:

- `IMPORTANT` – zpráva vyžadující pozornost, rozhodnutí nebo akci
- `NORMAL` – běžná informační zpráva
- `ADVERTISEMENT` – reklama, newsletter nebo marketing
- `UNCERTAIN` – nejednoznačný obsah

Podle výsledku může agent provést akci v Gmailu:

| Kategorie | Akce |
|---|---|
| IMPORTANT | označí e-mail jako důležitý |
| NORMAL | ponechá e-mail beze změny |
| ADVERTISEMENT | archivuje e-mail |
| UNCERTAIN | ponechá e-mail beze změny |

Každý úspěšně zpracovaný e-mail dostane štítek:

`AI_PROCESSED`

Díky tomu agent stejnou zprávu nezpracovává opakovaně.

---

## Architektura

```text
Gmail
  |
  v
Gmail API
  |
  v
Python Gmail Agent
  |
  +--> deterministická pravidla
  |
  v
OpenAI Agents SDK
  |
  v
lokální LLM
Llama 3.1 8B
  |
  v
Ollama
  |
  v
klasifikace
  |
  +--> IMPORTANT
  +--> NORMAL
  +--> ADVERTISEMENT
  +--> UNCERTAIN
  |
  v
Gmail API
  |
  v
provedení akce + AI_PROCESSED