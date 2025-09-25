from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os, json

# States for conversation
DEPARTMENT, VOLUNTEERS = range(2)

departments = ["Kitchen", "Flow", "Shayona", "Signs"]

# Connect to Google Sheets
# Scope for Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ New line: load credentials from Render secret file
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)

client = gspread.authorize(creds)
sheet = client.open("Food Request Diwali").sheet1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [[d] for d in departments]
    await update.message.reply_text(
        "Welcome! Please select your department:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return DEPARTMENT

async def department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["department"] = update.message.text
    await update.message.reply_text("How many volunteers will need food?")
    return VOLUNTEERS

async def volunteers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    department = context.user_data["department"]
    volunteers = update.message.text
    now = datetime.now()

    # Save to Google Sheet
    sheet.append_row([user.full_name, department, volunteers, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")])

    await update.message.reply_text("✅ Your request has been recorded. Thank you!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Request cancelled.")
    return ConversationHandler.END

def main():
    app = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN_HERE").build()

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
