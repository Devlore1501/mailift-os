"""Catalogo di fonti consigliate per l'Idea Engine.

Tutte le voci sono feed RSS/Atom pubblici (il fetch rispetta ToS e rate limit,
NFR-06). Si aggiungono con un click da Impostazioni → Fonti; una fonte che
smette di funzionare mostra l'errore in tabella e si può disattivare.

Nota X/Twitter: X non espone RSS pubblici. Il tipo `twitter` è supportato via
bridge self-hosted o pubblico (Nitter, RSSHub) — aggiungere l'URL del bridge
come fonte manuale. Nessun default incluso per non seminare fonti rotte.
"""

CATALOG = [
    # --- Reddit (community eCommerce / email marketing) ---
    {"type": "reddit", "label": "r/ecommerce", "url": "https://www.reddit.com/r/ecommerce/.rss",
     "note": "Problemi reali degli owner: pricing, ads, retention"},
    {"type": "reddit", "label": "r/shopify", "url": "https://www.reddit.com/r/shopify/.rss",
     "note": "Novità e dolori quotidiani degli store Shopify"},
    {"type": "reddit", "label": "r/EmailMarketing", "url": "https://www.reddit.com/r/Emailmarketing/.rss",
     "note": "Discussioni deliverability, flussi, copy"},
    {"type": "reddit", "label": "r/klaviyo", "url": "https://www.reddit.com/r/klaviyo/.rss",
     "note": "Casi d'uso e problemi specifici Klaviyo"},
    {"type": "reddit", "label": "r/ecommercemarketing", "url": "https://www.reddit.com/r/ecommercemarketing/.rss",
     "note": "Marketing eCom a tutto tondo"},

    # --- Google News (query mirate, edizione IT) ---
    {"type": "news", "label": "Google News · email marketing",
     "url": "https://news.google.com/rss/search?q=email%20marketing&hl=it&gl=IT&ceid=IT:it",
     "note": "Notizie italiane sul settore email"},
    {"type": "news", "label": "Google News · eCommerce Italia",
     "url": "https://news.google.com/rss/search?q=ecommerce%20italia&hl=it&gl=IT&ceid=IT:it",
     "note": "Trend e dati eCommerce italiano"},
    {"type": "news", "label": "Google News · Shopify",
     "url": "https://news.google.com/rss/search?q=shopify&hl=it&gl=IT&ceid=IT:it",
     "note": "Novità piattaforma e casi store"},
    {"type": "news", "label": "Google News · Klaviyo",
     "url": "https://news.google.com/rss/search?q=klaviyo&hl=it&gl=IT&ceid=IT:it",
     "note": "Novità prodotto e pricing Klaviyo"},

    # --- Google Trends ---
    {"type": "trend", "label": "Google Trends · Italia (daily)",
     "url": "https://trends.google.com/trending/rss?geo=IT",
     "note": "Argomenti caldi del giorno in Italia — utile per hook contrarian"},

    # --- Blog di settore ---
    {"type": "blog", "label": "Shopify Blog (IT)", "url": "https://www.shopify.com/it/blog.atom",
     "note": "Guide e novità ufficiali Shopify"},
    {"type": "blog", "label": "Practical Ecommerce", "url": "https://www.practicalecommerce.com/feed",
     "note": "Tattiche eCom concrete (EN)"},
    {"type": "blog", "label": "Litmus Blog", "url": "https://www.litmus.com/blog/feed",
     "note": "Deliverability e design email (EN)"},
    {"type": "blog", "label": "Ninja Marketing", "url": "https://www.ninjamarketing.it/feed/",
     "note": "Marketing digitale in italiano"},
    {"type": "blog", "label": "Klaviyo Blog", "url": "https://www.klaviyo.com/blog/feed",
     "note": "Best practice e release Klaviyo (EN)"},
]
