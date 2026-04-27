"""states.py — All FSM states."""
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    language    = State()
    username    = State()


class Squad(StatesGroup):
    formation   = State()
    picking_gk  = State()
    picking_def = State()
    picking_mf  = State()
    picking_fw  = State()
    picking_bench = State()
    captain     = State()
    review      = State()
    searching   = State()


class Transfer(StatesGroup):
    pick_out    = State()
    pick_in     = State()
    confirm     = State()


class Stats(StatesGroup):
    viewing     = State()
    player      = State()


class Results(StatesGroup):
    viewing     = State()
    match       = State()


class Leaderboard(StatesGroup):
    viewing     = State()


class Admin(StatesGroup):
    main        = State()
    broadcast   = State()
    send_user   = State()
    reset_menu  = State()
    reset_user  = State()
