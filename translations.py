# All bot messages in 4 languages
# IT / FR / ES are placeholder — replace with professional translations before launch

T = {
    "en": {
        "lang_flag": "🇬🇧",
        "ask_username": (
            "👋 Welcome to <b>Rolletto Fantasy Football</b>!\n\n"
            "To get started, please enter your <b>Rolletto username</b>:"
        ),
        "checking": "🔍 Checking your account...",
        "not_found": (
            "❌ We couldn't find your Rolletto account.\n\n"
            "Please sign up at Rolletto and use <b>@rollettopromobot</b> to get free spins "
            "and register in our system.\n\n"
            "👉 <a href='{url}'>Sign up here</a>\n\n"
            "Once registered, use /check to try again."
        ),
        "still_not_found": (
            "⏳ We still couldn't find your account.\n\n"
            "Our team has been notified and will grant you access manually within <b>24 hours</b>.\n"
            "Please be patient!"
        ),
        "found_welcome": "✅ Account verified! Welcome, <b>{username}</b>!\n\nPlease choose your language:",
        "choose_lang": "🌍 Please choose your language:",
        "rules_title": (
            "📋 <b>ROLLETTO FANTASY FOOTBALL — RULES</b>\n\n"
            "🏆 <b>Champions League Edition</b>\n\n"
            "<b>How it works:</b>\n"
            "Build a squad of 15 players with a €100M budget and score points based on real CL match performance.\n\n"
            "<b>💰 Prizes — Top 10:</b>\n"
            "🥇 1st — €500 bonus\n"
            "🥈 2nd — €300 bonus\n"
            "🥉 3rd — €150 bonus\n"
            "4th — €100 bonus\n"
            "5th — €75 bonus\n"
            "6th — €50 bonus\n"
            "7th–10th — €25 bonus each\n\n"
            "<b>📊 Points system:</b>\n"
            "⚽ Goal (FW/MF) → +5 pts\n"
            "⚽ Goal (DEF/GK) → +10 pts\n"
            "🅰️ Assist → +3 pts\n"
            "🧤 Clean sheet (GK/DEF) → +4 pts\n"
            "🟨 Yellow card → -1 pt\n"
            "🟥 Red card → -3 pts\n"
            "❌ Penalty miss → -2 pts\n\n"
            "<b>🔄 Transfers:</b>\n"
            "2 free transfers per matchday. Extra transfers cost -4 pts each.\n\n"
            "<b>🛡️ Fair play:</b>\n"
            "One account per person. No bots or multiple accounts. Violations = disqualification.\n\n"
            "By accepting you confirm you have read and agree to all rules."
        ),
        "accept_btn":      "✅ Accept & Continue",
        "home_title": (
            "🏠 <b>HOME</b>\n\n"
            "💰 Budget: <b>{budget}</b>\n"
            "👥 Squad: <b>{filled}/15</b> players\n"
            "⭐ Captain: <b>{captain}</b>\n"
            "📊 Total points: <b>{points}</b>"
        ),
        "choose_formation": "⚽ Choose your formation:",
        "formation_set": "✅ Formation <b>{f}</b> selected!\n\nNow build your squad below.",
        "squad_view": (
            "📋 <b>YOUR SQUAD</b> — {formation}\n"
            "💰 Remaining budget: <b>{budget}</b>\n\n"
            "{visual}\n\n"
            "🔵 Tap a position to add a player."
        ),
        "choose_position": "Select a position to fill:",
        "pick_player": "👇 Choose a <b>{pos}</b> (Page {page}/{total}):",
        "no_budget":    "❌ Not enough budget for this player!",
        "already_in":   "❌ This player is already in your squad!",
        "confirm_player": (
            "➕ Add <b>{name}</b> {nation} ({team}) — {price}?\n\n"
            "💰 Remaining after: <b>{remaining}</b>"
        ),
        "yes_btn":    "✅ Yes, add",
        "no_btn":     "❌ Cancel",
        "player_added": "✅ <b>{name}</b> added to your squad!",
        "choose_captain": "⭐ Choose your captain (scores double points):",
        "captain_set":    "⭐ <b>{name}</b> set as captain!",
        "confirm_submit": (
            "🚀 <b>Submit your squad?</b>\n\n"
            "Formation: {formation}\n"
            "Captain: {captain}\n"
            "Budget used: {spent}\n\n"
            "You can still edit until the deadline."
        ),
        "squad_submitted": "🎉 Squad submitted successfully! Good luck! 🏆",
        "squad_incomplete": "⚠️ Please fill all 15 squad slots before submitting.",
        "no_captain": "⚠️ Please set a captain before submitting.",
        "transfer_menu": (
            "🔄 <b>TRANSFERS</b>\n\n"
            "Free transfers remaining: <b>{free}</b>\n"
            "Extra transfer cost: -4 pts each\n\n"
            "Select a player to transfer OUT:"
        ),
        "select_player_in": "👇 Choose a replacement <b>{pos}</b>:",
        "confirm_transfer": (
            "🔄 Transfer <b>{out}</b> → <b>{in}</b>?\n\n"
            "{cost_msg}"
        ),
        "transfer_free_cost": "✅ This is a free transfer.",
        "transfer_points_cost": "⚠️ This transfer costs <b>-4 points</b>.",
        "transfer_done": "✅ Transfer complete!",
        "back_home": "🏠 Home",
        "transfers_btn": "🔄 Transfers",
        "my_squad_btn": "📋 My Squad",
        "leaderboard_btn": "📊 Leaderboard",
        "stats_btn":      "📊 Stats",
        "results_btn":    "🏟 Results",
        "rules_btn":       "📋 Rules",
        "admin_btn": "⚙️ Admin",
        "leaderboard_empty": "📊 Leaderboard is empty so far. Be the first to submit your squad!",
        "leaderboard_title": "📊 <b>LEADERBOARD — Top 10</b>\n\n",
        # Admin
        "admin_menu": "⚙️ <b>ADMIN PANEL</b>\n\nChoose an action:",
        "admin_send_msg":   "📨 Message User",
        "admin_broadcast":  "📢 Broadcast",
        "admin_pending":    "⏳ Pending Users",
        "admin_get_id":     "Enter the user's Telegram ID:",
        "admin_get_msg":    "Now send the message (text or photo) to forward to the user:",
        "admin_get_bc_ids": "Send a list of Telegram IDs separated by commas, or type <b>ALL</b> to send to everyone:",
        "admin_confirm_send": "Send this message to <b>{n} user(s)</b>?",
        "admin_send_done":  "✅ Message sent to {n} user(s).",
        "admin_user_not_found": "❌ User not found in database.",
        "promo_get_id":   "Enter the Telegram ID of the user to receive the promo:",
        "promo_get_code": "Enter the promo code to send:",
        "promo_confirm":  "Send promo code <b>{code}</b> to user <b>{uid}</b>?",
        "promo_sent":     "🎁 Your exclusive Rolletto promo code: <b>{code}</b>",
        "promo_done":     "✅ Promo code sent.",
        "pending_list":   "⏳ <b>Pending access requests:</b>\n\n{list}",
        "pending_empty":  "✅ No pending access requests.",
        # Admin notification sent to admin chat
        "admin_notify_pending": (
            "🔔 <b>New access request</b>\n\n"
            "Telegram ID: <code>{tg_id}</code>\n"
            "Telegram username: @{tg_username}\n"
            "Rolletto username: <b>{rolletto}</b>\n"
            "Time: {time}\n\n"
            "User tried /check and was still not found in the sheets."
        ),
    },

    "it": {
        "lang_flag": "🇮🇹",
        "ask_username": "👋 Benvenuto su <b>Rolletto Fantasy Football</b>!\n\nInserisci il tuo <b>username Rolletto</b>:",
        "checking": "🔍 Verifica in corso...",
        "not_found": (
            "❌ Account Rolletto non trovato.\n\n"
            "Registrati su Rolletto e usa <b>@rollettopromobot</b> per ricevere giri gratuiti.\n\n"
            "👉 <a href='{url}'>Registrati qui</a>\n\n"
            "Una volta registrato, usa /check per riprovare."
        ),
        "still_not_found": "⏳ Account ancora non trovato. Il nostro team ti darà accesso entro <b>24 ore</b>.",
        "found_welcome": "✅ Account verificato! Benvenuto, <b>{username}</b>!\n\nScegli la lingua:",
        "choose_lang": "🌍 Scegli la tua lingua:",
        "rules_title": "📋 <b>REGOLE ROLLETTO FANTASY</b>\n\n[Versione italiana — da tradurre professionalmente]",
        "accept_btn": "✅ Accetta e Continua",
        "home_title": "🏠 <b>HOME</b>\n\n💰 Budget: <b>{budget}</b>\n👥 Rosa: <b>{filled}/15</b>\n⭐ Capitano: <b>{captain}</b>\n📊 Punti: <b>{points}</b>",
        "choose_formation": "⚽ Scegli il modulo:",
        "formation_set": "✅ Modulo <b>{f}</b> selezionato!",
        "squad_view": "📋 <b>LA TUA ROSA</b> — {formation}\n💰 Budget rimanente: <b>{budget}</b>\n\n{visual}\n\n🔵 Tocca una posizione.",
        "choose_position": "Seleziona una posizione:",
        "pick_player": "👇 Scegli un <b>{pos}</b> (Pag {page}/{total}):",
        "no_budget": "❌ Budget insufficiente!",
        "already_in": "❌ Giocatore già nella rosa!",
        "confirm_player": "➕ Aggiungere <b>{name}</b> {nation} ({team}) — {price}?\n\n💰 Rimanente: <b>{remaining}</b>",
        "yes_btn": "✅ Sì, aggiungi",
        "no_btn": "❌ Annulla",
        "player_added": "✅ <b>{name}</b> aggiunto!",
        "choose_captain": "⭐ Scegli il capitano:",
        "captain_set": "⭐ <b>{name}</b> è il capitano!",
        "confirm_submit": "🚀 <b>Confermi la rosa?</b>\n\nModulo: {formation}\nCapitano: {captain}\nBudget usato: {spent}",
        "squad_submitted": "🎉 Rosa inviata! Buona fortuna! 🏆",
        "squad_incomplete": "⚠️ Completa tutti i 15 slot prima di inviare.",
        "no_captain": "⚠️ Seleziona un capitano prima di inviare.",
        "transfer_menu": "🔄 <b>TRASFERIMENTI</b>\n\nTrasferimenti gratuiti: <b>{free}</b>\nCosto extra: -4 punti\n\nSeleziona il giocatore da cedere:",
        "select_player_in": "👇 Scegli il sostituto <b>{pos}</b>:",
        "confirm_transfer": "🔄 Cedere <b>{out}</b> → <b>{in}</b>?\n\n{cost_msg}",
        "transfer_free_cost": "✅ Trasferimento gratuito.",
        "transfer_points_cost": "⚠️ Questo trasferimento costa <b>-4 punti</b>.",
        "transfer_done": "✅ Trasferimento completato!",
        "back_home": "🏠 Home",
        "transfers_btn": "🔄 Trasferimenti",
        "my_squad_btn": "📋 La mia Rosa",
        "leaderboard_btn": "📊 Classifica",
        "stats_btn":      "📊 Statistiche",
        "results_btn":    "🏟 Risultati",
        "rules_btn":       "📋 Regole",
        "admin_btn": "⚙️ Admin",
        "leaderboard_empty": "📊 Classifica vuota. Sii il primo!",
        "leaderboard_title": "📊 <b>CLASSIFICA — Top 10</b>\n\n",
        "admin_menu": "⚙️ <b>PANNELLO ADMIN</b>",
        "admin_send_msg": "📨 Messaggio Utente",
        "admin_broadcast": "📢 Broadcast",
        "admin_pending": "⏳ Utenti in Attesa",
        "admin_get_id": "Inserisci il Telegram ID dell'utente:",
        "admin_get_msg": "Invia il messaggio da inviare:",
        "admin_get_bc_ids": "Inserisci gli ID separati da virgola, o scrivi <b>ALL</b>:",
        "admin_confirm_send": "Inviare a <b>{n} utente(i)</b>?",
        "admin_send_done": "✅ Messaggio inviato a {n} utente(i).",
        "admin_user_not_found": "❌ Utente non trovato.",
        "promo_get_id": "Inserisci il Telegram ID:",
        "promo_get_code": "Inserisci il codice promo:",
        "promo_confirm": "Inviare il codice <b>{code}</b> all'utente <b>{uid}</b>?",
        "promo_sent": "🎁 Il tuo codice promo esclusivo Rolletto: <b>{code}</b>",
        "promo_done": "✅ Codice promo inviato.",
        "pending_list": "⏳ <b>Richieste in attesa:</b>\n\n{list}",
        "pending_empty": "✅ Nessuna richiesta in attesa.",
        "admin_notify_pending": "🔔 <b>Nuova richiesta di accesso</b>\n\nTelegram ID: <code>{tg_id}</code>\n@{tg_username}\nRolletto: <b>{rolletto}</b>\nOra: {time}",
    },

    "fr": {
        "lang_flag": "🇫🇷",
        "ask_username": "👋 Bienvenue sur <b>Rolletto Fantasy Football</b>!\n\nEntrez votre <b>nom d'utilisateur Rolletto</b>:",
        "checking": "🔍 Vérification en cours...",
        "not_found": (
            "❌ Compte Rolletto introuvable.\n\n"
            "Inscrivez-vous sur Rolletto et utilisez <b>@rollettopromobot</b> pour recevoir des tours gratuits.\n\n"
            "👉 <a href='{url}'>S'inscrire ici</a>\n\n"
            "Une fois inscrit, utilisez /check pour réessayer."
        ),
        "still_not_found": "⏳ Compte toujours introuvable. Notre équipe vous donnera accès dans <b>24 heures</b>.",
        "found_welcome": "✅ Compte vérifié! Bienvenue, <b>{username}</b>!\n\nChoisissez votre langue:",
        "choose_lang": "🌍 Choisissez votre langue:",
        "rules_title": "📋 <b>RÈGLES ROLLETTO FANTASY</b>\n\n[Version française — à traduire professionnellement]",
        "accept_btn": "✅ Accepter et Continuer",
        "home_title": "🏠 <b>ACCUEIL</b>\n\n💰 Budget: <b>{budget}</b>\n👥 Équipe: <b>{filled}/15</b>\n⭐ Capitaine: <b>{captain}</b>\n📊 Points: <b>{points}</b>",
        "choose_formation": "⚽ Choisissez votre formation:",
        "formation_set": "✅ Formation <b>{f}</b> sélectionnée!",
        "squad_view": "📋 <b>VOTRE ÉQUIPE</b> — {formation}\n💰 Budget restant: <b>{budget}</b>\n\n{visual}\n\n🔵 Appuyez sur un poste.",
        "choose_position": "Sélectionnez un poste:",
        "pick_player": "👇 Choisissez un <b>{pos}</b> (Page {page}/{total}):",
        "no_budget": "❌ Budget insuffisant!",
        "already_in": "❌ Joueur déjà dans votre équipe!",
        "confirm_player": "➕ Ajouter <b>{name}</b> {nation} ({team}) — {price}?\n\n💰 Restant: <b>{remaining}</b>",
        "yes_btn": "✅ Oui, ajouter",
        "no_btn": "❌ Annuler",
        "player_added": "✅ <b>{name}</b> ajouté!",
        "choose_captain": "⭐ Choisissez votre capitaine:",
        "captain_set": "⭐ <b>{name}</b> est capitaine!",
        "confirm_submit": "🚀 <b>Confirmer votre équipe?</b>\n\nFormation: {formation}\nCapitaine: {captain}\nBudget utilisé: {spent}",
        "squad_submitted": "🎉 Équipe soumise! Bonne chance! 🏆",
        "squad_incomplete": "⚠️ Remplissez les 15 slots avant de soumettre.",
        "no_captain": "⚠️ Choisissez un capitaine avant de soumettre.",
        "transfer_menu": "🔄 <b>TRANSFERTS</b>\n\nTransferts gratuits: <b>{free}</b>\nCoût supplémentaire: -4 pts\n\nSélectionnez un joueur à transférer:",
        "select_player_in": "👇 Choisissez un remplaçant <b>{pos}</b>:",
        "confirm_transfer": "🔄 Transférer <b>{out}</b> → <b>{in}</b>?\n\n{cost_msg}",
        "transfer_free_cost": "✅ Transfert gratuit.",
        "transfer_points_cost": "⚠️ Ce transfert coûte <b>-4 points</b>.",
        "transfer_done": "✅ Transfert effectué!",
        "back_home": "🏠 Accueil",
        "transfers_btn": "🔄 Transferts",
        "my_squad_btn": "📋 Mon Équipe",
        "leaderboard_btn": "📊 Classement",
        "stats_btn":      "📊 Statistiques",
        "results_btn":    "🏟 Résultats",
        "rules_btn":       "📋 Règles",
        "admin_btn": "⚙️ Admin",
        "leaderboard_empty": "📊 Classement vide. Soyez le premier!",
        "leaderboard_title": "📊 <b>CLASSEMENT — Top 10</b>\n\n",
        "admin_menu": "⚙️ <b>PANNEAU ADMIN</b>",
        "admin_send_msg": "📨 Message Utilisateur",
        "admin_broadcast": "📢 Diffusion",
        "admin_pending": "⏳ Utilisateurs en Attente",
        "admin_get_id": "Entrez l'ID Telegram de l'utilisateur:",
        "admin_get_msg": "Envoyez le message à transmettre:",
        "admin_get_bc_ids": "Entrez les IDs séparés par des virgules, ou tapez <b>ALL</b>:",
        "admin_confirm_send": "Envoyer à <b>{n} utilisateur(s)</b>?",
        "admin_send_done": "✅ Message envoyé à {n} utilisateur(s).",
        "admin_user_not_found": "❌ Utilisateur introuvable.",
        "promo_get_id": "Entrez l'ID Telegram:",
        "promo_get_code": "Entrez le code promo:",
        "promo_confirm": "Envoyer le code <b>{code}</b> à l'utilisateur <b>{uid}</b>?",
        "promo_sent": "🎁 Votre code promo exclusif Rolletto: <b>{code}</b>",
        "promo_done": "✅ Code promo envoyé.",
        "pending_list": "⏳ <b>Demandes en attente:</b>\n\n{list}",
        "pending_empty": "✅ Aucune demande en attente.",
        "admin_notify_pending": "🔔 <b>Nouvelle demande d'accès</b>\n\nTelegram ID: <code>{tg_id}</code>\n@{tg_username}\nRolletto: <b>{rolletto}</b>\nHeure: {time}",
    },

    "es": {
        "lang_flag": "🇪🇸",
        "ask_username": "👋 ¡Bienvenido a <b>Rolletto Fantasy Football</b>!\n\nIngresa tu <b>nombre de usuario de Rolletto</b>:",
        "checking": "🔍 Verificando tu cuenta...",
        "not_found": (
            "❌ No encontramos tu cuenta de Rolletto.\n\n"
            "Regístrate en Rolletto y usa <b>@rollettopromobot</b> para recibir giros gratis.\n\n"
            "👉 <a href='{url}'>Regístrate aquí</a>\n\n"
            "Una vez registrado, usa /check para volver a intentarlo."
        ),
        "still_not_found": "⏳ Cuenta aún no encontrada. Nuestro equipo te dará acceso en <b>24 horas</b>.",
        "found_welcome": "✅ ¡Cuenta verificada! Bienvenido, <b>{username}</b>!\n\nElige tu idioma:",
        "choose_lang": "🌍 Elige tu idioma:",
        "rules_title": "📋 <b>REGLAS ROLLETTO FANTASY</b>\n\n[Versión en español — traducción profesional pendiente]",
        "accept_btn": "✅ Aceptar y Continuar",
        "home_title": "🏠 <b>INICIO</b>\n\n💰 Presupuesto: <b>{budget}</b>\n👥 Plantilla: <b>{filled}/15</b>\n⭐ Capitán: <b>{captain}</b>\n📊 Puntos: <b>{points}</b>",
        "choose_formation": "⚽ Elige tu formación:",
        "formation_set": "✅ Formación <b>{f}</b> seleccionada!",
        "squad_view": "📋 <b>TU PLANTILLA</b> — {formation}\n💰 Presupuesto restante: <b>{budget}</b>\n\n{visual}\n\n🔵 Toca una posición.",
        "choose_position": "Selecciona una posición:",
        "pick_player": "👇 Elige un <b>{pos}</b> (Pág {page}/{total}):",
        "no_budget": "❌ ¡Presupuesto insuficiente!",
        "already_in": "❌ ¡Este jugador ya está en tu plantilla!",
        "confirm_player": "➕ ¿Añadir a <b>{name}</b> {nation} ({team}) — {price}?\n\n💰 Restante: <b>{remaining}</b>",
        "yes_btn": "✅ Sí, añadir",
        "no_btn": "❌ Cancelar",
        "player_added": "✅ ¡<b>{name}</b> añadido!",
        "choose_captain": "⭐ Elige tu capitán:",
        "captain_set": "⭐ ¡<b>{name}</b> es el capitán!",
        "confirm_submit": "🚀 <b>¿Confirmar plantilla?</b>\n\nFormación: {formation}\nCapitán: {captain}\nPresupuesto usado: {spent}",
        "squad_submitted": "🎉 ¡Plantilla enviada! ¡Buena suerte! 🏆",
        "squad_incomplete": "⚠️ Completa los 15 huecos antes de enviar.",
        "no_captain": "⚠️ Elige un capitán antes de enviar.",
        "transfer_menu": "🔄 <b>TRASPASOS</b>\n\nTraspasos gratuitos: <b>{free}</b>\nCosto extra: -4 pts\n\nSelecciona un jugador para traspasar:",
        "select_player_in": "👇 Elige un sustituto <b>{pos}</b>:",
        "confirm_transfer": "🔄 ¿Traspasar <b>{out}</b> → <b>{in}</b>?\n\n{cost_msg}",
        "transfer_free_cost": "✅ Traspaso gratuito.",
        "transfer_points_cost": "⚠️ Este traspaso cuesta <b>-4 puntos</b>.",
        "transfer_done": "✅ ¡Traspaso completado!",
        "back_home": "🏠 Inicio",
        "transfers_btn": "🔄 Traspasos",
        "my_squad_btn": "📋 Mi Plantilla",
        "leaderboard_btn": "📊 Clasificación",
        "stats_btn":      "📊 Estadísticas",
        "results_btn":    "🏟 Resultados",
        "rules_btn":       "📋 Reglas",
        "admin_btn": "⚙️ Admin",
        "leaderboard_empty": "📊 Clasificación vacía. ¡Sé el primero!",
        "leaderboard_title": "📊 <b>CLASIFICACIÓN — Top 10</b>\n\n",
        "admin_menu": "⚙️ <b>PANEL DE ADMIN</b>",
        "admin_send_msg": "📨 Mensaje a Usuario",
        "admin_broadcast": "📢 Difusión",
        "admin_pending": "⏳ Usuarios Pendientes",
        "admin_get_id": "Introduce el ID de Telegram del usuario:",
        "admin_get_msg": "Envía el mensaje a reenviar:",
        "admin_get_bc_ids": "Introduce los IDs separados por comas, o escribe <b>ALL</b>:",
        "admin_confirm_send": "¿Enviar a <b>{n} usuario(s)</b>?",
        "admin_send_done": "✅ Mensaje enviado a {n} usuario(s).",
        "admin_user_not_found": "❌ Usuario no encontrado.",
        "promo_get_id": "Introduce el ID de Telegram:",
        "promo_get_code": "Introduce el código promo:",
        "promo_confirm": "¿Enviar el código <b>{code}</b> al usuario <b>{uid}</b>?",
        "promo_sent": "🎁 Tu código promo exclusivo de Rolletto: <b>{code}</b>",
        "promo_done": "✅ Código promo enviado.",
        "pending_list": "⏳ <b>Solicitudes pendientes:</b>\n\n{list}",
        "pending_empty": "✅ No hay solicitudes pendientes.",
        "admin_notify_pending": "🔔 <b>Nueva solicitud de acceso</b>\n\nTelegram ID: <code>{tg_id}</code>\n@{tg_username}\nRolletto: <b>{rolletto}</b>\nHora: {time}",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Get translated string, fallback to English."""
    text = T.get(lang, T["en"]).get(key) or T["en"].get(key, f"[{key}]")
    if kwargs:
        text = text.format(**kwargs)
    return text
