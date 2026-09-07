# Analisi landing Vex Media (/apply)

Fonte: HTML pubblico della pagina, letto il 2026-09-07.
Scopo: capire cosa regge la pagina e cosa Mailift può prendere davvero.

---

## Struttura, nell'ordine in cui scorre

1. **Hero.** Badge "Trusted By 200+ E-commerce Brands", occhiello qualificatore, H1 con l'offerta, sottotitolo con i due numeri grossi, VSL Wistia, CTA, carosello di 25 loghi.
2. **Risultati.** Sei casi in formato brand → before → after, ognuno con screenshot dell'account.
3. **Design.** "How Do Our Emails Actually Look?" con carosello di 22 screenshot di email.
4. **Meccanismo.** Tre card di fase: audit, build out, split test.
5. **Testimonianze video.** Quattro, ognuna con nome, ruolo e azienda.
6. **Benefici.** Quattro card con icona: repeat purchase, LTV, scalare le ads, garanzia.
7. **Deliverable.** Sei card numerate con i flussi inclusi.
8. **Wall of reviews.** Tre colonne di screenshot in scroll verticale infinito, alto 120vh.
9. **Tabella comparativa.** Vex contro "generic email agencies", sei righe per lato.
10. **About.** Storia dal 2019, "4x4 Retention Matrix™".
11. **Footer.**

Sette posizionamenti di CTA, tutti con lo stesso testo e la stessa scarsità.

---

## Cosa regge davvero la pagina

**La densità di prove, non il copy.** Cinque formati diversi di prova, in quantità: 25 loghi, 6 before/after con screenshot, 22 screenshot di email, 4 video testimonial attribuiti, una parete di recensioni. È esattamente lo "stacking" che il framework CRO chiama shower the user. Il copy tra un blocco e l'altro serve solo a raccordare.

**Le tre fasi uccidono tre obiezioni diverse.** Audit: nessun rischio, "all you do is give us access to your Klaviyo, that's it". Build out: nessuno sforzo, "you don't touch anything". Split test: nessun pagamento fino a prova fatta. Non è un elenco di servizi, è una sequenza di rimozione di attriti.

**Il formato before/after è brutale nella sua semplicità.** Nome brand, cifra prima, cifra dopo, screenshot. Nessuna narrazione, nessun contesto. Si legge in due secondi e si ripete sei volte.

**L'occhiello qualificatore.** "Lascia questa pagina se non hai un brand eCom" filtra e lusinga nello stesso movimento: chi resta si sente selezionato.

**Micro-copy che toglie frizione.** "Audits are 100% confidential" sotto due CTA. "All you do is give us access." "You don't touch anything." Ogni riga risponde a una domanda silenziosa.

**Una sola azione su tutta la pagina.** Sette bottoni, un solo testo, una sola destinazione.

---

## Cosa non funziona

**La pagina è in olandese.** L'attributo è `lang="nl"` e i player dei video testimonial mostrano "Schakel geluid in" al posto di "Enable sound". Residuo di template mai ripulito.

**I meta sono segnaposto.** `author` e `keywords` valgono entrambi "Change this".

**Refuso in un H1.** "We'll Beat Your Exisiting Flows".

**La scarsità è decorativa.** "Only 3 audit spots left this week" compare su tutti e sette i bottoni, sempre uguale. Chi torna sulla pagina la seconda volta vede gli stessi tre posti, e da quel momento smette di crederci. Il framework lo dice: la scarsità funziona solo se è vera e spiegata.

**I numeri non hanno metodo.** "€26K/mo → €904K/mo 90 Day Email Rev" mescola il mensile e il trimestrale nella stessa etichetta, ed è un 35x. Nessun caso dichiara il periodo, la baseline o il metodo di attribuzione. Sono screenshot di dashboard, cioè esattamente la metrica che la loro stessa VSL definisce inaffidabile.

**Contraddizione tra video e pagina.** Nella VSL Arturs dice che l'attribuzione Klaviyo è una medaglia di partecipazione e che quello che conta è l'incrementale misurato. Poi la sezione risultati è fatta di screenshot di revenue attribuita. Chi guarda il video e poi scrolla trova la contraddizione.

**Doppia esperienza sulla CTA.** Su desktop il bottone apre un popup con Typeform embeddato. Su mobile porta fuori sito verso Typeform. Il popup è la versione giusta e il mobile è dove sta la maggior parte del traffico.

**Ogni elemento è duplicato.** Versione desktop e versione mobile come elementi separati con hide diversi. Ogni modifica di copy va fatta due volte, e il rischio di divergenza è alto.

