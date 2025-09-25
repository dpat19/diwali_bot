import os
import json
import base64
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Google Sheets Setup ---
creds_b64 = os.environ.get("GOOGLE_CREDS_B64")
if not creds_b64:
    raise ValueError("GOOGLE_CREDS_B64 environment variable not set!")

creds_json = base64.b64decode(creds_b64)
creds_dict = json.loads(creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_ID = "1fBLl8BFPlGYLmG8s_D9d17AbvOyltZWz5wqk1wcb-oA"
sheet = client.open_by_key(SHEET_ID).sheet1

# --- Telegram Setup ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TARGET_CHAT_ID")  # The chat you want to send scheduled messages to

# --- Conversation states ---
DEPARTMENT, VOLUNTEERS = range(2)
departments = ["Kitchen", "Flow", "Shayona", "Signs"]

# --- Conversation Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [[d] for d in departments]
    await update.message.reply_text(
        "Welcome! Please select your department:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return DEPARTMENT

async def department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text not in departments:
        await update.message.reply_text("Please select a valid department from the keyboard.")
        return DEPARTMENT
    context.user_data["department"] = text
    await update.message.reply_text("How many volunteers will need food?")
    return VOLUNTEERS

async def volunteers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Please enter a valid number.")
        return VOLUNTEERS

    user = update.message.from_user
    department = context.user_data["department"]
    volunteers_count = int(text)
    now = datetime.now()

    sheet.append_row([
        user.full_name,
        department,
        volunteers_count,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S")
    ])

    await update.message.reply_text("✅ Your request has been recorded. Thank you!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Request cancelled.")
    return ConversationHandler.END

# --- Temporary handler to get chat ID ---
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"This chat ID is: {chat_id}")

# --- Scheduled Reminder ---
async def send_reminder(application: Application):
    if not CHAT_ID:
        print("TARGET_CHAT_ID not set!")
        return
    await application.bot.send_message(
        chat_id=int(CHAT_ID),
        text="📢 Please fill out your volunteer food request form today!"
    )

def schedule_reminder(app: Application):
    scheduler = BackgroundScheduler(timezone="UTC")
    # Schedule the job every day at 09:00 UTC (adjust as needed)
    scheduler.add_job(lambda: app.create_task(send_reminder(app)), "cron", hour=9, minute=0)
    scheduler.start()

# --- Main ---
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, department)],
            VOLUNTEERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, volunteers)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    # Add temporary /getid handler
    app.add_handler(CommandHandler("getid", get_chat_id))

    # Schedule daily reminder
    schedule_reminder(app)

    app.run_polling()

if __name__ == "__main__":
    main()
