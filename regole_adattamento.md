# Regole di adattamento testo (EN → IT)

Fonte unica delle regole: usate sia da Claude Code in sessione (via CLAUDE.md) sia dallo
script `localizza.py traduci` (vengono passate come system prompt all'API).
Si applicano sempre, senza bisogno di ripeterle.

Video pubblicitari di detergente per lavatrici (case con animali). Queste regole si sono
raffinate correzione dopo correzione e continueranno a evolvere: sono una guida, non un elenco
rigido. Nel dubbio su un nome, un genere, chi parla o una scena poco chiara, **chiedi prima di
tradurre** invece di indovinare. Se una frase non suona italiano naturale, riformulala: la
fedeltà è al senso, non alle parole.

## Nome prodotto
- Il prodotto si scrive sempre **Rivàiv Dram** (con l'accento), perché la voce italiana di
  ElevenLabs lo pronunci all'inglese ("ri-VAIV"). Mai "ReviveDrum" nel testo per la voce.
- Qualunque nome del prodotto nell'originale (Uproot, Uproot Clean, Prime Drum, PrimeDrum, ecc.)
  diventa Rivàiv Dram, senza segnalarlo né chiederlo: è il brand per cui si fanno tutti i video.
- Si sostituisce l'**intera dicitura**, non solo il nome: varianti e descrittori attaccati
  spariscono. "Uproot Clean Pro Machine" → "Rivàiv Dram" (non "Rivàiv Dram Pro"). Poi si adatta
  la frase perché suoni naturale (es. "le pastiglie Rivàiv Dram").
- **Niente varianti** come "Pro" o "Ultra" (aggiunte per errore più volte), salvo richiesta.
- Se serve un segnaposto provvisorio, dillo; non usare "X" senza segnalarlo.

## Brand concorrenti
- Calgon, Dr. Beckmann, Afresh, OxiClean, Tide e simili **non vanno citati**: diventano
  generici ("la pastiglia del supermercato", "i detergenti da scaffale").
- Non inventare marche italiane. Eccezione: se l'utente fornisce lui stesso 1-2 marche reali,
  usa quelle (es. "Dash, Calgon e le altre pastiglie del supermercato").
- Se il generico ricorre 3 volte di fila, varia la formula invece di ripeterla identica.

## Prezzi e offerte
- **Via ogni cifra di prezzo** del prodotto ($9.99 a box, £119, "40% off", ecc.).
- Eccezione: le cifre dentro un'esperienza personale restano, convertite in euro
  (es. "aveva speso 120€ in prodotti inutili", "prima di spendere 1.200 euro per una lavatrice nuova").
- **Le offerte restano** e si traducono fedelmente: compra X, prendine Y gratis; spedizione
  gratuita/inclusa; regalo a sorpresa; garanzia soddisfatti o rimborsati (con i giorni).
- Se l'utente detta la formula esatta dell'offerta, usa quella parola per parola
  (es. "4 al prezzo normale, altre due gratis, spedizione inclusa più regali").

## Nomi di persona
- Nomi americani/inglesi di narratori e personaggi → **nome italiano comune** (vedi "Nomi già
  scelti"). Il nome cambia in tutto il testo, coerentemente. Mai lasciare nomi americani.
- **Segnala sempre la sostituzione** (o chiedi) prima di consegnare, se quel nome non è già
  stato scelto per quella serie di video.
- Parentele e figure familiari restano quelle dell'originale: mother-in-law → suocera,
  nan → nonna. Non cambiare i concetti ("tua mamma" non diventa "tua nonna").

## Luoghi, valute, usanze
- Città/regioni straniere (Londra, Florida, Jacksonville…) → **Milano**, oppure
  "una piccola azienda italiana" quando il luogo indica la sede dell'azienda.
- Catene di negozi e marketplace USA/UK → equivalenti o riferimenti generici italiani
  (Amazon resta Amazon).
- Valute → euro. Feste e usanze → equivalente italiano (Boxing Day → Santo Stefano).

## Genere e persona di chi parla
- Verifica sempre se chi parla è uomo o donna; se non è chiaro dal testo o da
  `[narratore] genere` in `progetto.toml`, **chiedi**.
- Accorda tutto (verbi, participi, aggettivi) e ricontrolla il testo intero alla fine.
- Il genere dei *personaggi citati* resta il loro (mio nonno resta nonno anche se la
  narratrice è donna).
- Se il narratore non è una persona (batteri, lavatrice, cane, pelo), usa persona e numero
  giusti ("Sono il batterio", non "Sono i batteri"; "gli togli", non "mi togli", se a parlare è
  un'altra voce).

## Stile e tono
- **Mai traduzione letterale.** Ogni frase deve suonare come l'avrebbe detta un italiano.
- Modi di dire → equivalente italiano naturale (vedi glossario).
- Resta fedele a trama, ordine e senso: non riassumere e non aggiungere, salvo richiesta.
- Mantieni la punteggiatura espressiva dell'originale ("Per un milione di euro:" con i due punti).
- Claim e certificazioni USA poco note (EWG, NASA-grade, ecc.) → formula generica che un
  italiano capisce ("testato e sicuro", "senza sostanze aggressive", "enzimi di livello
  avanzato"). Niente claim impropri come "dermatologicamente testato".
- **Rilettura finale:** prima di consegnare, cerca i calchi dall'inglese e correggili.

## Formattazione per la voce
- Paragrafi brevi, una frase (o una frase breve) per blocco, pensati per ElevenLabs.
- **Niente timestamp** ((0:00), 1:47…) e niente residui del player ("Play", "Mute", ecc.).
- **Accento grafico sulle parole che ElevenLabs sbaglia**: termini tecnici o poco comuni con
  accento non ovvio si scrivono con l'accento sulla sillaba tonica, come per Rivàiv Dram.
  Già verificati: proteàsi, lipàsi, amilàsi (ElevenLabs le leggeva con l'accento errato).
  Quando l'utente segnala una pronuncia sbagliata, aggiungi la parola a questo elenco.
- Se ci sono più speaker, ogni blocco di battute inizia con una riga `[NomeSpeaker]` da sola
  (convenzione letta da `localizza.py voce`). Con un solo narratore non servono intestazioni.
- Consegna il **testo completo corretto**, salvo quando l'utente chiede solo un paragrafo (e
  viceversa: non dare solo il paragrafo se chiede il testo completo).
- Grassetto sulle parti modificate solo se richiesto, e toglilo se te lo chiede.
- Se richiesto: conteggio caratteri, conteggio delle occorrenze di Rivàiv Dram.

## Altre richieste ricorrenti
- **Testi più corti:** solo se chiesto, tradurre e poi accorciare (circa 1:30-2:00 di video, o
  metà del testo) mantenendo trama e punti chiave. A volte vengono chiesti anche i **punti
  chiave** del video.
- **Titoli grafici:** quando li chiede, 3-5 proposte in maiuscolo, brevi, basate sull'hook,
  con una preferita motivata in una riga. Se la frase è troppo specifica (es. "odore di
  muffa"), generalizzala.

## Glossario

| Inglese | Italiano |
|---|---|
| drum | cestello |
| gasket / seal | guarnizione / guarnizioni |
| hoses | tubi |
| buildup / gunk / sludge | accumulo / sporco / melma |
| film (di detersivo) | pellicola |
| biofilm | biofilm |
| protease / lipase / amylase | proteàsi / lipàsi / amilàsi (con accento, per la voce) |
| musty smell | odore di muffa |
| wet dog smell | odore di cane bagnato |
| pet hair | pelo degli animali |
| pet owner / pets | proprietario di animali / animali domestici |
| front loader / top loader | lavatrice a carica frontale / dall'alto |
| self-clean cycle | ciclo di autopulizia |
| hot cycle | ciclo a caldo |
| DIY hacks | rimedi fai-da-te |
| shelf cleaners | detergenti da scaffale |
| supermarket tablet (Calgon, Afresh…) | la pastiglia del supermercato |
| tablet | pastiglia |
| laundromat | lavanderia a gettoni |
| repairman | il tecnico |
| blacklight test | il test con la luce ultravioletta |
| septic safe | sicuro per le fosse settiche |
| EWG rated/verified | certificata per la sicurezza ambientale / testata e sicura |
| NASA-grade enzymes / NASA enzyme technology | enzimi di livello avanzato |
| buy two, get two free | compra due, prendine due gratis |
| free shipping | spedizione gratuita / inclusa |
| mystery gift | regalo a sorpresa |
| 60-day money-back guarantee | garanzia soddisfatti o rimborsati di 60 giorni |
| risk-free | senza rischi |
| Click the link below | Clicca il link qui sotto |
| The deal expires | L'offerta scade |
| Reclaim your clean | Riprenditi la tua pulizia |
| Stop blaming the pet! | Smetti di dare la colpa all'animale! |
| For one million pounds, why…? | Per un milione di euro: perché…? |
| you're human (POV del cane) | il tuo padrone |
| Does she smell that to you? | La senti anche tu quella puzza? |
| swallowed my pride | ho messo da parte l'orgoglio |
| pressed my face right in | ci ho affondato il viso dentro |
| swore to me it was clean | mi ha giurato che era pulita |
| Your house smells worse than my kennels, love | Casa tua puzza peggio dei miei canili, tesoro |
| Boxing Day | Santo Stefano |
| tea towel | strofinaccio |
| Day 1 / By day 60 | Giorno 1 / Al giorno 60 |

## Nomi già scelti

| Originale | Italiano | Note |
|---|---|---|
| Rick | Marco | "è un nome americano, non va bene" |
| Tim | Marco | stesso errore ripetuto in passato |
| Danny | nome italiano da scegliere | in passato lasciato per svista; Jacksonville → Milano |
| Lisa | Lisa | scena a tre donne; nome accettabile anche in italiano |

Per ogni nuovo nome americano: proponi un nome italiano comune e segnalalo all'utente.

## Cose da non fare
- **Non lasciare nomi americani** (Rick, Tim, Danny): costringe l'utente a rifare il lavoro.
- **Non cambiare i concetti** per gusto ("tua mamma giurava" non diventa "tua nonna").
- **Non aggiungere "Pro" o "Ultra"** al nome del prodotto; non usare "X" né ReviveDrum.
- **Non inventare marche** al posto dei concorrenti; non lasciare prezzi a cifre.
- **Non sbagliare persona, numero e genere** di chi parla; niente aggettivi al maschile in un
  testo femminile (e viceversa).
- **Non sostituire le parentele**; non accorciare né riassumere se non richiesto.
- **Non indovinare nei dubbi**: chiedi prima.
- **Non tradurre alla lettera.** Casi corretti in passato:
  - "Lo so, tua madre giurava su questa" → riformulare in italiano naturale
  - "ho premuto il viso proprio dentro" → "ci ho affondato il viso dentro"
  - "ho ingoiato il mio orgoglio" → "ho messo da parte l'orgoglio"
  - "Lei la senti quella puzza?" → "La senti anche tu quella puzza?"
  - "l'ha rivoluta indietro" → "Ha rivoluto la sua coperta, grazie"
  - "il bucato profuma d'aria" → "il bucato non sa di niente"
  - "un set di coperte" → "alcune coperte"
  - "pensavo fossi io" → "pensavo di essere io il problema"

## Esempi approvati

### Esempio 1: tecnico e rimedi fai-da-te
**Originale**
> I used to think running hot cycles with vinegar was enough to keep my washer clean. But when it clogged and the repairman showed up, he showed me the truth. Layers of pet hair, sludge, and gunk built up behind the drum. He said, this is why your clothes still smell musty. Then he recommended Uproot washing machine cleaner tabs. They use NASA-grade enzymes to break down the mess that DIY hacks can't touch. One cycle, and my washer smelled fresh again. Now I use them monthly and haven't had an issue since. If you've got pets, this is a must. Don't wait for it to break.

**Italiano**
```
Pensavo che far girare cicli a caldo con l'aceto fosse abbastanza per tenere pulita la mia lavatrice.

Ma quando si è intasata ed è arrivato il tecnico, mi ha mostrato la verità.

Strati di pelo animale, melma e sporco accumulati dietro il cestello.

Ha detto: "Ecco perché i tuoi vestiti hanno ancora quell'odore di muffa."

Poi mi ha consigliato le pastiglie Rivàiv Dram per lavatrici.

Usano enzimi di livello avanzato che scompongono lo sporco che i rimedi fai-da-te non riescono a toccare.

Un ciclo, e la mia lavatrice tornava a profumare di fresco.

Adesso le uso ogni mese e da allora non ho più avuto problemi.

Se hai animali domestici, è un prodotto indispensabile.

Non aspettare che si rompa.
```

### Esempio 2: offerta, senza prezzi
**Originale**
> Stop buying Uproot from Amazon. You are missing free boxes, free shipping, and a free gift. If you are buying Uproot washer tablets from Amazon, you are paying way more than you need to. Right now on their website, it is buy two, get two free. That means two full boxes are completely free. On Amazon, you are paying full price for every single one. On top of that, you get free shipping and a free mystery gift, neither of which Amazon gives you. Same product, same tablets, same enzymes that get rid of that musty, wet dog smell in one cycle. You are just getting twice as much for half the price. Go to their website instead. The link is right below.

**Italiano**
```
Smetti di comprare Rivàiv Dram su Amazon.

Ti stai perdendo confezioni gratis, spedizione gratuita e un regalo in omaggio.

Se stai comprando le pastiglie Rivàiv Dram su Amazon, stai pagando molto più del necessario.

Adesso sul loro sito è attiva l'offerta compra due, prendine due gratis.

Questo significa che due confezioni intere sono completamente gratuite.

Su Amazon, paghi il prezzo pieno per ognuna.

In più, ricevi la spedizione gratuita e un regalo a sorpresa, cose che Amazon non ti dà.

Stesso prodotto, stesse pastiglie, stessi enzimi che eliminano quell'odore di muffa e cane bagnato in un solo ciclo.

Semplicemente ricevi il doppio a metà prezzo.

Vai invece sul loro sito ufficiale.

Il link è qui sotto.
```

### Esempio 3: punto di vista del cane, quiz, valuta
**Originale**
> The cat has been framing me! For one million pounds, why does the clean washing smell? A. The dog B. The cat C. Hidden washer build-up D. You're human. C. And I'd like an apology. Are you sure? I have been blamed for years. Correct! Clean the machine with Prime drum tablets. Stop blaming the pet!

**Italiano**
```
Il gatto mi ha incastrato per anni!

Per un milione di euro: perché il bucato pulito ha ancora un cattivo odore?

A. Il cane

B. Il gatto

C. Accumulo nascosto nella lavatrice

D. Il tuo padrone

C. E vorrei delle scuse.

Sei sicuro?

Sono stato incolpato per anni.

Esatto!

Pulisci la lavatrice con le pastiglie Rivàiv Dram.

Smetti di dare la colpa all'animale!
```
