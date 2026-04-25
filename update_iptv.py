#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV M3U to HTML Updater
Aggiorna SOLO la porzione tra <div id="photos"> e </div> nei file index.html
"""

import os
import re
from pathlib import Path

# Mappatura group-title -> nome cartella
GROUP_TO_FOLDER = {
    "Digitale terrestre": "dtt",
    "News": "news",
    "Documentari": "doc",
    "Intrattenimento": "smile",
    "Musica": "music",
    "Esteri": "esteri",
    "Webcam": "webcam",
}

# Percorsi
REPO_ROOT = Path(__file__parent)
M3U_FILE = REPO_ROOT / "m3u" / "858it.m3u"

def parse_m3u(m3u_path):
    """
    Parsa il file M3U e restituisce un dizionario:
    {
        "group-title": [
            {
                "name": "Rai 1",
                "url": "https://...",
                "logo": "https://i.imgur.com/CAx7yRm.png",
                "group": "Digitale terrestre"
            },
            ...
        ]
    }
    """
    if not m3u_path.exists():
        print(f"❌ Errore: File {m3u_path} non trovato!")
        return {}
    
    with open(m3u_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    channels = {}
    current_channel = {}
    
    for line in lines:
        line = line.strip()
        
        # Riga EXTINF
        if line.startswith('#EXTINF:'):
            # Estrai group-title
            group_match = re.search(r'group-title="([^"]+)"', line)
            # Estrai tvg-logo
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            # Estrai nome (dopo l'ultima virgola)
            name_match = re.search(r',(.+?)$', line)
            
            if group_match and name_match:
                current_channel = {
                    'group': group_match.group(1),
                    'logo': logo_match.group(1) if logo_match else '',
                    'name': name_match.group(1).strip()
                }
        
        # Riga URL (non commento e non vuota)
        elif line and not line.startswith('#') and current_channel:
            current_channel['url'] = line
            
            # Aggiungi al dizionario
            group = current_channel['group']
            if group not in channels:
                channels[group] = []
            channels[group].append(current_channel.copy())
            
            # Resetta per il prossimo canale
            current_channel = {}
    
    return channels

def generate_html_links(channels_list):
    """
    Genera le righe HTML per i canali
    """
    html_links = []
    for ch in channels_list:
        # Gestisci caratteri speciali nel title
        title = ch['name'].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        html_links.append(f'<a href="{ch["url"]}"><img src="{ch["logo"]}" title="{title}" /></a>')
    
    return '\n        '.join(html_links)  # Indentazione di 8 spazi per allineamento

def update_index_html(folder_path, channels_list):
    """
    Aggiorna SOLO la porzione tra <div id="photos"> e </div> nel file index.html
    Tutto il resto del file rimane IDENTICO
    """
    index_file = folder_path / "index.html"
    
    if not index_file.exists():
        print(f"❌ Errore: {index_file} non trovato! Impossibile aggiornare.")
        return
    
    # Leggi il file esistente
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Genera nuovi link
    if channels_list:
        new_links = generate_html_links(channels_list)
    else:
        new_links = "<!-- Nessun canale -->"
    
    # Cerca esattamente <div id="photos"> e </div>
    # IMPORTANTE: preserva tutto ciò che sta fuori da questi tag
    pattern = r'(<div id="photos">)(.*?)(\s*</div>)'
    
    # Sostituisci SOLO il contenuto interno
    def replace_content(match):
        opening_tag = match.group(1)  # <div id="photos">
        closing_tag = match.group(3)  # </div>
        # Mantieni l'apertura e chiusura originali, sostituisci solo il contenuto
        return f'{opening_tag}\n        {new_links}\n    {closing_tag}'
    
    new_content = re.sub(pattern, replace_content, content, flags=re.DOTALL)
    
    # Verifica che la sostituzione sia avvenuta
    if new_content == content:
        # Fallback: cerca div con id="photos" anche con attributi aggiuntivi
        fallback_pattern = r'(<div[^>]*id="photos"[^>]*>)(.*?)(</div>)'
        new_content = re.sub(fallback_pattern, replace_content, content, flags=re.DOTALL)
        
        if new_content == content:
            print(f"⚠️  ATTENZIONE: non trovato <div id=\"photos\"> in {index_file}")
            return
    
    # Scrivi il file SOLO se ci sono modifiche effettive
    if new_content != content:
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Verifica rapida che il file non sia stato danneggiato
        if '</html>' not in new_content.lower():
            print(f"⚠️  DANNO POTENZIALE in {index_file}: restauro backup...")
            # Ripristina il contenuto originale
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"❌ Annullata modifica per {index_file} (struttura danneggiata)")
        else:
            print(f"✅ Aggiornato: {index_file} ({len(channels_list)} canali)")
    else:
        if channels_list:
            print(f"ℹ️  Nessuna modifica per: {index_file} ({len(channels_list)} canali)")
        else:
            print(f"ℹ️  Nessun canale per: {index_file} (preservato HTML esistente)")

def main():
    print("🚀 Avvio aggiornamento IPTV (SOLO sezione photos)...")
    print(f"📂 Repository root: {REPO_ROOT}")
    print(f"📄 File M3U: {M3U_FILE}")
    
    # Parsa il file M3U
    channels_by_group = parse_m3u(M3U_FILE)
    
    if not channels_by_group:
        print("❌ Nessun canale trovato nel file M3U!")
        return
    
    print(f"📺 Gruppi trovati: {list(channels_by_group.keys())}")
    
    # Aggiorna ogni gruppo mappato
    updated_count = 0
    for group_name, folder_name in GROUP_TO_FOLDER.items():
        folder_path = REPO_ROOT / folder_name
        
        # Verifica che la cartella esista
        if not folder_path.exists():
            print(f"⚠️  Cartella {folder_path} non trovata, skip...")
            continue
        
        # Verifica che index.html esista
        index_file = folder_path / "index.html"
        if not index_file.exists():
            print(f"⚠️  {index_file} non trovato, skip...")
            continue
        
        # Ottieni i canali per questo gruppo
        channels = channels_by_group.get(group_name, [])
        
        # Aggiorna l'HTML
        update_index_html(folder_path, channels)
        updated_count += 1
    
    # Report finale
    print("\n" + "="*50)
    print(f"✅ Aggiornamento completato!")
    print(f"📊 Statistiche:")
    for group_name, channels in channels_by_group.items():
        if group_name in GROUP_TO_FOLDER:
            print(f"   - {group_name}: {len(channels)} canali")
        else:
            print(f"   - {group_name}: {len(channels)} canali (NON mappato)")
    print("="*50)

if __name__ == "__main__":
    main()