**La parete di recensioni alta 120vh non si legge.** Scorre da sola in tre direzioni: comunica quantità, non contenuto.

---

## Note tecniche riutilizzabili

Palette: fondo #111112, card rgba(255,255,255,0.02), bordi #2D3035, bottoni #212328, accento verde #24ad7d, testo corpo #AFAFAF.

Font: Inter per i titoli, Helvetica Now Display caricato via @font-face per corpo e bottoni.

H1 in gradiente da bianco a #A1A1A1 con background-clip su testo. Costa poco e alza molto la percezione di cura.

Due classi utility che fanno tutto il lavoro delle etichette: una pill scura con bordo e raggio 25px, e la sua variante con testo verde. Usate per "Verified Brands", "Reviews", "What do you get?" e per i numeri da #1 a #6.

Bottoni pill con hover elevate, maiuscolo, letter-spacing, freccia in coda.

Video con overlay custom in jQuery che al click riparte da zero con l'audio attivo, e controlli nativi in parte disattivati.

Tracking: Hyros più Meta Pixel.

---

## La conclusione che conta per Mailift

Questa pagina non converte per come è scritta. Converte perché sotto ogni affermazione c'è un livello di prova, e i livelli sono cinque.

Prendere la struttura senza le prove produce una pagina che promette le stesse cose con niente dietro, e legge peggio di una pagina più semplice e onesta. Il rischio concreto è costruire l'impalcatura e riempirla di aria.

**Cosa Mailift può prendere subito:** la sequenza delle tre fasi come rimozione di attriti, l'occhiello qualificatore, il micro-copy anti-frizione, la disciplina della CTA unica, la tabella comparativa, il formato before/after come schema.

**Cosa Mailift non può prendere adesso:** la densità di prove. Oggi c'è un risultato documentato (Treemme, +134% a sei mesi, ancora da confermare) e zero video testimonial. Il divario è quello, e nessuna riscrittura lo colma.

**L'ordine giusto di lavoro, quindi, è al contrario:** prima si raccolgono le prove, poi si costruisce la pagina che le ospita. Tre cose in ordine di impatto:
1. Il video testimonial di Alessio Merlo, già messo a piano nella call del 30 giugno. Un video attribuito batte sei screenshot.
2. Due o tre screenshot before/after dagli account che gestisci, con periodo e metodo dichiarati. Dichiarare il metodo è il punto in cui Mailift può battere Vex invece di imitarlo: loro mostrano revenue attribuita mentre il loro stesso video la definisce inaffidabile, tu puoi mostrare la netta e dire come l'hai calcolata.
3. I loghi dei clienti, con il permesso di usarli.

Finché mancano, la pagina di Mailift regge meglio con meno blocchi e più onestà sul metodo che con la stessa impalcatura mezza vuota.

---

# Parte 2 — Il video letto insieme alla pagina

Aggiunta dopo aver avuto la trascrizione completa della VSL e l'informazione che Vex incassa una setup fee tra i 4.000 e gli 8.000.

## La contraddizione sta dentro il video, non tra video e pagina

Nei primi venticinque secondi, il momento con la retention più alta di tutto il funnel:

> "If my don't make more money, you pay nothing. Zero dollars. You're out nothing."

Poi al minuto 3:01: "you owe us nothing. We eat the cost." Al minuto 12:49: "if our stuff doesn't beat what you have now, you get all of that for free."

Tre volte, zero.

Poi al minuto **13:33**, dentro il blocco obiezioni, quando è rimasto forse il dieci per cento di chi ha iniziato:

> "Do I have to pay some upfront deposit? It depends on the complexity to be frank. Simple builds, we can often start without a deposit. Bigger brands with heavier builds, there is usually a deposit involved."

La setup fee reale sta tra i 4.000 e gli 8.000. La promessa più forte del video sta al secondo venti, la sua smentita al minuto tredici. Chi arriva in call scopre lì il numero.

Questa è la cosa più utile emersa da tutta l'analisi, per due motivi.

**Primo:** la loro garanzia è più morbida di come suona, quindi la tua versione onesta non è più debole della loro. È più difendibile.

**Secondo:** il tuo setup a 2.000–5.000 sta sotto la metà del loro. Dichiararlo entro il primo minuto invece che al tredicesimo diventa un vantaggio, non una concessione.

## Il proof stack gira sulla metrica che il video stesso demolisce

Il cuore argomentativo della VSL è che l'attribuzione Klaviyo non dimostra niente:

