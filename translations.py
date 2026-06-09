"""
translations.py — All bot messages in EN, IT, FR, ES.
"""

STRINGS = {
    "en": {
        # General
        "back_home":        "🏠 Home",
        "back":             "◀️ Back",
        "cancel":           "❌ Cancel",
        "confirm":          "✅ Confirm",

        # Registration
        "welcome":          "🌍 Welcome! Please choose your language:",
        "enter_username":   "👤 Please enter your Rolletto username to verify your account:",
        "verifying":        "🔄 Verifying...",
        "verified":         "✅ Welcome, {username}! You're now registered.",
        "not_found":        "❌ We couldn't find your Rolletto account.\n\nPlease sign up at Rolletto and use @rollettopromobot to get free spins and register in our system.\n\n👉 <a href=\"{url}\">Sign up here</a>\n\nOnce registered, use /check to try again.",
        "already_reg":      "✅ You are already registered. Use /start to go home.",

        # Home
        "home_title":       "🏆 <b>Rolletto Fantasy</b>\n\n{status}",
        "btn_squad":        "📋 My Squad",
        "btn_transfers":    "🔄 Transfers",
        "btn_confirm":      "✅ Confirm Squad",
        "btn_stats":        "📊 My Stats",
        "btn_results":      "🏟 Results",
        "btn_leaderboard":  "🏆 Leaderboard",
        "btn_rules":        "📖 Rules",

        # Squad
        "build_squad":      "⚽ <b>Squad Builder</b>\n\nChoose your formation:",
        "pick_formation":   "Choose formation:",
        "budget_left":      "💰 Budget remaining: {budget}",
        "pick_pos":         "Pick your <b>{pos}</b> ({n} remaining):",
        "squad_full":       "✅ Squad complete! Set your captain:",
        "pick_captain":     "⭐ Choose your captain (×2 points):",
        "captain_set":      "⭐ Captain: <b>{name}</b>",
        "squad_summary":    "📋 <b>Your Squad</b>\n\n{lineup}\n\n💰 Spent: {spent}\n⭐ Captain: {captain}",
        "no_captain":       "❌ You must set a captain before confirming.",
        "squad_confirmed":  "✅ <b>Squad confirmed!</b> Good luck! 🍀",
        "already_confirmed":"✅ Your squad is already confirmed for this gameweek.",
        "deadline_passed":  "❌ Confirmation deadline has passed. Your squad is locked.",
        "no_squad":         "❌ You don't have a squad yet. Go to 📋 My Squad to build one.",
        "over_budget":      "❌ Over budget! Remove a player first.",

        # Transfers
        "transfers_closed": "🔒 Transfer window is closed.",
        "transfers_open":   "🔓 Transfer window is open until {close}.",
        "free_transfers":   "Free transfers: {n}",
        "pick_remove":      "Select a player to remove:",
        "pick_add":         "Select replacement ({pos}):",
        "transfer_done":    "✅ Transfer complete: {out} → {in}",
        "extra_cost":       "⚠️ This transfer costs {pts} pts.",
        "no_transfers":     "❌ No transfers available.",

        # Stats
        "stats_title":      "📊 <b>My Stats</b>\n🏆 Total: <b>{total} pts</b>\n",
        "no_stats":         "No points yet. Play some gameweeks!",
        "player_detail":    "📊 <b>{name}</b> — {team}\n💰 {price} | Total: <b>{total} pts</b>\n",

        # Results
        "results_title":    "🏟 <b>Recent Results</b>",
        "no_results":       "No results yet.",

        # Leaderboard
        "lb_overall":       "🏆 <b>Overall Leaderboard</b>",
        "lb_gameweek":      "📅 <b>Round {n} Leaderboard</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 Overall",
        "lb_btn_gw":        "📅 This Round",

        # Rules
        "rules_title":      "📖 <b>Points System</b>",
        "rules_text": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>HOW TO PLAY</b>
━━━━━━━━━━━━━━━━━━━━

<b>Squad</b>
▸ Pick 15 players: 2 GK, 5 DEF, 5 MF, 3 FW
▸ Budget: €100m
▸ <b>Max 3 players from any single club</b>
▸ Choose a formation for your starting 11
▸ Bench: 4 substitutes (1 GK + 3 outfield)

<b>Captain</b>
▸ Must pick a captain before confirming
▸ Captain scores ×2 points
▸ No captain = cannot confirm

<b>Confirmation Deadline</b>
▸ Squad/captain/formation lock 1 hour before each round's first kickoff
▸ Unconfirmed squads score 0 points that round
▸ After deadline you cannot change the squad

<b>Sub Swaps</b>
▸ Allowed between kickoff windows (not during live matches)
▸ Locked from 1h before kickoff until all matches in that window finish
▸ Only swaps between starter and bench of same position

<b>Transfers</b>
▸ <b>1 free transfer per gameweek</b>
▸ Extra transfers cost -4 pts each
▸ Outside the transfer window = no transfers allowed
▸ After a transfer your squad is auto-confirmed with the new lineup

━━━━━━━━━━━━━━━━━━━━
⚽ <b>POINTS SYSTEM</b>
━━━━━━━━━━━━━━━━━━━━

<b>All Players:</b>
▸ Played (any): +1 pt
▸ Played 60+ min: +1 pt
▸ Assist: +3 pts
▸ Penalty earned: +2 pts
▸ Penalty conceded: -1 pt
▸ Penalty missed: -2 pts
▸ Yellow card: -1 pt
▸ Red card: -3 pts
▸ Yellow + Red: -4 pts
▸ Own goal: -2 pts
▸ <b>Defensive Contribution</b> (tackles+interceptions+blocks):
   • DEF: 10+ actions → +2 pts
   • MID/FW: 12+ actions → +2 pts
▸ <b>Player of the Match</b> (highest rating): +3 pts

<b>Goalkeeper:</b>
▸ Goal: +6 pts
▸ Penalty saved: +5 pts
▸ Clean sheet (60+ min): +4 pts
▸ Goals conceded per 2: -1 pt
▸ Saves per 3: +1 pt

<b>Defender:</b>
▸ Goal: +6 pts
▸ Clean sheet (60+ min): +4 pts
▸ Goals conceded per 2: -1 pt

<b>Midfielder:</b>
▸ Goal: +5 pts
▸ Clean sheet (60+ min): +1 pt

<b>Forward:</b>
▸ Goal: +4 pts

<b>Captain: ×2 all points</b>
▸ Only starting 11 score points (bench = 0)

━━━━━━━━━━━━━━━━━━━━
🏅 <b>LEADERBOARD</b>
━━━━━━━━━━━━━━━━━━━━

▸ Overall: total points across all rounds
▸ Per round: best score that round
▸ Usernames are partially hidden for privacy
""",

        "rules_text_wc": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>HOW TO PLAY</b>
━━━━━━━━━━━━━━━━━━━━

<b>Squad</b>
▸ Pick 15 players: 2 GK, 5 DEF, 5 MF, 3 FW
▸ Budget: $100m
▸ <b>Max players from one nation:</b>
   • Group stage: 3
   • Round of 16: 4
   • Quarter-finals: 5
   • Semi-finals: 6
   • Final: 8
▸ Choose a formation for your starting 11
▸ Bench: 4 substitutes (1 GK + 3 outfield)

<b>Captain</b>
▸ Must pick a captain before confirming
▸ Captain scores ×2 points
▸ No captain = cannot confirm

<b>Confirmation Deadline</b>
▸ Squad/captain/formation lock 1 hour before each matchday's first kickoff
▸ Unconfirmed squads score 0 points that matchday
▸ After deadline you cannot change the squad

<b>Sub Swaps</b>
▸ Allowed between kickoff windows (not during live matches)
▸ Locked from 1h before kickoff until all matches in that window finish
▸ Only swaps between starter and bench of same position

<b>Transfers (per matchday)</b>
▸ Matchday 1: unlimited free transfers
▸ Matchday 2: 2 free
▸ Matchday 3: 2 free
▸ Round of 16: unlimited free transfers
▸ Quarter-finals: 4 free
▸ Semi-finals: 5 free
▸ Final: 6 free
▸ Extra transfers cost -3 pts each
▸ After a transfer your squad is auto-confirmed with the new lineup

<b>Eliminated Teams</b>
▸ When a nation is knocked out, its players disappear from the picker
▸ Players already in your squad stay but score 0 — transfer them out

━━━━━━━━━━━━━━━━━━━━
⚽ <b>POINTS SYSTEM</b>
━━━━━━━━━━━━━━━━━━━━

<b>All Players:</b>
▸ Played (any): +1 pt
▸ Played 60+ min: +1 pt
▸ Assist: +3 pts
▸ Penalty earned: +2 pts
▸ Penalty conceded: -1 pt
▸ Penalty missed: -2 pts
▸ Yellow card: -1 pt
▸ Red card: -3 pts
▸ Yellow + Red: -4 pts
▸ Own goal: -2 pts
▸ <b>Defensive Contribution</b> (tackles+interceptions+blocks):
   • DEF: 10+ actions → +2 pts
   • MID/FW: 12+ actions → +2 pts
▸ <b>Player of the Match</b> (highest rating): +3 pts

<b>Goalkeeper:</b>
▸ Goal: +6 pts
▸ Penalty saved: +5 pts
▸ Clean sheet (60+ min): +4 pts
▸ Goals conceded per 2: -1 pt
▸ Saves per 3: +1 pt

<b>Defender:</b>
▸ Goal: +6 pts
▸ Clean sheet (60+ min): +4 pts
▸ Goals conceded per 2: -1 pt

<b>Midfielder:</b>
▸ Goal: +5 pts
▸ Clean sheet (60+ min): +1 pt

<b>Forward:</b>
▸ Goal: +4 pts

<b>Captain: ×2 all points</b>
▸ Only starting 11 score points (bench = 0)

━━━━━━━━━━━━━━━━━━━━
💰 <b>PRIZE POOL — TOP 30</b>
━━━━━━━━━━━━━━━━━━━━

🥇 1st: $500
🥈 2nd: $300
🥉 3rd: $200
🏅 4th: $50
🏅 5th: $50
🎖 6th–10th: $30 each
🎖 11th–20th: $15 each
🎖 21st–30th: $10 each

<i>Total prize pool: $1,500</i>

━━━━━━━━━━━━━━━━━━━━
🏅 <b>LEADERBOARD</b>
━━━━━━━━━━━━━━━━━━━━

▸ Overall: total points across all matchdays
▸ Per matchday: best score that matchday
▸ Usernames are partially hidden for privacy
""",

        # Notifications
        "notif_deadline_24h": "⏰ <b>24 hours left!</b>\nConfirm your squad before the deadline:\n{deadline}",
        "notif_deadline_1h":  "🚨 <b>1 hour left!</b>\nConfirm your squad NOW:\n{deadline}",
        "notif_window_open":  "🔓 <b>Transfer window is open!</b>\nMake your transfers before {close}",
        "notif_window_close": "🔒 <b>Transfer window has closed.</b>",
        "notif_result":       "⚽ <b>Match Result</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 Points updated! Tap 📊 Stats to see your score.",
        "notif_gw_summary":   "📊 <b>Gameweek {n} finished!</b>\nYour score: <b>{pts} pts</b>\nTap 🏆 Leaderboard to see rankings.",
        "btn_swap_subs": "🔁 Swap Subs",
        "btn_randomise": "🎲 Randomise",
        "rnd_building": "🎲 Building a random squad…",
        "rnd_failed": "Couldn't build a random squad within budget. Try again.",
        "swap_pick_sub": "🔁 <b>Select sub to swap:</b>",
        "swap_pick_target": "🔁 Swap <b>{name}</b> with:",
        "swap_confirm_prompt": "🔁 <b>Confirm Swap</b>\n\nSwap <b>{out}</b> ↔️ <b>{in_}</b>?",
        "swap_done": "✅ Swap confirmed! <b>{out}</b> ↔️ <b>{in_}</b>",
        "captain_moved": "⭐ Your captain was transferred out, so the armband moved to <b>{name}</b>. Change it any time before the deadline.",
        "swap_deadline_passed": "⏰ Swap deadline has passed.",
        "swap_no_subs": "You have no substitutes to swap.",
    },
    "it": {
        "back_home":        "🏠 Home",
        "back":             "◀️ Indietro",
        "cancel":           "❌ Annulla",
        "confirm":          "✅ Conferma",
        "welcome":          "🌍 Benvenuto! Scegli la tua lingua:",
        "enter_username":   "👤 Inserisci il tuo nome utente Rolletto:",
        "verifying":        "🔄 Verifica in corso...",
        "verified":         "✅ Benvenuto, {username}! Sei registrato.",
        "not_found":        "❌ Non abbiamo trovato il tuo account Rolletto.\n\nRegistrati su Rolletto e usa @rollettopromobot per ottenere giri gratuiti e registrarti nel nostro sistema.\n\n👉 <a href=\"{url}\">Registrati qui</a>\n\nUna volta registrato, usa /check per riprovare.",
        "already_reg":      "✅ Sei già registrato.",
        "home_title":       "🏆 <b>Rolletto Fantasy</b>\n\n{status}",
        "btn_squad":        "📋 La Mia Squadra",
        "btn_transfers":    "🔄 Trasferimenti",
        "btn_confirm":      "✅ Conferma Squadra",
        "btn_stats":        "📊 Le Mie Statistiche",
        "btn_results":      "🏟 Risultati",
        "btn_leaderboard":  "🏆 Classifica",
        "btn_rules":        "📖 Regole",
        "build_squad":      "⚽ <b>Crea Squadra</b>\n\nScegli il tuo modulo:",
        "pick_formation":   "Scegli modulo:",
        "budget_left":      "💰 Budget rimanente: {budget}",
        "pick_pos":         "Scegli il tuo <b>{pos}</b> ({n} rimasti):",
        "squad_full":       "✅ Squadra completa! Scegli il capitano:",
        "pick_captain":     "⭐ Scegli il capitano (×2 punti):",
        "captain_set":      "⭐ Capitano: <b>{name}</b>",
        "squad_confirmed":  "✅ <b>Squadra confermata!</b> Buona fortuna! 🍀",
        "deadline_passed":  "❌ Scadenza passata.",
        "no_squad":         "❌ Non hai ancora una squadra.",
        "transfers_closed": "🔒 Finestra trasferimenti chiusa.",
        "transfers_open":   "🔓 Finestra trasferimenti aperta fino a {close}.",
        "free_transfers":   "Trasferimenti gratuiti: {n}",
        "transfer_done":    "✅ Trasferimento: {out} → {in}",
        "stats_title":      "📊 <b>Le Mie Statistiche</b>\n🏆 Totale: <b>{total} pts</b>\n",
        "results_title":    "🏟 <b>Risultati Recenti</b>",
        "lb_overall":       "🏆 <b>Classifica Generale</b>",
        "lb_gameweek":      "📅 <b>Round {n} Classifica</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 Generale",
        "lb_btn_gw":        "📅 Questo Round",
        "rules_title":      "📖 <b>Sistema Punteggi</b>",
        "rules_text": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>COME GIOCARE</b>
━━━━━━━━━━━━━━━━━━━━

<b>Rosa</b>
▸ Scegli 15 giocatori: 2 POR, 5 DIF, 5 CEN, 3 ATT
▸ Budget: €100M
▸ <b>Max 3 giocatori per club</b>
▸ Scegli una formazione per i tuoi 11 titolari
▸ Panchina: 4 sostituti (1 POR + 3 di movimento)

<b>Capitano</b>
▸ Devi scegliere un capitano prima di confermare
▸ Il capitano segna ×2 punti
▸ Senza capitano non puoi confermare

<b>Deadline di conferma</b>
▸ Rosa/capitano/formazione si bloccano 1 ora prima del primo calcio d'inizio
▸ Rosa non confermata = 0 punti per il round
▸ Dopo la deadline non puoi più modificare la rosa

<b>Cambi panchina</b>
▸ Consentiti tra una finestra di partite e l'altra (non durante partite in corso)
▸ Bloccati 1h prima del calcio d'inizio fino al termine di tutte le partite di quella finestra
▸ Solo scambi titolare/panchina dello stesso ruolo

<b>Trasferimenti</b>
▸ <b>1 trasferimento gratuito a giornata</b>
▸ Trasferimenti extra costano -4 punti ciascuno
▸ Fuori dalla finestra trasferimenti = nessun trasferimento
▸ Dopo un trasferimento la rosa si riconferma automaticamente

━━━━━━━━━━━━━━━━━━━━
⚽ <b>SISTEMA PUNTI</b>
━━━━━━━━━━━━━━━━━━━━

<b>Tutti i giocatori:</b>
▸ Giocato (qualsiasi): +1
▸ Giocato 60+ min: +1
▸ Assist: +3
▸ Rigore conquistato: +2
▸ Rigore concesso: -1
▸ Rigore sbagliato: -2
▸ Cartellino giallo: -1
▸ Cartellino rosso: -3
▸ Giallo + Rosso: -4
▸ Autogol: -2
▸ <b>Contributo difensivo</b> (contrasti+intercetti+blocchi):
   • DIF: 10+ azioni → +2
   • CEN/ATT: 12+ azioni → +2
▸ <b>Migliore in campo</b> (rating più alto): +3

<b>Portiere:</b>
▸ Gol: +6 ▸ Rigore parato: +5
▸ Porta inviolata (60+ min): +4
▸ Gol subiti ogni 2: -1
▸ Parate ogni 3: +1

<b>Difensore:</b>
▸ Gol: +6 ▸ Porta inviolata (60+ min): +4
▸ Gol subiti ogni 2: -1

<b>Centrocampista:</b>
▸ Gol: +5 ▸ Porta inviolata (60+ min): +1

<b>Attaccante:</b>
▸ Gol: +4

<b>Capitano: ×2 punti</b>
▸ Solo gli 11 titolari segnano punti (panchina = 0)

━━━━━━━━━━━━━━━━━━━━
🏅 <b>CLASSIFICA</b>
━━━━━━━━━━━━━━━━━━━━

▸ Generale: punti totali in tutti i round
▸ Per round: miglior punteggio di quel round
▸ I nomi utente sono parzialmente nascosti per privacy
""",

        "rules_text_wc": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>COME GIOCARE</b>
━━━━━━━━━━━━━━━━━━━━

<b>Rosa</b>
▸ Scegli 15 giocatori: 2 POR, 5 DIF, 5 CEN, 3 ATT
▸ Budget: $100M
▸ <b>Max giocatori per nazionale:</b>
   • Fase a gironi: 3
   • Ottavi: 4
   • Quarti: 5
   • Semifinali: 6
   • Finale: 8
▸ Scegli una formazione per i tuoi 11 titolari
▸ Panchina: 4 sostituti (1 POR + 3 di movimento)

<b>Capitano</b>
▸ Devi scegliere un capitano prima di confermare
▸ Il capitano segna ×2 punti
▸ Senza capitano non puoi confermare

<b>Deadline di conferma</b>
▸ Rosa/capitano/formazione si bloccano 1 ora prima del primo calcio d'inizio della giornata
▸ Rosa non confermata = 0 punti per la giornata
▸ Dopo la deadline non puoi più modificare la rosa

<b>Cambi panchina</b>
▸ Consentiti tra una finestra di partite e l'altra (non durante partite in corso)
▸ Bloccati 1h prima del calcio d'inizio fino al termine di tutte le partite di quella finestra
▸ Solo scambi titolare/panchina dello stesso ruolo

<b>Trasferimenti (per giornata)</b>
▸ Giornata 1: trasferimenti illimitati gratis
▸ Giornata 2: 2 gratis
▸ Giornata 3: 2 gratis
▸ Ottavi: trasferimenti illimitati gratis
▸ Quarti: 4 gratis
▸ Semifinali: 5 gratis
▸ Finale: 6 gratis
▸ Trasferimenti extra costano -3 punti ciascuno
▸ Dopo un trasferimento la rosa si riconferma automaticamente

<b>Squadre eliminate</b>
▸ Quando una nazionale è eliminata, i suoi giocatori spariscono dalla selezione
▸ I giocatori già in rosa restano ma segnano 0 — cedili

━━━━━━━━━━━━━━━━━━━━
⚽ <b>SISTEMA PUNTI</b>
━━━━━━━━━━━━━━━━━━━━

<b>Tutti i giocatori:</b>
▸ Giocato (qualsiasi): +1
▸ Giocato 60+ min: +1
▸ Assist: +3
▸ Rigore conquistato: +2
▸ Rigore concesso: -1
▸ Rigore sbagliato: -2
▸ Cartellino giallo: -1
▸ Cartellino rosso: -3
▸ Giallo + Rosso: -4
▸ Autogol: -2
▸ <b>Contributo difensivo</b> (contrasti+intercetti+blocchi):
   • DIF: 10+ azioni → +2
   • CEN/ATT: 12+ azioni → +2
▸ <b>Migliore in campo</b> (rating più alto): +3

<b>Portiere:</b>
▸ Gol: +6 ▸ Rigore parato: +5
▸ Porta inviolata (60+ min): +4
▸ Gol subiti ogni 2: -1
▸ Parate ogni 3: +1

<b>Difensore:</b>
▸ Gol: +6 ▸ Porta inviolata (60+ min): +4
▸ Gol subiti ogni 2: -1

<b>Centrocampista:</b>
▸ Gol: +5 ▸ Porta inviolata (60+ min): +1

<b>Attaccante:</b>
▸ Gol: +4

<b>Capitano: ×2 punti</b>
▸ Solo gli 11 titolari segnano punti (panchina = 0)

━━━━━━━━━━━━━━━━━━━━
💰 <b>MONTEPREMI — TOP 30</b>
━━━━━━━━━━━━━━━━━━━━

🥇 1°: $500
🥈 2°: $300
🥉 3°: $200
🏅 4°: $50
🏅 5°: $50
🎖 6°–10°: $30 ciascuno
🎖 11°–20°: $15 ciascuno
🎖 21°–30°: $10 ciascuno

<i>Montepremi totale: $1.500</i>

━━━━━━━━━━━━━━━━━━━━
🏅 <b>CLASSIFICA</b>
━━━━━━━━━━━━━━━━━━━━

▸ Generale: punti totali in tutte le giornate
▸ Per giornata: miglior punteggio di quella giornata
▸ I nomi utente sono parzialmente nascosti per privacy
""",
        "notif_result":     "⚽ <b>Risultato</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 Punti aggiornati!",
        "notif_gw_summary": "📊 <b>Giornata {n} finita!</b>\nI tuoi punti: <b>{pts}</b>",
        "btn_swap_subs": "🔁 Cambia Riserve",
        "btn_randomise": "🎲 Casuale",
        "rnd_building": "🎲 Creazione squadra casuale…",
        "rnd_failed": "Impossibile creare una squadra entro il budget. Riprova.",
        "swap_pick_sub": "🔁 <b>Seleziona riserva da cambiare:</b>",
        "swap_pick_target": "🔁 Cambia <b>{name}</b> con:",
        "swap_confirm_prompt": "🔁 <b>Conferma Cambio</b>\n\nCambia <b>{out}</b> ↔️ <b>{in_}</b>?",
        "swap_done": "✅ Cambio confermato! <b>{out}</b> ↔️ <b>{in_}</b>",
        "captain_moved": "⭐ Il tuo capitano è stato ceduto, quindi la fascia è passata a <b>{name}</b>. Puoi cambiarla prima della scadenza.",
        "swap_deadline_passed": "⏰ Termine cambi scaduto.",
        "swap_no_subs": "Nessuna riserva disponibile.",
        "notif_deadline_24h":"⏰ <b>24 ore rimaste!</b>\nConferma la squadra: {deadline}",
        "notif_deadline_1h": "🚨 <b>1 ora rimasta!</b>\nConferma ORA: {deadline}",
        "notif_window_open": "🔓 <b>Finestra aperta!</b>\nFai i trasferimenti prima di {close}",
        "notif_window_close":"🔒 <b>Finestra chiusa.</b>",
        "no_captain":       "❌ Devi impostare un capitano.",
        "over_budget":      "❌ Budget superato!",
        "no_stats":         "Nessun punto ancora.",
        "no_results":       "Nessun risultato.",
        "already_confirmed":"✅ Squadra già confermata.",
        "squad_summary":    "📋 <b>La Tua Squadra</b>\n\n{lineup}\n\n💰 Speso: {spent}\n⭐ Capitano: {captain}",
        "pick_remove":      "Seleziona giocatore da rimuovere:",
        "pick_add":         "Seleziona sostituto ({pos}):",
        "extra_cost":       "⚠️ Questo trasferimento costa {pts} pts.",
        "no_transfers":     "❌ Nessun trasferimento disponibile.",
        "player_detail":    "📊 <b>{name}</b> — {team}\n💰 {price} | Totale: <b>{total} pts</b>\n",
        "lb_btn_gw":        "📅 Questo Round",
    },
    "fr": {
        "back_home":        "🏠 Accueil",
        "back":             "◀️ Retour",
        "cancel":           "❌ Annuler",
        "confirm":          "✅ Confirmer",
        "welcome":          "🌍 Bienvenue! Choisissez votre langue:",
        "enter_username":   "👤 Entrez votre nom d'utilisateur Rolletto:",
        "verifying":        "🔄 Vérification...",
        "verified":         "✅ Bienvenue, {username}! Vous êtes inscrit.",
        "not_found":        "❌ Nous n'avons pas trouvé votre compte Rolletto.\n\nInscrivez-vous sur Rolletto et utilisez @rollettopromobot pour obtenir des tours gratuits et vous enregistrer.\n\n👉 <a href=\"{url}\">S'inscrire ici</a>\n\nUne fois inscrit, utilisez /check pour réessayer.",
        "already_reg":      "✅ Vous êtes déjà inscrit.",
        "home_title":       "🏆 <b>Rolletto Fantasy</b>\n\n{status}",
        "btn_squad":        "📋 Mon Équipe",
        "btn_transfers":    "🔄 Transferts",
        "btn_confirm":      "✅ Confirmer Équipe",
        "btn_stats":        "📊 Mes Stats",
        "btn_results":      "🏟 Résultats",
        "btn_leaderboard":  "🏆 Classement",
        "btn_rules":        "📖 Règles",
        "build_squad":      "⚽ <b>Créer Équipe</b>\n\nChoisissez votre formation:",
        "pick_formation":   "Choisir formation:",
        "budget_left":      "💰 Budget restant: {budget}",
        "pick_pos":         "Choisissez votre <b>{pos}</b> ({n} restants):",
        "squad_full":       "✅ Équipe complète! Choisissez le capitaine:",
        "pick_captain":     "⭐ Choisissez le capitaine (×2 points):",
        "captain_set":      "⭐ Capitaine: <b>{name}</b>",
        "squad_confirmed":  "✅ <b>Équipe confirmée!</b> Bonne chance! 🍀",
        "deadline_passed":  "❌ Date limite dépassée.",
        "no_squad":         "❌ Vous n'avez pas encore d'équipe.",
        "transfers_closed": "🔒 Fenêtre de transferts fermée.",
        "transfers_open":   "🔓 Fenêtre ouverte jusqu'à {close}.",
        "free_transfers":   "Transferts gratuits: {n}",
        "transfer_done":    "✅ Transfert: {out} → {in}",
        "stats_title":      "📊 <b>Mes Stats</b>\n🏆 Total: <b>{total} pts</b>\n",
        "results_title":    "🏟 <b>Résultats Récents</b>",
        "lb_overall":       "🏆 <b>Classement Général</b>",
        "lb_gameweek":      "📅 <b>Round {n} Classement</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 Général",
        "lb_btn_gw":        "📅 Ce Round",
        "rules_title":      "📖 <b>Système de Points</b>",
        "rules_text": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>COMMENT JOUER</b>
━━━━━━━━━━━━━━━━━━━━

<b>Effectif</b>
▸ Choisis 15 joueurs : 2 GB, 5 DEF, 5 MIL, 3 ATT
▸ Budget : 100M €
▸ <b>Max 3 joueurs par club</b>
▸ Choisis une formation pour ton 11 de départ
▸ Banc : 4 remplaçants (1 GB + 3 de champ)

<b>Capitaine</b>
▸ Tu dois choisir un capitaine avant de confirmer
▸ Le capitaine marque ×2 points
▸ Pas de capitaine = pas de confirmation

<b>Deadline de confirmation</b>
▸ Équipe/capitaine/formation verrouillés 1h avant le premier coup d'envoi
▸ Équipe non confirmée = 0 point ce round
▸ Après la deadline, tu ne peux plus modifier l'équipe

<b>Échanges de remplaçants</b>
▸ Autorisés entre les fenêtres de matchs (pas pendant les matchs en direct)
▸ Verrouillés 1h avant le coup d'envoi jusqu'à la fin de tous les matchs de cette fenêtre
▸ Uniquement entre titulaire et remplaçant du même poste

<b>Transferts</b>
▸ <b>1 transfert gratuit par journée</b>
▸ Transferts supplémentaires : -4 points chacun
▸ Hors fenêtre de transferts = aucun transfert
▸ Après un transfert, l'équipe est reconfirmée automatiquement

━━━━━━━━━━━━━━━━━━━━
⚽ <b>SYSTÈME DE POINTS</b>
━━━━━━━━━━━━━━━━━━━━

<b>Tous les joueurs :</b>
▸ A joué (quelconque) : +1
▸ A joué 60+ min : +1
▸ Passe décisive : +3
▸ Pénalty obtenu : +2
▸ Pénalty concédé : -1
▸ Pénalty raté : -2
▸ Carton jaune : -1
▸ Carton rouge : -3
▸ Jaune + Rouge : -4
▸ But contre son camp : -2
▸ <b>Contribution défensive</b> (tacles+interceptions+blocs) :
   • DEF : 10+ actions → +2
   • MIL/ATT : 12+ actions → +2
▸ <b>Homme du match</b> (note la plus haute) : +3

<b>Gardien :</b>
▸ But : +6 ▸ Pénalty arrêté : +5
▸ Clean sheet (60+ min) : +4
▸ Buts encaissés tous les 2 : -1
▸ Arrêts tous les 3 : +1

<b>Défenseur :</b>
▸ But : +6 ▸ Clean sheet (60+ min) : +4
▸ Buts encaissés tous les 2 : -1

<b>Milieu :</b>
▸ But : +5 ▸ Clean sheet (60+ min) : +1

<b>Attaquant :</b>
▸ But : +4

<b>Capitaine : ×2 tous les points</b>
▸ Seul le 11 titulaire marque (banc = 0)

━━━━━━━━━━━━━━━━━━━━
🏅 <b>CLASSEMENT</b>
━━━━━━━━━━━━━━━━━━━━

▸ Général : total des points sur tous les rounds
▸ Par round : meilleur score du round
▸ Les noms d'utilisateur sont partiellement masqués
""",

        "rules_text_wc": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>COMMENT JOUER</b>
━━━━━━━━━━━━━━━━━━━━

<b>Effectif</b>
▸ Choisis 15 joueurs : 2 GB, 5 DEF, 5 MIL, 3 ATT
▸ Budget : 100M $
▸ <b>Max joueurs d'une même nation :</b>
   • Phase de groupes : 3
   • Huitièmes : 4
   • Quarts : 5
   • Demi-finales : 6
   • Finale : 8
▸ Choisis une formation pour ton 11 de départ
▸ Banc : 4 remplaçants (1 GB + 3 de champ)

<b>Capitaine</b>
▸ Tu dois choisir un capitaine avant de confirmer
▸ Le capitaine marque ×2 points
▸ Pas de capitaine = pas de confirmation

<b>Deadline de confirmation</b>
▸ Équipe/capitaine/formation verrouillés 1h avant le premier coup d'envoi de la journée
▸ Équipe non confirmée = 0 point cette journée
▸ Après la deadline, tu ne peux plus modifier l'équipe

<b>Échanges de remplaçants</b>
▸ Autorisés entre les fenêtres de matchs (pas pendant les matchs en direct)
▸ Verrouillés 1h avant le coup d'envoi jusqu'à la fin de tous les matchs de cette fenêtre
▸ Uniquement entre titulaire et remplaçant du même poste

<b>Transferts (par journée)</b>
▸ Journée 1 : transferts gratuits illimités
▸ Journée 2 : 2 gratuits
▸ Journée 3 : 2 gratuits
▸ Huitièmes : transferts gratuits illimités
▸ Quarts : 4 gratuits
▸ Demi-finales : 5 gratuits
▸ Finale : 6 gratuits
▸ Transferts supplémentaires : -3 points chacun
▸ Après un transfert, l'équipe est reconfirmée automatiquement

<b>Équipes éliminées</b>
▸ Quand une nation est éliminée, ses joueurs disparaissent de la sélection
▸ Les joueurs déjà dans ton équipe restent mais marquent 0 — transfère-les

━━━━━━━━━━━━━━━━━━━━
⚽ <b>SYSTÈME DE POINTS</b>
━━━━━━━━━━━━━━━━━━━━

<b>Tous les joueurs :</b>
▸ A joué (quelconque) : +1
▸ A joué 60+ min : +1
▸ Passe décisive : +3
▸ Pénalty obtenu : +2
▸ Pénalty concédé : -1
▸ Pénalty raté : -2
▸ Carton jaune : -1
▸ Carton rouge : -3
▸ Jaune + Rouge : -4
▸ But contre son camp : -2
▸ <b>Contribution défensive</b> (tacles+interceptions+blocs) :
   • DEF : 10+ actions → +2
   • MIL/ATT : 12+ actions → +2
▸ <b>Homme du match</b> (note la plus haute) : +3

<b>Gardien :</b>
▸ But : +6 ▸ Pénalty arrêté : +5
▸ Clean sheet (60+ min) : +4
▸ Buts encaissés tous les 2 : -1
▸ Arrêts tous les 3 : +1

<b>Défenseur :</b>
▸ But : +6 ▸ Clean sheet (60+ min) : +4
▸ Buts encaissés tous les 2 : -1

<b>Milieu :</b>
▸ But : +5 ▸ Clean sheet (60+ min) : +1

<b>Attaquant :</b>
▸ But : +4

<b>Capitaine : ×2 tous les points</b>
▸ Seul le 11 titulaire marque (banc = 0)

━━━━━━━━━━━━━━━━━━━━
💰 <b>CAGNOTTE — TOP 30</b>
━━━━━━━━━━━━━━━━━━━━

🥇 1er : $500
🥈 2e : $300
🥉 3e : $200
🏅 4e : $50
🏅 5e : $50
🎖 6e–10e : $30 chacun
🎖 11e–20e : $15 chacun
🎖 21e–30e : $10 chacun

<i>Cagnotte totale : $1 500</i>

━━━━━━━━━━━━━━━━━━━━
🏅 <b>CLASSEMENT</b>
━━━━━━━━━━━━━━━━━━━━

▸ Général : total des points sur toutes les journées
▸ Par journée : meilleur score de la journée
▸ Les noms d'utilisateur sont partiellement masqués
""",
        "notif_result":     "⚽ <b>Résultat</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 Points mis à jour!",
        "notif_gw_summary": "📊 <b>Journée {n} terminée!</b>\nVos points: <b>{pts}</b>",
        "btn_swap_subs": "🔁 Changer Remplacants",
        "btn_randomise": "🎲 Aléatoire",
        "rnd_building": "🎲 Création d'une équipe aléatoire…",
        "rnd_failed": "Impossible de créer une équipe dans le budget. Réessaie.",
        "swap_pick_sub": "🔁 <b>Selectionnez le remplacant:</b>",
        "swap_pick_target": "🔁 Changer <b>{name}</b> avec:",
        "swap_confirm_prompt": "🔁 <b>Confirmer Echange</b>\n\nEchanger <b>{out}</b> ↔️ <b>{in_}</b>?",
        "swap_done": "✅ Echange confirme! <b>{out}</b> ↔️ <b>{in_}</b>",
        "captain_moved": "⭐ Votre capitaine a été transféré, le brassard passe donc à <b>{name}</b>. Vous pouvez le changer avant la date limite.",
        "swap_deadline_passed": "⏰ Delai echange depasse.",
        "swap_no_subs": "Aucun remplacant disponible.",
        "notif_deadline_24h":"⏰ <b>24 heures restantes!</b>\nConfirmez avant: {deadline}",
        "notif_deadline_1h": "🚨 <b>1 heure restante!</b>\nConfirmez MAINTENANT: {deadline}",
        "notif_window_open": "🔓 <b>Fenêtre ouverte!</b>\nFaites vos transferts avant {close}",
        "notif_window_close":"🔒 <b>Fenêtre fermée.</b>",
        "no_captain":       "❌ Vous devez choisir un capitaine.",
        "over_budget":      "❌ Budget dépassé!",
        "no_stats":         "Aucun point encore.",
        "no_results":       "Aucun résultat.",
        "already_confirmed":"✅ Équipe déjà confirmée.",
        "squad_summary":    "📋 <b>Votre Équipe</b>\n\n{lineup}\n\n💰 Dépensé: {spent}\n⭐ Capitaine: {captain}",
        "pick_remove":      "Sélectionnez un joueur à retirer:",
        "pick_add":         "Sélectionnez le remplaçant ({pos}):",
        "extra_cost":       "⚠️ Ce transfert coûte {pts} pts.",
        "no_transfers":     "❌ Aucun transfert disponible.",
        "player_detail":    "📊 <b>{name}</b> — {team}\n💰 {price} | Total: <b>{total} pts</b>\n",
    },
    "es": {
        "back_home":        "🏠 Inicio",
        "back":             "◀️ Atrás",
        "cancel":           "❌ Cancelar",
        "confirm":          "✅ Confirmar",
        "welcome":          "🌍 ¡Bienvenido! Elige tu idioma:",
        "enter_username":   "👤 Ingresa tu nombre de usuario de Rolletto:",
        "verifying":        "🔄 Verificando...",
        "verified":         "✅ ¡Bienvenido, {username}! Estás registrado.",
        "not_found":        "❌ No encontramos tu cuenta de Rolletto.\n\nRegístrate en Rolletto y usa @rollettopromobot para obtener giros gratis y registrarte en nuestro sistema.\n\n👉 <a href=\"{url}\">Regístrate aquí</a>\n\nUna vez registrado, usa /check para intentarlo de nuevo.",
        "already_reg":      "✅ Ya estás registrado.",
        "home_title":       "🏆 <b>Rolletto Fantasy</b>\n\n{status}",
        "btn_squad":        "📋 Mi Equipo",
        "btn_transfers":    "🔄 Fichajes",
        "btn_confirm":      "✅ Confirmar Equipo",
        "btn_stats":        "📊 Mis Stats",
        "btn_results":      "🏟 Resultados",
        "btn_leaderboard":  "🏆 Clasificación",
        "btn_rules":        "📖 Reglas",
        "build_squad":      "⚽ <b>Crear Equipo</b>\n\nElige tu formación:",
        "pick_formation":   "Elige formación:",
        "budget_left":      "💰 Presupuesto restante: {budget}",
        "pick_pos":         "Elige tu <b>{pos}</b> ({n} restantes):",
        "squad_full":       "✅ ¡Equipo completo! Elige el capitán:",
        "pick_captain":     "⭐ Elige el capitán (×2 puntos):",
        "captain_set":      "⭐ Capitán: <b>{name}</b>",
        "squad_confirmed":  "✅ <b>¡Equipo confirmado!</b> ¡Buena suerte! 🍀",
        "deadline_passed":  "❌ Plazo expirado.",
        "no_squad":         "❌ Todavía no tienes equipo.",
        "transfers_closed": "🔒 Ventana de fichajes cerrada.",
        "transfers_open":   "🔓 Ventana abierta hasta {close}.",
        "free_transfers":   "Fichajes gratuitos: {n}",
        "transfer_done":    "✅ Fichaje: {out} → {in}",
        "stats_title":      "📊 <b>Mis Stats</b>\n🏆 Total: <b>{total} pts</b>\n",
        "results_title":    "🏟 <b>Resultados Recientes</b>",
        "lb_overall":       "🏆 <b>Clasificación General</b>",
        "lb_gameweek":      "📅 <b>Round {n} Clasificación</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 General",
        "lb_btn_gw":        "📅 Este Round",
        "rules_title":      "📖 <b>Sistema de Puntos</b>",
        "rules_text": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>CÓMO JUGAR</b>
━━━━━━━━━━━━━━━━━━━━

<b>Plantilla</b>
▸ Elige 15 jugadores: 2 POR, 5 DEF, 5 MED, 3 DEL
▸ Presupuesto: 100M €
▸ <b>Máx 3 jugadores por club</b>
▸ Elige una formación para tu 11 titular
▸ Banquillo: 4 suplentes (1 POR + 3 de campo)

<b>Capitán</b>
▸ Debes elegir un capitán antes de confirmar
▸ El capitán suma ×2 puntos
▸ Sin capitán no se puede confirmar

<b>Plazo de confirmación</b>
▸ Plantilla/capitán/formación se bloquean 1h antes del primer saque inicial
▸ Plantilla no confirmada = 0 puntos en esa ronda
▸ Tras el plazo no puedes modificar la plantilla

<b>Cambios de banquillo</b>
▸ Permitidos entre ventanas de partidos (no durante partidos en vivo)
▸ Bloqueados desde 1h antes del saque inicial hasta que terminen todos los partidos
▸ Solo entre titular y suplente de la misma posición

<b>Traspasos</b>
▸ <b>1 traspaso gratis por jornada</b>
▸ Traspasos extra: -4 puntos cada uno
▸ Fuera de la ventana de traspasos = no permitidos
▸ Tras un traspaso, la plantilla se reconfirma automáticamente

━━━━━━━━━━━━━━━━━━━━
⚽ <b>SISTEMA DE PUNTOS</b>
━━━━━━━━━━━━━━━━━━━━

<b>Todos los jugadores:</b>
▸ Jugó (cualquier minuto): +1
▸ Jugó 60+ min: +1
▸ Asistencia: +3
▸ Penalti provocado: +2
▸ Penalti concedido: -1
▸ Penalti fallado: -2
▸ Tarjeta amarilla: -1
▸ Tarjeta roja: -3
▸ Amarilla + Roja: -4
▸ Gol en propia: -2
▸ <b>Contribución defensiva</b> (entradas+intercepciones+bloqueos):
   • DEF: 10+ acciones → +2
   • MED/DEL: 12+ acciones → +2
▸ <b>Jugador del partido</b> (mejor valoración): +3

<b>Portero:</b>
▸ Gol: +6 ▸ Penalti parado: +5
▸ Portería a cero (60+ min): +4
▸ Goles encajados cada 2: -1
▸ Paradas cada 3: +1

<b>Defensa:</b>
▸ Gol: +6 ▸ Portería a cero (60+ min): +4
▸ Goles encajados cada 2: -1

<b>Centrocampista:</b>
▸ Gol: +5 ▸ Portería a cero (60+ min): +1

<b>Delantero:</b>
▸ Gol: +4

<b>Capitán: ×2 todos los puntos</b>
▸ Solo los 11 titulares puntúan (banquillo = 0)

━━━━━━━━━━━━━━━━━━━━
🏅 <b>CLASIFICACIÓN</b>
━━━━━━━━━━━━━━━━━━━━

▸ General: puntos totales en todas las rondas
▸ Por ronda: mejor puntuación de esa ronda
▸ Los nombres de usuario están parcialmente ocultos
""",

        "rules_text_wc": """
━━━━━━━━━━━━━━━━━━━━
🏆 <b>CÓMO JUGAR</b>
━━━━━━━━━━━━━━━━━━━━

<b>Plantilla</b>
▸ Elige 15 jugadores: 2 POR, 5 DEF, 5 MED, 3 DEL
▸ Presupuesto: 100M $
▸ <b>Máx jugadores de una selección:</b>
   • Fase de grupos: 3
   • Octavos: 4
   • Cuartos: 5
   • Semifinales: 6
   • Final: 8
▸ Elige una formación para tu 11 titular
▸ Banquillo: 4 suplentes (1 POR + 3 de campo)

<b>Capitán</b>
▸ Debes elegir un capitán antes de confirmar
▸ El capitán suma ×2 puntos
▸ Sin capitán no se puede confirmar

<b>Plazo de confirmación</b>
▸ Plantilla/capitán/formación se bloquean 1h antes del primer saque inicial de la jornada
▸ Plantilla no confirmada = 0 puntos en esa jornada
▸ Tras el plazo no puedes modificar la plantilla

<b>Cambios de banquillo</b>
▸ Permitidos entre ventanas de partidos (no durante partidos en vivo)
▸ Bloqueados desde 1h antes del saque inicial hasta que terminen todos los partidos
▸ Solo entre titular y suplente de la misma posición

<b>Traspasos (por jornada)</b>
▸ Jornada 1: traspasos gratis ilimitados
▸ Jornada 2: 2 gratis
▸ Jornada 3: 2 gratis
▸ Octavos: traspasos gratis ilimitados
▸ Cuartos: 4 gratis
▸ Semifinales: 5 gratis
▸ Final: 6 gratis
▸ Traspasos extra: -3 puntos cada uno
▸ Tras un traspaso, la plantilla se reconfirma automáticamente

<b>Equipos eliminados</b>
▸ Cuando una selección es eliminada, sus jugadores desaparecen de la selección
▸ Los jugadores ya en tu plantilla se quedan pero suman 0 — traspásalos

━━━━━━━━━━━━━━━━━━━━
⚽ <b>SISTEMA DE PUNTOS</b>
━━━━━━━━━━━━━━━━━━━━

<b>Todos los jugadores:</b>
▸ Jugó (cualquier minuto): +1
▸ Jugó 60+ min: +1
▸ Asistencia: +3
▸ Penalti provocado: +2
▸ Penalti concedido: -1
▸ Penalti fallado: -2
▸ Tarjeta amarilla: -1
▸ Tarjeta roja: -3
▸ Amarilla + Roja: -4
▸ Gol en propia: -2
▸ <b>Contribución defensiva</b> (entradas+intercepciones+bloqueos):
   • DEF: 10+ acciones → +2
   • MED/DEL: 12+ acciones → +2
▸ <b>Jugador del partido</b> (mejor valoración): +3

<b>Portero:</b>
▸ Gol: +6 ▸ Penalti parado: +5
▸ Portería a cero (60+ min): +4
▸ Goles encajados cada 2: -1
▸ Paradas cada 3: +1

<b>Defensa:</b>
▸ Gol: +6 ▸ Portería a cero (60+ min): +4
▸ Goles encajados cada 2: -1

<b>Centrocampista:</b>
▸ Gol: +5 ▸ Portería a cero (60+ min): +1

<b>Delantero:</b>
▸ Gol: +4

<b>Capitán: ×2 todos los puntos</b>
▸ Solo los 11 titulares puntúan (banquillo = 0)

━━━━━━━━━━━━━━━━━━━━
💰 <b>BOTE — TOP 30</b>
━━━━━━━━━━━━━━━━━━━━

🥇 1º: $500
🥈 2º: $300
🥉 3º: $200
🏅 4º: $50
🏅 5º: $50
🎖 6º–10º: $30 cada uno
🎖 11º–20º: $15 cada uno
🎖 21º–30º: $10 cada uno

<i>Bote total: $1.500</i>

━━━━━━━━━━━━━━━━━━━━
🏅 <b>CLASIFICACIÓN</b>
━━━━━━━━━━━━━━━━━━━━

▸ General: puntos totales en todas las jornadas
▸ Por jornada: mejor puntuación de esa jornada
▸ Los nombres de usuario están parcialmente ocultos
""",
        "notif_result":     "⚽ <b>Resultado</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 ¡Puntos actualizados!",
        "notif_gw_summary": "📊 <b>¡Jornada {n} terminada!</b>\nTus puntos: <b>{pts}</b>",
        "btn_swap_subs": "🔁 Cambiar Suplentes",
        "btn_randomise": "🎲 Aleatorio",
        "rnd_building": "🎲 Creando un equipo aleatorio…",
        "rnd_failed": "No se pudo crear un equipo dentro del presupuesto. Inténtalo de nuevo.",
        "swap_pick_sub": "🔁 <b>Selecciona el suplente:</b>",
        "swap_pick_target": "🔁 Cambiar <b>{name}</b> con:",
        "swap_confirm_prompt": "🔁 <b>Confirmar Cambio</b>\n\nCambiar <b>{out}</b> ↔️ <b>{in_}</b>?",
        "swap_done": "✅ Cambio confirmado! <b>{out}</b> ↔️ <b>{in_}</b>",
        "captain_moved": "⭐ Tu capitán fue traspasado, así que el brazalete pasó a <b>{name}</b>. Puedes cambiarlo antes de la fecha límite.",
        "swap_deadline_passed": "⏰ Plazo de cambios pasado.",
        "swap_no_subs": "No hay suplentes disponibles.",
        "notif_deadline_24h":"⏰ <b>¡24 horas restantes!</b>\nConfirma antes de: {deadline}",
        "notif_deadline_1h": "🚨 <b>¡1 hora restante!</b>\nConfirma AHORA: {deadline}",
        "notif_window_open": "🔓 <b>¡Ventana abierta!</b>\nHaz tus fichajes antes de {close}",
        "notif_window_close":"🔒 <b>Ventana cerrada.</b>",
        "no_captain":       "❌ Debes elegir un capitán.",
        "over_budget":      "❌ ¡Presupuesto excedido!",
        "no_stats":         "Aún no hay puntos.",
        "no_results":       "Sin resultados.",
        "already_confirmed":"✅ Equipo ya confirmado.",
        "squad_summary":    "📋 <b>Tu Equipo</b>\n\n{lineup}\n\n💰 Gastado: {spent}\n⭐ Capitán: {captain}",
        "pick_remove":      "Selecciona jugador a eliminar:",
        "pick_add":         "Selecciona sustituto ({pos}):",
        "extra_cost":       "⚠️ Este fichaje cuesta {pts} pts.",
        "no_transfers":     "❌ No hay fichajes disponibles.",
        "player_detail":    "📊 <b>{name}</b> — {team}\n💰 {price} | Total: <b>{total} pts</b>\n",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Get translated string, fallback to EN."""
    lang = lang if lang in STRINGS else "en"
    text = STRINGS[lang].get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
