from dotenv import load_dotenv
import os
import logging
from threading import Thread

from telegram import (
    Update,
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler, 
    CallbackQueryHandler,
    ConversationHandler, 
    MessageHandler, 
    ContextTypes, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# from languages import translations

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional keep-alive webserver (for Replit)
try:
    from flask import Flask  # type: ignore
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

# import environment variable from .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
import json
import tempfile

# ---------------- Google Sheets Setup ----------------
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not GOOGLE_CREDENTIALS_JSON:
    raise ValueError("❌ Missing GOOGLE_CREDENTIALS_JSON environment variable")

# Create a temporary file to hold the credentials content
with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_json:
    temp_json.write(GOOGLE_CREDENTIALS_JSON)
    temp_json.flush()
    creds = ServiceAccountCredentials.from_json_keyfile_name(temp_json.name, [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ])

client = gspread.authorize(creds)

# Try connecting to your Google Sheet
try:
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    print("✅ Connected to Google Sheet successfully!")
except Exception as e:
    print("❌ Error connecting to Google Sheet:", e)

# GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
# GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")

# # ---------------- Google Sheets Setup ----------------
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_PATH, scope)
# client = gspread.authorize(creds)
# # sheet = client.open("Jundullah Members").sheet1


# # ========================= Connect to Google Sheet =========================
# try:
#     sheet = client.open(GOOGLE_SHEET_NAME).sheet1
#     print("✅ Connected to Google Sheet successfully!")
#     # print(sheet.get_all_records())
# except Exception as e:
#     print("❌ Error connecting to Google Sheet:", e)


# ---------------------------
# Keep-alive server 
# If Flask is available we start a simple server on port 8080 (Replit friendly).
# ---------------------------
if FLASK_AVAILABLE:
    flask_app = Flask("keepalive")

    @flask_app.route("/")
    def home():
        return "🤖 Jundullah Assistant Bot is alive"

    def run_flask():
        flask_app.run(host="0.0.0.0", port=8080)

    # start flask in a thread so it doesn't block the bot
    Thread(target=run_flask, daemon=True).start()
else:
    logger.info("Flask not available; keep-alive webserver disabled. Install flask to enable it.")


# ---------------- Conversation States ----------------
(
    MAIN_MENU, INFO_MENU, REGISTER_ELIGIBLE,
    REG_NAME, REG_PHONE, REG_EMAIL, REG_ADDRESS,
    REG_PROF, REG_PURPOSE, REG_ACCEPT
) = range(10)


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await start(update, context)


# ---------------- Start / Main Menu ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📘 Learn About Jundullah", callback_data="learn")],
        [InlineKeyboardButton("🧾 Register as a Member", callback_data="register")],
        [InlineKeyboardButton("📞 Contact Us", callback_data="contact")]
    ]

    text = (
        "As-salamu alaykum and welcome to the *Jundullah Charitable Association.*\n\n"
        "I am here to help you learn about our association and guide you through the membership registration process.\n\n"
        "Please choose an option below:"
    )

    # Support both message and callback
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    return MAIN_MENU



# ---------------- Handle Main Menu ----------------
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "learn":
        submenu = [
            [InlineKeyboardButton("🎯 Our Objectives", callback_data="obj")],
            [InlineKeyboardButton("🏗️ Our Activities", callback_data="act")],
            [InlineKeyboardButton("🏛️ Our Structure", callback_data="struct")],
            [InlineKeyboardButton("⚖️ Member Rights & Duties", callback_data="rights")],
            # this Back goes to back_main (not 'learn')
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]

        await query.edit_message_text(
            "What would you like to know?",
            reply_markup=InlineKeyboardMarkup(submenu)
        )
        return INFO_MENU

    elif query.data == "register":
        keyboard = [
            [InlineKeyboardButton("✅ Yes, proceed", callback_data="yes_reg")],
            # back_main here so pressing it returns to main
            [InlineKeyboardButton("❌ No, go back", callback_data="back_main")]
        ]

        await query.edit_message_text(
            "Thank you for your interest in joining *Jundullah Charitable Association.*\n\n"
            "To be eligible, you must be an Ethiopian national who accepts the objectives and bylaws of the Association.\n\n"
            "Do you wish to proceed with registration?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REGISTER_ELIGIBLE

    elif query.data == "contact":
        back_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main")]
        ])
        await query.edit_message_text(
            "📞 *Contact Us*\n\n"
            "Email: Junudullahcharity@gmail.com\n"
            "Phone: +251-937-067-800\n"
            "Address: Addis Ababa, Ethiopia",
            parse_mode="Markdown",
            reply_markup=back_btn
        )
        return MAIN_MENU