> "Klaviyo attribution basically is participation trophy at this point." (06:47)
> "If we can't prove we move the needle with real data, not Klaviyo attribution, you owe us nothing." (03:01)
> "It's not a guess. It's not attributed revenue." (09:07)

E le prove che porta, nello stesso video:

> "Stern Setups who got thirty one percent email **attributed** revenue" (01:15)
> "we've reached over twenty percent **attributed** revenue" (11:00)
> "from zero percent email revenue to over twenty five percent **attributable** revenue" (11:17)

Sulla landing, i sei casi before/after sono screenshot di dashboard Klaviyo, cioè la stessa metrica.

Il video smonta il metro e poi usa quel metro come prova. Non è una discrepanza tra due asset diversi, è dentro lo stesso script a sei minuti di distanza.

## L'assenza di criteri è venduta come semplicità

Al minuto 00:45:

> "There isn't some forty two page document with all these different criteria's you have to hit. It's just super simple and clear."

Nessun punto del video dice per quanto tempo gira lo split test, quale soglia conta come vittoria, o chi decide. "If we can't prove we move the needle" lascia la valutazione al venditore.

Su un brand da 100k$/mese, un holdout 50/50 sul tasso di riacquisto ha bisogno di mesi per dare un numero leggibile. Il video non lo affronta.

**Qui c'è la tua apertura più concreta.** Loro presentano l'assenza di criteri come chiarezza. Tu puoi avere un criterio che sta in un paragrafo: baseline netta X, soglia X più un euro, calcolata escludendo ordini manuali, rimborsi e cancellati, verificabile da entrambi ogni mese. Semplice come la loro, ma con un numero dentro. La semplicità senza criterio la puoi battere solo con la semplicità con criterio, non con un contratto da quarantadue pagine.

## Cosa nella struttura del video funziona e va preso

**L'offerta prima dell'identità.** Nei primi cinquantasette secondi ci stanno: offerta, inversione del rischio, meccanismo, cosa chiede in cambio. Il qualificatore arriva al minuto uno, le prime tre prove con nomi e numeri al minuto 1:08. Chi parla si presenta al **minuto 3:57**, quasi quattro minuti dentro.

La VSL italiana media fa il contrario e apre con "ciao, sono X e faccio Y da Z anni". Vale la pena testare questa apertura come quarta variante di hook, contro il controllo narrativo che ti ho scritto.

**Il bivio al minuto 3:05.** "Se ti convince, il bottone è sotto. Se sei ancora indeciso, resta e ti spiego perché funziona." Lascia andare chi è pronto a comprare senza costringerlo ad altri dodici minuti, e trattiene lo scettico dandogli un motivo. È replicabile a costo zero.

**Lo specchio dell'avatar al minuto 4:27.** "Provo a indovinare la situazione in cui sei: hai un carrello abbandonato, forse una welcome series, magari una o due post acquisto. L'ha impostato qualcuno a un certo punto e da allora gira così." Poi le frasi che i founder gli dicono in call, citate come le dicono loro. È esattamente l'uso che si può fare della tua banca voice-of-customer da 75 call, e tu quel materiale ce l'hai già.

**Le quattro obiezioni nominate ad alta voce.** "Se sei arrivato fin qui e non hai prenotato, è perché hai delle obiezioni. Te le dico io." Il permesso esplicito di dubitare abbassa la difesa prima di rispondere.

## Cosa nel video non funziona

Sedici minuti con l'offerta ripetuta per intero tre volte, al minuto zero, al 9:16 e al 14:49. La terza è ridondante.

Due analogie diverse per lo stesso identico punto: i tizi che girano il cartello davanti al ristorante (02:25) e l'insegna "aperto" (07:10). Una delle due basta.

L'inglese ha errori ("what your email is capable for", "we've just haven't been able"). Converte lo stesso, il che dice una cosa utile: la rifinitura linguistica non è la variabile che decide.

I due numeri portanti, 150 milioni e 200 brand, non hanno mai una fonte né un intervallo di date, né nel video né in pagina.

## Le quattro cose da fare, in ordine

1. **Dichiara il setup entro il primo minuto.** È il punto in cui li batti senza avere il loro track record. La frase da usare sta in `creative/offerta-mailift-copy.md`.
2. **Metti una soglia scritta.** Baseline netta, criterio in un paragrafo, verificabile da entrambi. Batte l'assenza di criteri venduta come chiarezza.
3. **Non usare mai revenue attribuita come prova.** Se attacchi il metro e poi lo usi, hai lo stesso buco loro. Le tue prove devono essere nette, con periodo e metodo dichiarati.
4. **Testa l'apertura con l'offerta al posto della storia,** come quarta variante nel test degli hook.
