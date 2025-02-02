import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
import re
from datetime import datetime
import jdatetime

# تنظیم لاگر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن تلگرام
TELEGRAM_TOKEN = '7807825480:AAFFA5IFMDKiOgAGRYPg5W_RPM1lkEiqWIM'

def clean_price(price_text):
    """حذف کاراکترهای اضافی از قیمت"""
    if not price_text:
        return ""
    price = re.sub(r'[^\d.]', '', price_text)
    return f"{int(float(price)):,}" if price else ""

def get_contact_keyboard():
    """ایجاد دکمه‌های ارتباط با سازنده و قیمت‌ها"""
    keyboard = [
        [InlineKeyboardButton("💰 دریافت قیمت‌های لحظه‌ای", callback_data="get_prices")],
        [InlineKeyboardButton("📱 ارتباط با سازنده", url="https://t.me/svy000")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_prices():
    try:
        logger.info("Fetching prices from TGJU...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get('https://www.tgju.org', headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        prices = {
            'gold': [],
            'currency': [],
            'crypto': []
        }

        # دریافت همه جداول قیمت
        price_tables = soup.find_all('table', {'class': 'market-table'})

        for table in price_tables:
            for row in table.find_all('tr'):
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    name = cols[0].text.strip()
                    price = cols[1].text.strip()

                    if not name or not price:
                        continue

                    item = {
                        'name': name,
                        'price': clean_price(price),
                        'unit': 'ریال'
                    }

                    # دسته‌بندی قیمت‌ها
                    if any(keyword in name for keyword in ['سکه', 'طلا', 'عیار']):
                        prices['gold'].append(item)
                    elif any(keyword in name for keyword in ['دلار', 'یورو', 'پوند', 'درهم', 'لیر', 'یوان']):
                        prices['currency'].append(item)
                    elif any(keyword in name.lower() for keyword in ['بیت کوین', 'اتریوم', 'تتر', 'دوج']):
                        prices['crypto'].append(item)

        return prices
    except Exception as e:
        logger.error(f"Error in get_prices: {e}")
        return None

async def send_prices(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False) -> None:
    try:
        logger.info("Processing prices request...")

        # تشخیص نوع درخواست (دستور یا دکمه)
        if is_callback:
            status_message = await update.message.edit_text("در حال دریافت اطلاعات... ⏳")
        else:
            status_message = await update.message.reply_text("در حال دریافت اطلاعات... ⏳")

        data = get_prices()
        if data:
            message = "💰 قیمت‌های لحظه‌ای:\n\n"

            # نمایش طلا و سکه
            if data['gold']:
                message += "🏆 طلا و سکه:\n"
                for item in data['gold']:
                    message += f"• {item['name']}: {item['price']} ریال\n"
                message += "\n"

            # نمایش ارزها
            if data['currency']:
                message += "💵 ارز:\n"
                for item in data['currency']:
                    message += f"• {item['name']}: {item['price']} ریال\n"
                message += "\n"

            # نمایش ارزهای دیجیتال
            if data['crypto']:
                message += "₿ ارز دیجیتال:\n"
                for item in data['crypto']:
                    message += f"• {item['name']}: {item['price']} ریال\n"

            # اضافه کردن زمان به‌روزرسانی به هر دو صورت میلادی و شمسی
            current_time_miladi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_time_shamsi = jdatetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"\n⏰ به‌روزرسانی:\n📅 میلادی: {current_time_miladi}\n📅 شمسی: {current_time_shamsi}"

            if is_callback:
                await update.message.edit_text(
                    message,
                    reply_markup=get_contact_keyboard()
                )
            else:
                await status_message.edit_text(
                    message,
                    reply_markup=get_contact_keyboard()
                )
            logger.info("Prices sent successfully")
        else:
            error_message = "❌ خطا در دریافت اطلاعات. لطفا دوباره تلاش کنید."
            if is_callback:
                await update.message.edit_text(error_message)
            else:
                await status_message.edit_text(error_message)
            logger.error("Failed to fetch prices")

    except Exception as e:
        logger.error(f"Error in send_prices: {e}")
        error_message = "متأسفانه مشکلی در دریافت اطلاعات پیش آمده. لطفا دوباره تلاش کنید."
        if is_callback:
            await update.message.edit_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "get_prices":
        await send_prices(query, context, is_callback=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        welcome_message = (
            f"سلام {update.effective_user.first_name}! 👋\n\n"
            "به ربات قیمت ارز و طلا خوش آمدید.\n"
            "برای دریافت قیمت‌های لحظه‌ای، دستور /prices را ارسال کنید یا روی دکمه زیر کلیک کنید."
        )
        await update.message.reply_text(
            welcome_message,
            reply_markup=get_contact_keyboard()
        )
        logger.info(f"Start command used by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("متأسفانه مشکلی پیش آمده. لطفا دوباره تلاش کنید.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        help_text = (
            "🤖 راهنمای استفاده از ربات:\n\n"
            "📍 دستورات موجود:\n"
            "/start - شروع کار با ربات\n"
            "/prices - دریافت قیمت‌های لحظه‌ای\n"
            "/help - نمایش این راهنما\n\n"
            "⚠️ قیمت‌ها به صورت لحظه‌ای به‌روزرسانی می‌شوند.\n\n"
            "📱 برای ارتباط با سازنده روی دکمه زیر کلیک کنید."
        )
        await update.message.reply_text(
            help_text,
            reply_markup=get_contact_keyboard()
        )
        logger.info("Help command used")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("متأسفانه مشکلی پیش آمده. لطفا دوباره تلاش کنید.")

def main() -> None:
    try:
        logger.info("Bot is starting...")

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # اضافه کردن handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("prices", send_prices))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))

        logger.info("Starting polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Critical error: {e}")

if __name__ == '__main__':
    main()