# ---------------- Info Menu ----------------
async def info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    info = {
        "obj": "📘 *Our Objectives:*\n• Provide humanitarian assistance.\n• Support education, health, and livelihood.\n• Promote self-reliance.\n• Undertake lawful charitable works.",
        "act": "🏗️ *Our Activities:*\n• Mobilize donations & grants.\n• Implement development projects.\n• Collaborate with partners.\n• Conduct awareness programs.",
        "struct": "🏛️ *Our Structure:*\n• Founding Members: 33\n• General Assembly → Supreme body\n• Board → 7 elected members\n• Executive Committee → Daily management\n• Audit Committee → Oversight",
        "rights": "⚖️ *Rights & Duties:*\n\n*Rights:*\n• Attend & vote\n• Elect or be elected\n• Access information\n\n*Duties:*\n• Follow bylaws\n• Pay fees\n• Protect our name"
    }

    # If user selected an info item, show the page and a Back-to-Learn button
    if query.data in info:
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_learn")]])
        await query.edit_message_text(info[query.data], parse_mode="Markdown", reply_markup=back_btn)
        return INFO_MENU

    # If user clicked the Back-to-main button from the learn submenu
    if query.data == "back_main":
        return await back_to_main(update, context)

    # If user clicked the back_learn button to return to the learn submenu
    if query.data == "back_learn":
        # build the learn submenu again
        submenu = [
            [InlineKeyboardButton("🎯 Our Objectives", callback_data="obj")],
            [InlineKeyboardButton("🏗️ Our Activities", callback_data="act")],
            [InlineKeyboardButton("🏛️ Our Structure", callback_data="struct")],
            [InlineKeyboardButton("⚖️ Member Rights & Duties", callback_data="rights")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]
        await query.edit_message_text("What would you like to know?", reply_markup=InlineKeyboardMarkup(submenu))
        return INFO_MENU

    return INFO_MENU




# ---------------- Registration Flow ----------------
async def register_eligibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "no_reg":
        await query.edit_message_text("Thank you. You can always register later from the main menu.")
        return ConversationHandler.END

    if query.data == "yes_reg":
        await query.edit_message_text("Please enter your *Full Name (as per ID):*", parse_mode="Markdown")
        return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Please enter your *Phone Number:*", parse_mode="Markdown")
    return REG_PHONE


async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    await update.message.reply_text("Please enter your *Email Address:*", parse_mode="Markdown")
    return REG_EMAIL


async def reg_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Please enter your *Full Address (Sub-City, Woreda):*", parse_mode="Markdown")
    return REG_ADDRESS


async def reg_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("Please state your *Profession:*", parse_mode="Markdown")
    return REG_PROF


async def reg_prof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profession"] = update.message.text
    await update.message.reply_text("Why do you wish to join Jundullah? *(Brief Statement of Purpose)*", parse_mode="Markdown")
    return REG_PURPOSE


async def reg_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["purpose"] = update.message.text
    keyboard = [
        [InlineKeyboardButton("✅ Yes, I Accept", callback_data="accept_yes")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="accept_no")]
    ]
    await update.message.reply_text(
        "By submitting this application, you declare that you have read and accept the objectives and bylaws.\n\nDo you accept?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return REG_ACCEPT


async def reg_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "accept_no":
        await query.edit_message_text("You must accept the bylaws to become a member. Please try again later.")
        return ConversationHandler.END

    # Save data to Google Sheet
    data = [
        context.user_data["name"], 
        context.user_data["phone"],
        context.user_data["email"], 
        context.user_data["address"],
        context.user_data["profession"], 
        context.user_data["purpose"]
    ]
    sheet.append_row(data)

    summary = (
        f"✅ *Registration Complete!*\n\n"
        f"Name: {data[0]}\nPhone: {data[1]}\nEmail: {data[2]}\nAddress: {data[3]}\n"
        f"Profession: {data[4]}\nPurpose: {data[5]}\n\n"
        "Your application will be reviewed by the Board of Directors.\n"
        "May Allah accept your good intentions."
    )
    await query.edit_message_text(summary, parse_mode="Markdown")

    # Show main menu again — single Back button
    back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]])
    await query.message.reply_text("🏠 Back to main menu:", reply_markup=back_markup)

    return ConversationHandler.END


# ---------------- Main Function ----------------
def main():
    # app = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],

    states={
        MAIN_MENU: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(main_menu)
        ],

        INFO_MENU: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(info_menu)
        ],

        REGISTER_ELIGIBLE: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(register_eligibility)
        ],

        REG_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
        REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone)],
        REG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_email)],
        REG_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_address)],
        REG_PROF: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_prof)],
        REG_PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_purpose)],

        REG_ACCEPT: [
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CallbackQueryHandler(reg_accept)
        ],
    },

    fallbacks=[CommandHandler("start", start)],
)


    app.add_handler(conv_handler)
    # app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    # app.add_handler()
    # app.add_handler(CommandHandler("language", language))
    # app.add_handler(CallbackQueryHandler(language_button, pattern=r"^lang_"))

    print("🤖 Jundullah Assistant is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
