# ─── Conversation states ──────────────────────────────────────────────────────

# Registration flow
REG_NAME, REG_EMPLOYEE_ID, REG_DEPARTMENT = range(3)

# Main HR flow
CHOOSING, CHOOSING_LEAVE_TYPE, WAITING_FOR_DATES, WAITING_FOR_MC_PHOTO = range(3, 7)


# ─── Leave type configuration ─────────────────────────────────────────────────

# key → display label + annual entitlement in days
LEAVE_TYPES: dict[str, dict] = {
    "annual":    {"label": "📅 Annual Leave",     "default_days": 14},
    "emergency": {"label": "🚨 Emergency Leave",  "default_days": 3},
    "unpaid":    {"label": "💸 Unpaid Leave",     "default_days": 9999},  # effectively unlimited
    "paternity": {"label": "👶 Paternity Leave",  "default_days": 7},
    "maternity": {"label": "🤱 Maternity Leave",  "default_days": 60},
}

# MC is a separate flow (requires photo), but shares the leave_balance table
MC_DEFAULT_DAYS = 14
