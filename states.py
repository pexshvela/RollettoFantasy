from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_username = State()
    waiting_check    = State()

class Setup(StatesGroup):
    selecting_language = State()
    reading_rules      = State()

class Squad(StatesGroup):
    home               = State()
    selecting_formation = State()
    viewing_squad      = State()
    selecting_position = State()
    selecting_player   = State()
    confirming_player  = State()
    selecting_captain  = State()
    confirming_submit  = State()

class Transfers(StatesGroup):
    menu               = State()
    select_player_out  = State()
    select_player_in   = State()
    confirming         = State()

class Admin(StatesGroup):
    menu               = State()
    get_target_id      = State()
    get_message        = State()
    get_broadcast_ids  = State()
    get_broadcast_msg  = State()
    confirming_send    = State()
    get_promo_id       = State()
    get_promo_code     = State()
