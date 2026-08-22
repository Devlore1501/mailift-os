#!/usr/bin/env python3
"""
Crea 20 bozze di ads immagine su account ads-2 (act_674408036377203).
Struttura: 1 campagna PAUSED → 1 adset → 20 ads con immagini statiche.

Uso: python3 tools/create_ads2_drafts.py
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / ".secrets/mailift/.env")

ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
AD_ACCOUNT_ID = "act_2390793521074673"
PAGE_ID = "101236142286783"
DESTINATION_URL = "https://report.mailift.com"
IMAGES_DIR = Path("/Users/lorenzobaretta/Downloads/images (19)")
API_BASE = "https://graph.facebook.com/v21.0"

COPY = {
    "01_secchio_bucato": {
        "primary_text": "Il tuo eCommerce ha un problema che le ads non risolveranno mai.\n\nOgni euro che spendi in Meta porta traffico dentro. Ma senza una macchina di retention, quei clienti escono dalla porta sul retro.\n\nWelcome flow assente. Carrello abbandonato senza follow-up. Nessuna sequenza post-acquisto. Nessun win-back.\n\nScopri esattamente quanti soldi stai perdendo ogni mese. Analisi gratuita, risultati in 48h.",
        "headline": "Il tuo eCom è un secchio bucato?",
        "description": "Analisi gratuita per chi spende 15K+/mese",
        "cta": "LEARN_MORE",
    },
    "02_tassa_silenziosa": {
        "primary_text": "Ogni giorno che passa senza un sistema di retention è un giorno in cui paghi una tassa che non vedi nel bilancio.\n\n€1.200 al giorno di revenue che potrebbe venire da clienti già acquisiti — e invece vai a ricomprare gli stessi contatti con le ads.\n\nQuesto è il costo reale della dipendenza da Meta.\n\nSe spendi 15K+€/mese in ads, calcola quanto stai perdendo davvero →",
        "headline": "Stai pagando una tassa nascosta",
        "description": "Scopri quanto ti costa ogni giorno",
        "cta": "LEARN_MORE",
    },
    "03_matematica_brutale": {
        "primary_text": "Opinione impopolare: aumentare il budget ads non scala il tuo business.\n\n15.000€ in Meta + un solo acquisto per cliente = dipendenza totale dalla piattaforma.\n\nI brand che hanno scalato davvero in Italia nel 2024 non hanno raddoppiato il budget. Hanno costruito un sistema che fa tornare i clienti che avevano già.\n\nSe vuoi capire come applicarlo al tuo eCommerce, parti da qui →",
        "headline": "Più budget ≠ più scala",
        "description": "La matematica che nessuno ti dice",
        "cta": "LEARN_MORE",
    },
    "04_vincitore": {
        "primary_text": "C'è una differenza fondamentale tra chi fa numeri e chi costruisce un brand solido.\n\nChi dipende dalle ads ogni mese riparte da zero: nuovi clienti, nuovo budget, nuovo rischio.\n\nChi ha costruito un sistema di retention parte da una base di clienti che tornano — e usa le ads solo per crescere, non per sopravvivere.\n\nHai 15K+€/mese in ads e vuoi sapere come passare dalla prima alla seconda categoria? →",
        "headline": "I brand vincenti non ripartono da zero",
        "description": "Scopri il sistema che li differenzia",
        "cta": "LEARN_MORE",
    },
    "05_brand_vs_shop": {
        "primary_text": "342 nuovi clienti questo mese. Ma il 92% non ha mai ricomprato.\n\nSignifica che ogni vendita che fai dipende al 100% da nuovi investimenti in ads. Nessun effetto compounding. Nessuna base solida.\n\nI brand che scalano hanno percentuali di riacquisto sopra il 35%. Il gap tra il 8% e il 35% è dove si nasconde il fatturato che non stai vedendo.\n\nSe spendi 15K+€/mese in acquisizione, richiedi l'analisi gratuita e scopri il tuo potenziale reale →",
        "headline": "Le ads ti portano clienti. L'email li fa tornare.",
        "description": "Analisi gratuita per eCommerce 15K+",
        "cta": "LEARN_MORE",
    },
    "06_esperto_dilettante": {
        "primary_text": "Se controlli solo il ROAS, stai misurando la cosa sbagliata.\n\nIl ROAS ti dice quanto hai comprato oggi. Non ti dice quanto vale ogni cliente nel tempo.\n\nChi controlla ROAS → compra vendite, una alla volta, pagando Meta ogni volta.\nChi controlla LTV → costruisce asset: una lista di clienti che comprano di nuovo senza pagare l'algoritmo.\n\nSe spendi 15K+€/mese in Meta Ads e vuoi passare da \"media buyer\" a imprenditore, parti da qui →",
        "headline": "Se controlli solo il ROAS, non stai scalando",
        "description": "La metrica che separa chi scala da chi sopravvive",
        "cta": "LEARN_MORE",
    },
    "07_meta_in_pugno": {
        "primary_text": "Domanda scomoda: se domani Meta bloccasse il tuo account, quanto durerebbero le tue vendite?\n\n1 settimana? 3 giorni? 24 ore?\n\nPer molti eCommerce la risposta è: il fatturato si ferma quasi subito.\n\nLa lista email è l'unico asset che possiedi davvero. Non dipende dall'algoritmo, non può essere bloccata, non aumenta di prezzo ogni trimestre.\n\nSe spendi 15K+€/mese in ads, costruisci il canale che nessuno può toglierti →",
        "headline": "Meta ti ha in pugno?",
        "description": "Costruisci il canale che possiedi",
        "cta": "LEARN_MORE",
    },
    "08_meta_vs_email": {
        "primary_text": "Due canali. Due regole completamente diverse.\n\nMeta: ogni trimestre CPM sale, CAC sale, devi spendere di più per ottenere lo stesso risultato.\n\nEmail: la lista cresce, il costo di invio resta fisso, ogni campagna porta margin puro.\n\nPer ogni €1 speso in email su un eCommerce ottimizzato, il ritorno medio è tra 36€ e 45€. Non è un caso: è il traffico che hai già pagato che converte di nuovo, senza extra budget.\n\nCalcola il ROI nascosto nel tuo eCommerce →",
        "headline": "Meta aumenta i costi. La tua lista no.",
        "description": "Il canale che cresce senza CPM",
        "cta": "LEARN_MORE",
    },
    "09_virale_non_business": {
        "primary_text": "800.000 views sul Reel. Bellissimo.\n\nMa quanti di quei 800.000 hanno ricomprato? Quanti li hai nella tua lista? Quanti li puoi contattare domani senza pagare Meta?\n\nLe views sono in affitto. La lista è di proprietà.\n\nI brand che scalano in modo sostenibile trasformano ogni clic, ogni view, ogni visita in un contatto che possono raggiungere a costo marginale zero.\n\nSe spendi 15K+€/mese in acquisizione e vuoi costruire un asset vero →",
        "headline": "Un video virale non è un business",
        "description": "Le views spariscono. La lista resta.",
        "cta": "LEARN_MORE",
    },
    "10_lavorando_per_tiktok": {
        "primary_text": "Verità scomoda: ogni ora che passi a creare contenuti per TikTok o Instagram stai costruendo l'audience della piattaforma, non la tua.\n\nLoro tengono i dati. Loro decidono la reach. Loro cambiano l'algoritmo.\n\nLa tua lista email è l'unico database clienti che possiedi davvero. Ogni iscritto è un asset permanente che nessuna piattaforma può limitare.\n\nTrasforma l'attenzione che stai generando in contatti, riacquisti e valore misurabile →",
        "headline": "Stai costruendo il brand della piattaforma?",
        "description": "Trasforma attenzione in asset che possiedi",
        "cta": "LEARN_MORE",
    },
    "11_fondatore_solitario": {
        "primary_text": "Stai gestendo ads, ordini, logistica, supporto clienti e contenuti contemporaneamente.\n\nE la retention? Quasi sempre rimane in fondo alla lista.\n\nIl problema: senza un sistema automatizzato, ogni cliente che non torna è revenue persa che non recuperi mai più.\n\nUn sistema di email automation lavora 24/7 anche quando tu sei offline: recupera carrelli, genera riacquisti, riattiva clienti dormienti.\n\nPer i founder con 15K+€/mese in ads →",
        "headline": "Il tuo eCom non può dipendere dalle tue 12h/giorno",
        "description": "Automatizza la retention, libera il tuo tempo",
        "cta": "LEARN_MORE",
    },
    "12_loop_infinito": {
        "primary_text": "Ogni mese lo stesso loop: spendi in ads, vendi, il mese finisce, riparti da zero.\n\nNon c'è memoria. Non c'è compounding. Non c'è base.\n\nIl problema non è il budget — è che ogni cliente che non ritorna ti obbliga a pagare Meta una seconda volta per acquisirne uno nuovo.\n\nSpezza il ciclo. Calcola quanto fatturato stai perdendo ogni mese perché i tuoi clienti non tornano →",
        "headline": "Ogni mese compri da capo le stesse vendite",
        "description": "Spezza il loop con clienti che tornano",
        "cta": "LEARN_MORE",
    },
    "13_prima_dopo": {
        "primary_text": "Prima: ogni vendita che fai dipende da un nuovo click sulle ads. Nessuna automazione attiva. Ricavi volatili. Ogni mese si ricomincia.\n\nDopo: Welcome flow, Cart Abandonment, Post-Purchase e Win-Back attivi 24/7. I clienti tornano. I ricavi diventano più stabili e prevedibili.\n\nLa differenza tra i due scenari non è il budget. È avere o non avere il sistema.\n\nScopri quali automazioni mancano al tuo eCommerce →",
        "headline": "Prima compri ogni vendita. Dopo costruisci riacquisti.",
        "description": "Scopri le automazioni che mancano",
        "cta": "LEARN_MORE",
    },
    "14_numero_preciso": {
        "primary_text": "Hai già investito 15.000€ questo mese in Meta Ads.\n\nDomanda: sai esattamente quanto vale ogni cliente che hai acquisito dopo il primo ordine?\n\nSe non lo sai, stai ottimizzando per la metrica sbagliata. Chi conosce il proprio LTV può scalare le ads in modo sostenibile. Chi non lo sa brucia budget senza un tetto.\n\nCalcola il potenziale LTV reale del tuo eCommerce →",
        "headline": "Non è quanto spendi. È quanto vale ogni cliente dopo.",
        "description": "Calcola il tuo LTV reale",
        "cta": "LEARN_MORE",
    },
    "15_sconti_profitto": {
        "primary_text": "-10%. -20%. -30%.\n\nOgni volta che fai uno sconto per riportare un cliente, stai erodendo il margine che le ads ti hanno già costato.\n\nLa retention via email fa tornare i clienti senza che tu debba svendere ogni volta. Un'email ben scritta al momento giusto converte meglio di un coupon del 20%.\n\nSe spendi 15K+€/mese in ads e stai difendendo i margini con i denti, esiste un modo migliore →",
        "headline": "I tuoi sconti stanno uccidendo il profitto?",
        "description": "Retention che vende senza svendere",
        "cta": "LEARN_MORE",
    },
    "16_carrelli_fantasma": {
        "primary_text": "1.284 carrelli abbandonati questo mese.\n\nSe mandi una sola email, stai recuperando forse il 5-8% di quel valore. Una sequenza completa di 3-5 email arriva al 15-22%.\n\nLa differenza è già nel tuo database — non devi spendere un euro in più di ads.\n\nSe spendi 15K+€/mese in acquisizione e vuoi sapere quanto stai lasciando sul tavolo →",
        "headline": "Non hai un problema di traffico. Hai un problema di recupero.",
        "description": "Calcola le vendite recuperabili",
        "cta": "LEARN_MORE",
    },
    "17_welcome_flow": {
        "primary_text": "Stai pagando Meta per portare traffico. Ma se non hai un welcome flow, la maggior parte di quei lead scompaiono senza mai comprare.\n\nIl primo contatto decide tutto: se è vuoto, il lead passa alla concorrenza. Se è ben strutturato — benvenuto, social proof, prima offerta — si trasforma in cliente.\n\nPer ogni €15.000 in ads senza un welcome flow ottimizzato, stai bruciando almeno il 30-40% del potenziale.\n\nRichiedi l'audit gratuito del tuo sistema email →",
        "headline": "Il tuo welcome flow è un buco nero?",
        "description": "Il primo contatto decide se comprano",
        "cta": "LEARN_MORE",
    },
    "18_ltv_pozzo": {
        "primary_text": "Se i tuoi clienti comprano una sola volta, hai un problema strutturale che il budget ads non risolve.\n\nPerché? Perché senza LTV, ogni crescita richiede proporzionalmente più investimento in acquisizione. Non si scala — si corre sul posto.\n\nI brand che crescono in modo sostenibile hanno un 2° e 3° ordine automatizzato nel sistema.\n\nCalcola il tuo LTV reale e scopri quanto fatturato potresti sbloccare senza aumentare il budget →",
        "headline": "Il tuo LTV è un pozzo senza fondo?",
        "description": "Ogni riacquisto abbassa il tuo CAC effettivo",
        "cta": "LEARN_MORE",
    },
    "19_non_ho_tempo": {
        "primary_text": "\"Non ho tempo per l'email marketing.\"\n\nCapito. Ma il sistema che ti serve non richiede il tuo tempo per funzionare.\n\nWelcome, cart abandonment, post-purchase, win-back: una volta configurati, lavorano ogni giorno senza che tu debba toccarli. Recuperano revenue mentre tu gestisci il resto del brand.\n\nL'unica cosa che richiede il tuo tempo è decidere di farlo. Se spendi 15K+€/mese in ads, il ROI è immediato →",
        "headline": "Non hai tempo? È per questo che ti serve un sistema.",
        "description": "Automazioni che lavorano mentre tu no",
        "cta": "LEARN_MORE",
    },
    "20_klaviyo_non_basta": {
        "primary_text": "Hai già Klaviyo. Ma hai i flussi attivi?\n\nWelcome: ✗ | Carrello: ✗ | Post-acquisto: ✗ | Win-back: ✗\n\nKlaviyo è uno strumento. Il valore non viene dall'avere la piattaforma — viene dall'averla configurata in modo strategico con i flussi giusti, la segmentazione corretta e copy che converte.\n\nIl 70% degli eCommerce che usano Klaviyo non sfrutta più del 20% delle sue funzionalità.\n\nScopri cosa manca nel tuo setup →",
        "headline": "Hai Klaviyo ma non lo fai rendere?",
        "description": "Il valore è nei flussi, nei dati e nella strategia",
        "cta": "LEARN_MORE",
    },
}


def api_post(endpoint, data=None, files=None):
    url = f"{API_BASE}/{endpoint}"
    if files:
        resp = requests.post(url, data=data, files=files)
    else:
        params = data or {}
        params["access_token"] = ACCESS_TOKEN
        resp = requests.post(url, data=params)
    if resp.status_code != 200:
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json()


def api_get(endpoint, params=None):
    url = f"{API_BASE}/{endpoint}"
    p = params or {}
    p["access_token"] = ACCESS_TOKEN
    resp = requests.get(url, params=p)
    if resp.status_code != 200:
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json()


def upload_image(image_path):
    print(f"  Uploading image: {image_path.name}")
    with open(image_path, "rb") as f:
        result = api_post(
            f"{AD_ACCOUNT_ID}/adimages",
            data={"access_token": ACCESS_TOKEN},
            files={"filename": (image_path.name, f, "image/png")},
        )
    if result and "images" in result:
        images_data = result["images"]
        first_key = list(images_data.keys())[0]
        hash_val = images_data[first_key]["hash"]
        print(f"    ✓ Hash: {hash_val}")
        return hash_val
    print(f"    ✗ Upload failed: {result}")
    return None


def create_campaign():
    print("\n📋 Creazione campagna draft...")
    result = api_post(
        f"{AD_ACCOUNT_ID}/campaigns",
        {
            "name": "🎨 Immagini Statiche — Bozze Luglio 2026",
            "objective": "OUTCOME_LEADS",
            "status": "PAUSED",
            "special_ad_categories": "[]",
            "is_adset_budget_sharing_enabled": "false",
            "access_token": ACCESS_TOKEN,
        },
    )
    if result and "id" in result:
        cid = result["id"]
        print(f"  ✓ Campaign ID: {cid}")
        return cid
    print(f"  ✗ Fallita: {result}")
    return None


def create_adset(campaign_id):
    print("\n📦 Creazione adset draft...")
    targeting = json.dumps({
        "geo_locations": {"countries": ["IT"]},
        "age_min": 28,
        "age_max": 55,
        "targeting_automation": {"advantage_audience": 0},
    })
    result = api_post(
        f"{AD_ACCOUNT_ID}/adsets",
        {
            "name": "IT — eCommerce Owner — Broad",
            "campaign_id": campaign_id,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "LEAD_GENERATION",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "daily_budget": 1000,
            "targeting": targeting,
            "status": "PAUSED",
            "promoted_object": json.dumps({"page_id": PAGE_ID}),
            "dsa_beneficiary": "Mailift",
            "dsa_payor": "Mailift",
            "access_token": ACCESS_TOKEN,
        },
    )
    if result and "id" in result:
        aid = result["id"]
        print(f"  ✓ Adset ID: {aid}")
        return aid
    print(f"  ✗ Fallita: {result}")
    return None


def create_ad_creative(image_hash, copy_data, ad_name):
    object_story_spec = json.dumps({
        "page_id": PAGE_ID,
        "link_data": {
            "image_hash": image_hash,
            "link": DESTINATION_URL,
            "message": copy_data["primary_text"],
            "name": copy_data["headline"],
            "description": copy_data["description"],
            "call_to_action": {
                "type": copy_data["cta"],
                "value": {"link": DESTINATION_URL},
            },
        },
    })
    result = api_post(
        f"{AD_ACCOUNT_ID}/adcreatives",
        {
            "name": f"Creative — {ad_name}",
            "object_story_spec": object_story_spec,
            "access_token": ACCESS_TOKEN,
        },
    )
    if result and "id" in result:
        return result["id"]
    print(f"    ✗ Creative fallita: {result}")
    return None


def create_ad(adset_id, creative_id, ad_name):
    result = api_post(
        f"{AD_ACCOUNT_ID}/ads",
        {
            "name": ad_name,
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "PAUSED",
            "access_token": ACCESS_TOKEN,
        },
    )
    if result and "id" in result:
        return result["id"]
    print(f"    ✗ Ad fallita: {result}")
    return None


def main():
    if not ACCESS_TOKEN:
        print("ERROR: FB_ACCESS_TOKEN non trovato in .env")
        sys.exit(1)

    print(f"Account: {AD_ACCOUNT_ID}")
    print(f"Page: {PAGE_ID}")
    print(f"Immagini: {IMAGES_DIR}")

    # Step 1: Crea campagna
    campaign_id = create_campaign()
    if not campaign_id:
        sys.exit(1)

    # Step 2: Crea adset
    adset_id = create_adset(campaign_id)
    if not adset_id:
        sys.exit(1)

    # Step 3: Per ogni immagine — upload + creative + ad
    results = []
    images = sorted(IMAGES_DIR.glob("*.png"))
    print(f"\n🖼  Processo {len(images)} immagini...")

    for img_path in images:
        ad_key = img_path.stem  # es. "01_secchio_bucato"
        copy_data = COPY.get(ad_key)
        if not copy_data:
            print(f"  ⚠ Copy non trovato per {ad_key}, skip")
            continue

        print(f"\n[{ad_key}]")

        # Upload immagine
        image_hash = upload_image(img_path)
        if not image_hash:
            results.append({"name": ad_key, "status": "FAILED_IMAGE"})
            continue

        # Crea creative
        creative_id = create_ad_creative(image_hash, copy_data, ad_key)
        if not creative_id:
            results.append({"name": ad_key, "status": "FAILED_CREATIVE"})
            continue
        print(f"    ✓ Creative ID: {creative_id}")

        # Crea ad
        ad_id = create_ad(adset_id, creative_id, ad_key.replace("_", " ").title())
        if not ad_id:
            results.append({"name": ad_key, "status": "FAILED_AD"})
            continue
        print(f"    ✓ Ad ID: {ad_id}")
        results.append({"name": ad_key, "status": "OK", "ad_id": ad_id})

        time.sleep(0.5)  # rate limit courtesy

    # Riepilogo
    print("\n" + "=" * 60)
    print("RIEPILOGO")
    print("=" * 60)
    ok = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] != "OK"]
    print(f"✓ Creati:   {len(ok)}/20")
    if failed:
        print(f"✗ Falliti:  {len(failed)}")
        for f in failed:
            print(f"   - {f['name']}: {f['status']}")

    print(f"\nCampagna: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={AD_ACCOUNT_ID.replace('act_', '')}")
    print(f"Campaign ID: {campaign_id}")
    print(f"Adset ID: {adset_id}")

    # Salva risultati
    output_path = Path("/Users/lorenzobaretta/workflow ai/.tmp/ads2_draft_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "ads": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nRisultati salvati: {output_path}")


def complete_only():
    """Crea solo gli ad objects usando creative ID già salvati. Eseguire dopo aver aggiunto il metodo di pagamento su ads-2."""
    results_path = Path("/Users/lorenzobaretta/workflow ai/.tmp/ads2_draft_results.json")
    with open(results_path) as f:
        saved = json.load(f)

    adset_id = saved["adset_id"]
    creative_ids = saved["creative_ids"]

    print(f"Adset: {adset_id}")
    print(f"Creando {len(creative_ids)} ads...")
    created = []
    for ad_name, creative_id in creative_ids.items():
        ad_id = create_ad(adset_id, creative_id, ad_name.replace("_", " ").title())
        if ad_id:
            print(f"  ✓ {ad_name}: {ad_id}")
            created.append({"name": ad_name, "ad_id": ad_id})
        else:
            print(f"  ✗ {ad_name}")
        time.sleep(0.3)

    print(f"\nCreati: {len(created)}/{len(creative_ids)}")
    saved["ads_created"] = len(created)
    saved["ads"] = created
    saved["status"] = "COMPLETE" if len(created) == len(creative_ids) else "PARTIAL"
    with open(results_path, "w") as f:
        json.dump(saved, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    if "--complete-only" in sys.argv:
        complete_only()
    else:
        main()
