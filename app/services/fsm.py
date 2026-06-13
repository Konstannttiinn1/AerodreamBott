from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import User

logger = logging.getLogger(__name__)

CANCEL_TEXTS = {"❌ отмена", "отмена", "/cancel", "⬅️ назад", "назад"}


def is_cancel_text(text: str | None) -> bool:
    return (text or "").strip().casefold() in CANCEL_TEXTS


async def safe_clear_state(state: FSMContext, user: User | None = None, reason: str = "") -> bool:
    current_state = await state.get_state()
    if current_state is None:
        return False
    await state.clear()
    logger.info(
        "FSM state cleared: user_id=%s state=%s reason=%s",
        user.id if user else None,
        current_state,
        reason,
    )
    return True


async def set_fsm_state(state: FSMContext, new_state, user: User | None = None, reason: str = "") -> None:
    await state.set_state(new_state)
    logger.info(
        "FSM state set: user_id=%s state=%s reason=%s",
        user.id if user else None,
        await state.get_state(),
        reason,
    )
