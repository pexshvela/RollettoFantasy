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
        "not_found":        "❌ Username not found. Please register at {url} first.",
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
        "lb_gameweek":      "📅 <b>Gameweek {n} Leaderboard</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 Overall",
        "lb_btn_gw":        "📅 This Gameweek",

        # Rules
        "rules_title":      "📖 <b>Points System</b>",
        "rules_text": """
<b>All Players:</b>
▸ Played: +1 pt
▸ 60+ min: +1 pt
▸ Assist: +3 pts
▸ Penalty earned: +2 pts
▸ Penalty conceded: -1 pt
▸ Penalty missed: -2 pts
▸ Yellow card: -1 pt
▸ Red card: -3 pts
▸ Yellow + Red: -4 pts
▸ Own goal: -2 pts
▸ Def. actions (per 3): +1 pt

<b>Goalkeeper:</b>
▸ Goal: +6 pts
▸ Penalty saved: +5 pts
▸ Clean sheet (60+ min): +4 pts
▸ Goals conceded (per 2): -1 pt
▸ Saves (per 3): +1 pt

<b>Defender:</b>
▸ Goal: +6 pts
▸ Clean sheet (60+ min): +4 pts
▸ Goals conceded (per 2): -1 pt

<b>Midfielder:</b>
▸ Goal: +5 pts
▸ Clean sheet (60+ min): +1 pt

<b>Forward:</b>
▸ Goal: +4 pts

<b>Captain: ×2 all points</b>
""",

        # Notifications
        "notif_deadline_24h": "⏰ <b>24 hours left!</b>\nConfirm your squad before the deadline:\n{deadline}",
        "notif_deadline_1h":  "🚨 <b>1 hour left!</b>\nConfirm your squad NOW:\n{deadline}",
        "notif_window_open":  "🔓 <b>Transfer window is open!</b>\nMake your transfers before {close}",
        "notif_window_close": "🔒 <b>Transfer window has closed.</b>",
        "notif_result":       "⚽ <b>Match Result</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 Points updated! Tap 📊 Stats to see your score.",
        "notif_gw_summary":   "📊 <b>Gameweek {n} finished!</b>\nYour score: <b>{pts} pts</b>\nTap 🏆 Leaderboard to see rankings.",
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
        "not_found":        "❌ Utente non trovato. Registrati su {url}.",
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
        "lb_gameweek":      "📅 <b>Classifica Giornata {n}</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 Generale",
        "lb_btn_gw":        "📅 Questa Giornata",
        "rules_title":      "📖 <b>Sistema Punteggi</b>",
        "rules_text":       "Vedi versione EN per le regole complete.",
        "notif_result":     "⚽ <b>Risultato</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 Punti aggiornati!",
        "notif_gw_summary": "📊 <b>Giornata {n} finita!</b>\nI tuoi punti: <b>{pts}</b>",
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
        "lb_btn_gw":        "📅 Questa Giornata",
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
        "not_found":        "❌ Utilisateur introuvable. Inscrivez-vous sur {url}.",
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
        "lb_gameweek":      "📅 <b>Classement Journée {n}</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 Général",
        "lb_btn_gw":        "📅 Cette Journée",
        "rules_title":      "📖 <b>Système de Points</b>",
        "rules_text":       "Voir version EN pour les règles complètes.",
        "notif_result":     "⚽ <b>Résultat</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 Points mis à jour!",
        "notif_gw_summary": "📊 <b>Journée {n} terminée!</b>\nVos points: <b>{pts}</b>",
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
        "not_found":        "❌ Usuario no encontrado. Regístrate en {url}.",
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
        "lb_gameweek":      "📅 <b>Clasificación Jornada {n}</b>",
        "lb_entry":         "{rank}. {username} — {pts} pts",
        "lb_btn_overall":   "🏆 General",
        "lb_btn_gw":        "📅 Esta Jornada",
        "rules_title":      "📖 <b>Sistema de Puntos</b>",
        "rules_text":       "Ver versión EN para las reglas completas.",
        "notif_result":     "⚽ <b>Resultado</b>\n\n{home} {hs} - {as_} {away}\n\n🏆 ¡Puntos actualizados!",
        "notif_gw_summary": "📊 <b>¡Jornada {n} terminada!</b>\nTus puntos: <b>{pts}</b>",
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
