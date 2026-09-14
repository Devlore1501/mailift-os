"use client";

import { PageTitle } from "@/components/ui";

export default function PortalSupport() {
  return (
    <div className="max-w-2xl">
      <PageTitle title="Supporto" />
      <div className="card space-y-3 text-sm">
        <p>Per contestare un lead usa il pulsante "Richiedi sostituzione" nella scheda del lead: la richiesta viene valutata entro un giorno lavorativo e, se approvata, il credito torna disponibile sul pacchetto.</p>
        <p>Per rinnovi, modifiche al territorio servito o ai criteri di qualifica scrivi al tuo referente commerciale Lead on Demand.</p>
        <p>Registrare l'esito di ogni lead (contattato, appuntamento, preventivo, venduto, perso) rende affidabili le statistiche di ritorno che vedi nella sezione Statistiche.</p>
      </div>
    </div>
  );
}
