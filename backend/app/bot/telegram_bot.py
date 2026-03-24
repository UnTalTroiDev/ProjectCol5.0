"""MedCity Dashboard — Telegram Bot.

Exposes the same data available in the web dashboard via Telegram commands.
Uses the existing service layer directly (no HTTP round-trip).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..services.dashboard_service import (
    get_dashboard_compare,
    get_dashboard_overview,
    get_territory_comunas,
)
from ..services.security_service import get_criminalidad_consolidada
from ..services.health_service import get_natalidad
from ..services.education_service import get_establecimientos
from ..services.environment_service import get_residuos_solidos
from ..services.quality_service import get_imcv

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Mensaje de bienvenida"),
    BotCommand("help", "Mostrar comandos disponibles"),
    BotCommand("comunas", "Listar las 16 comunas de Medellín"),
    BotCommand("overview", "Resumen general (opcional: código de comuna)"),
    BotCommand("seguridad", "Estadísticas de criminalidad (opcional: año)"),
    BotCommand("salud", "Estadísticas de natalidad (opcional: año)"),
    BotCommand("educacion", "Establecimientos educativos (opcional: comuna)"),
    BotCommand("ambiente", "Residuos sólidos (opcional: año)"),
    BotCommand("calidad", "Índice de Calidad de Vida (opcional: comuna)"),
    BotCommand("comparar", "Comparar comunas — ej: /comparar 01,04,09"),
]

HELP_TEXT = (
    "*MedCity Dashboard Bot* 🏙\n"
    "Consulta datos abiertos de Medellín directamente desde Telegram.\n\n"
    "*Comandos disponibles:*\n"
    "/comunas — Listar las 16 comunas\n"
    "/overview `[comuna]` — Resumen general\n"
    "/seguridad `[año]` — Criminalidad consolidada\n"
    "/salud `[año]` — Estadísticas de natalidad\n"
    "/educacion `[comuna]` — Establecimientos educativos\n"
    "/ambiente `[año]` — Residuos sólidos\n"
    "/calidad `[comuna]` — Índice Calidad de Vida\n"
    "/comparar `01,04,09` — Comparar comunas\n"
)


def _parse_int_arg(args: list[str], index: int = 0) -> Optional[int]:
    """Safely extract an integer argument from the command args."""
    if args and len(args) > index:
        try:
            return int(args[index])
        except ValueError:
            return None
    return None


def _parse_str_arg(args: list[str], index: int = 0) -> Optional[str]:
    """Safely extract a string argument from the command args."""
    if args and len(args) > index:
        return args[index].strip()
    return None


# ── Handlers ──────────────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "¡Hola! Soy el bot de *MedCity Dashboard*.\n\n"
        "Te permito consultar datos abiertos de Medellín "
        "(movilidad, seguridad, salud, educación, ambiente y calidad de vida).\n\n"
        "Escribe /help para ver los comandos disponibles.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def cmd_comunas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    comunas = await get_territory_comunas()
    lines = ["*Comunas de Medellín:*\n"]
    for c in comunas:
        lines.append(f"  `{c['code']}` — {c['name']}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    comuna_code = _parse_str_arg(context.args) or "ALL"
    year = _parse_int_arg(context.args, index=1)
    try:
        data = await get_dashboard_overview(comuna_code=comuna_code, year=year)
        # data is an OverviewResponse pydantic model
        d = data.model_dump() if hasattr(data, "model_dump") else data.dict()

        label = f"comuna *{comuna_code}*" if comuna_code != "ALL" else "toda la ciudad"
        lines = [f"📊 *Resumen* — {label}\n"]

        if d.get("mobility"):
            mob = d["mobility"]
            lines.append(f"🚗 *Movilidad* (año {mob.get('year', '?')}):")
            lines.append(f"  Vehículos equiv.: {mob.get('total_vehicles', 'N/D'):,}")

        if d.get("safety"):
            saf = d["safety"]
            lines.append(f"🔒 *Seguridad* (año {saf.get('year', '?')}):")
            lines.append(f"  Homicidios: {saf.get('homicides', 'N/D'):,}")

        if d.get("investment"):
            inv = d["investment"]
            lines.append(f"💰 *Inversión* (año {inv.get('year', '?')}):")
            total = inv.get("total_investment", 0)
            lines.append(f"  Total: ${total:,.0f}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /overview")
        await update.message.reply_text(f"Error al consultar overview: {exc}")


async def cmd_seguridad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    year = _parse_int_arg(context.args)
    try:
        data = await get_criminalidad_consolidada(year=year)
        if not data.get("available"):
            await update.message.reply_text("Datos de criminalidad no disponibles.")
            return

        lines = [f"🔒 *Criminalidad consolidada*"]
        if year:
            lines[0] += f" — {year}"
        lines.append("")

        for item in data.get("by_type", [])[:10]:
            tipo = item.get("crime_type", "?")
            total = item.get("total", 0)
            lines.append(f"  • {tipo}: {total:,}")

        years = data.get("available_years", [])
        if years:
            lines.append(f"\nAños disponibles: {years[0]}–{years[-1]}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /seguridad")
        await update.message.reply_text(f"Error al consultar seguridad: {exc}")


async def cmd_salud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    year = _parse_int_arg(context.args)
    try:
        data = await get_natalidad(year=year)
        if not data.get("available"):
            await update.message.reply_text("Datos de natalidad no disponibles.")
            return

        lines = ["🏥 *Natalidad*"]
        if data.get("latest_year"):
            lines[0] += f" — {data['latest_year']}"
        lines.append("")
        lines.append(f"Total nacimientos: {data.get('total_nacimientos', 'N/D'):,}")

        by_sex = data.get("by_sex", [])
        for s in by_sex:
            lines.append(f"  • {s.get('sex', '?')}: {s.get('count', 0):,}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /salud")
        await update.message.reply_text(f"Error al consultar salud: {exc}")


async def cmd_educacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    comuna_code = _parse_str_arg(context.args)
    try:
        data = await get_establecimientos(comuna_code=comuna_code)
        if not data.get("available"):
            await update.message.reply_text("Datos de educación no disponibles.")
            return

        label = f"comuna *{comuna_code}*" if comuna_code else "toda la ciudad"
        lines = [f"📚 *Establecimientos educativos* — {label}\n"]
        lines.append(f"Total: {data.get('total', 'N/D'):,}")

        by_type = data.get("by_modalidad", data.get("by_type", []))
        for item in by_type[:8]:
            name = item.get("modalidad", item.get("type", "?"))
            count = item.get("count", 0)
            lines.append(f"  • {name}: {count:,}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /educacion")
        await update.message.reply_text(f"Error al consultar educación: {exc}")


async def cmd_ambiente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    year = _parse_int_arg(context.args)
    try:
        data = await get_residuos_solidos(year=year)
        if not data.get("available"):
            await update.message.reply_text("Datos de residuos sólidos no disponibles.")
            return

        lines = ["♻️ *Residuos sólidos*"]
        if data.get("latest_year"):
            lines[0] += f" — {data['latest_year']}"
        lines.append("")
        lines.append(f"Total (kg): {data.get('total_kg', 'N/D'):,}")

        by_type = data.get("by_type", [])
        for item in by_type[:8]:
            name = item.get("type", "?")
            kg = item.get("total_kg", 0)
            lines.append(f"  • {name}: {kg:,.0f} kg")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /ambiente")
        await update.message.reply_text(f"Error al consultar ambiente: {exc}")


async def cmd_calidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    comuna_code = _parse_str_arg(context.args)
    year = _parse_int_arg(context.args, index=1)
    try:
        data = await get_imcv(year=year, comuna_code=comuna_code)
        if not data.get("available"):
            await update.message.reply_text("Datos de calidad de vida no disponibles.")
            return

        label = f"comuna *{comuna_code}*" if comuna_code else "toda la ciudad"
        lines = [f"📈 *Índice de Calidad de Vida (IMCV)* — {label}\n"]
        if data.get("latest_year"):
            lines.append(f"Año: {data['latest_year']}")

        by_comuna = data.get("by_comuna", [])
        for item in by_comuna[:16]:
            name = item.get("comuna", "?")
            value = item.get("imcv", 0)
            lines.append(f"  • {name}: {value:.2f}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /calidad")
        await update.message.reply_text(f"Error al consultar calidad de vida: {exc}")


async def cmd_comparar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = _parse_str_arg(context.args)
    if not raw:
        await update.message.reply_text(
            "Uso: /comparar `01,04,09`\n"
            "Separa los códigos de comuna con comas.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    codes = [c.strip() for c in raw.split(",") if c.strip()]
    try:
        data = await get_dashboard_compare(comunas=codes)
        lines = [f"⚖️ *Comparación* — comunas {', '.join(codes)}\n"]

        for entry in data.get("results", data.get("comunas", [])):
            code = entry.get("comuna_code", entry.get("code", "?"))
            name = entry.get("comuna_name", entry.get("name", code))
            lines.append(f"*{code} — {name}*")

            mob = entry.get("mobility", {})
            if mob:
                lines.append(f"  🚗 Vehículos: {mob.get('total_vehicles', 'N/D'):,}")

            saf = entry.get("safety", {})
            if saf:
                lines.append(f"  🔒 Homicidios: {saf.get('homicides', 'N/D'):,}")

            inv = entry.get("investment", {})
            if inv:
                total = inv.get("total_investment", 0)
                lines.append(f"  💰 Inversión: ${total:,.0f}")
            lines.append("")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        logger.exception("Error in /comparar")
        await update.message.reply_text(f"Error al comparar comunas: {exc}")


# ── Application factory ──────────────────────────────────────────────────


async def _post_init(application: Application) -> None:
    """Register bot commands in the Telegram menu."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot commands registered with Telegram.")


def create_bot() -> Application:
    """Build and return the Telegram Application (not yet running)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Get a token from @BotFather on Telegram."
        )

    app = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("comunas", cmd_comunas))
    app.add_handler(CommandHandler("overview", cmd_overview))
    app.add_handler(CommandHandler("seguridad", cmd_seguridad))
    app.add_handler(CommandHandler("salud", cmd_salud))
    app.add_handler(CommandHandler("educacion", cmd_educacion))
    app.add_handler(CommandHandler("ambiente", cmd_ambiente))
    app.add_handler(CommandHandler("calidad", cmd_calidad))
    app.add_handler(CommandHandler("comparar", cmd_comparar))

    return app
