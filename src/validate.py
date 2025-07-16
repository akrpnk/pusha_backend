# src/validate.py
from fastapi import HTTPException, status
from init_data_py import InitData, errors


def get_init_data(raw: str, bot_token: str, *, lifetime: int = 3600, request=None):
    """
    Parse + validate Telegram Web-App initData.
    Raises HTTP 403 for forged data, 400 for completely malformed / absent data.
    """
    try:
        init = InitData.parse(raw)
    except errors.UnexpectedFormatError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="initData missing or malformed – open this page inside Telegram",
        )

    if not init.validate(bot_token, lifetime=lifetime):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="initData signature invalid or expired",
        )

    if request is not None:
        request.state.user_id = str(init.user.id)
    return init
