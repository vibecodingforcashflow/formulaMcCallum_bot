from aiogram.fsm.state import State, StatesGroup


class McCallumFlow(StatesGroup):
    waiting_wrist = State()
    collecting = State()
