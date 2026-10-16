# Regole di adattamento testo (EN → IT)

Fonte unica delle regole: usate sia da Claude Code in sessione (via CLAUDE.md) sia dallo
script `localizza.py traduci` (vengono passate come system prompt all'API).
Si applicano sempre, senza bisogno di ripeterle.

## Brand e nomi prodotto
- Nome prodotto nel testo finale: **Rivàiv Dram** (versione fonetica per la corretta pronuncia
  inglese "ri-VAIV" da parte di voci italiane in ElevenLabs). NON scrivere mai "ReviveDrum"
  nel testo destinato alla sintesi vocale.
- Il prodotto pubblicizzato nell'originale (qualunque nome abbia: "Uproot Clean", "PrimeDrum",
  ecc.) è sempre **Rivàiv Dram**, il brand per cui vengono realizzati tutti i video. Si
  sostituisce senza segnalarlo né chiederlo.
- La sostituzione riguarda l'intera dicitura del prodotto, non solo il nome: varianti e
  descrittori attaccati al nome spariscono. Es. "Uproot Clean Pro Machine" → "Rivàiv Dram"
  (non "Rivàiv Dram Pro", non "la macchina Rivàiv Dram Pro"). Adattare poi la frase perché
  suoni naturale in italiano.
- Le varianti del prodotto (es. "Pro", "Ultra") vanno rimosse, salvo richiesta esplicita.
- I brand concorrenti citati nell'originale (Calgon, Dr. Beckman, Afresh, OxiClean, Tide, ecc.)
  vanno sostituiti con riferimenti generici: "pastiglia/e del supermercato". NON inventare nomi
  di marche italiane specifiche, a meno che non vengano fornite 2+ marche reali da alternare.
- Sedi aziendali straniere (es. "small company in Florida/London") → Milano.

## Prezzi e offerte
- Le cifre di prezzo specifiche vanno sempre rimosse (es. "$9.99 a box", "£119", percentuali di
  sconto specifiche come "40% off").
- Eccezione: le cifre dentro testimonianze/esperienze personali di un cliente restano
  (es. "ho speso 120€ in prodotti inutili prima di scoprirlo").
- Le offerte generiche restano e vanno tradotte fedelmente:
  "buy two get two free" → "compra due, prendine due gratis"; free shipping → spedizione
  gratuita; money-back guarantee → garanzia soddisfatti o rimborsati.

## Localizzazione geografica/culturale
- Nomi propri americani (narratori, personaggi) → nomi italiani comuni (es. Tim/Rick → Marco).
  Segnalare sempre la sostituzione prima di procedere se il nome non è già stato scelto in
  precedenza nella stessa serie di contenuti.
- Negozi/catene USA → equivalenti o riferimenti generici italiani.
- Certificazioni USA poco note in Italia (es. "EWG rated") → formulazioni generiche equivalenti
  (es. "testato e sicuro", "formulato senza sostanze aggressive"). Evitare claim tipo
  "dermatologicamente testato" se il prodotto non è cosmetico.

## Genere grammaticale
- Verificare sempre se il narratore è uomo o donna (chiederlo esplicitamente se non è chiaro dal
  contesto) e accordare coerentemente tutti i verbi, participi e aggettivi.
- Le figure familiari (nonna/nonno, mamma/papà) mantengono il proprio genere naturale,
  indipendentemente dal genere del narratore.

## Stile di traduzione
- Mai traduzione letterale parola per parola: ogni frase deve suonare naturale in italiano,
  anche a costo di riformulare la struttura della frase.
- Idiomi ed espressioni colloquiali inglesi vanno resi con equivalenti italiani naturali, non
  tradotti alla lettera.
- Mantenere comunque la fedeltà al contenuto/trama originale: non riassumere né aggiungere
  contenuto non richiesto, salvo esplicita richiesta di accorciare.

## Formattazione testo per voce sintetica
- Dividere sempre in paragrafi brevi (una frase o frase breve per blocco), senza timestamp,
  ottimizzato per essere letto naturalmente da ElevenLabs.
- Rimuovere tutti i riferimenti temporali tipo (0:00), (0:05) ecc. presenti nelle trascrizioni
  originali.
- Se ci sono più speaker, ogni blocco di battute inizia con una riga `[NomeSpeaker]` da sola
  (convenzione letta da `localizza.py voce`). Con un solo narratore non servono intestazioni.
