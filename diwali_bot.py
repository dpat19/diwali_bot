import os
import json
import base64
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Google Sheets Setup ---
# Decode credentials from environment variable
creds_b64 = os.environ['GOOGLE_CREDS_B64']
creds_json = base64.b64decode(creds_b64)
creds_dict = json.loads(creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Food Request Diwali").sheet1

# --- Conversation states ---
DEPARTMENT, VOLUNTEERS = range(2)
departments = ["Kitchen", "Flow", "Shayona", "Signs"]

# --- Telegram Handlers ---
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

    # Save to Google Sheet
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

# --- Main Application ---
def main():
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
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
    app.run_polling()

if __name__ == "__main__":
    main()
