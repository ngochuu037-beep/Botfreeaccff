# ============================================================
# BOT MIGUEL FF — File chính
# Tác giả: [Tên bạn]
# Admin: 8432658618
# ============================================================

# ---------- PHẦN 2.1: IMPORT ----------
import os
import time
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ---------- PHẦN 2.2: CẤU HÌNH ----------
TOKEN = os.getenv("8256418029:AAHWnLrQ_BfKVP9AT1PRaBaCET-RSbEULQU")

ADMIN_IDS = {
    8432658618,   # admin chính
    # 111111111,  # thêm admin phụ
}
if os.getenv("ADMIN_IDS"):
    ADMIN_IDS |= {int(x) for x in os.getenv("ADMIN_IDS").split(",") if x.strip()}

GROUP_ID = -1003365347708
GROUP_LINK = "https://t.me/+-_Ylhi8u5PA1Nzhl"

DB_FILE = os.getenv("DB_PATH", "bot.db")
if DB_FILE.startswith("/data") and not os.path.isdir("/data"):
    DB_FILE = "bot.db"

COINS_PER_REF = 1
REFUND_ON_REJECT = True

GIFTS = {
    "acc_lv5": {
        "name": "Acc Clone TikTok LV5",
        "cost": 10,
        "emoji": "🎮",
        "desc": "Tài khoản clone TikTok level 5",
    },
    "key_miguel": {
        "name": "Key Miguel",
        "cost": 20,
        "emoji": "🔑",
        "desc": "Key kích hoạt Miguel",
    },
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ---------- PHẦN 2.3: DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            coins       INTEGER DEFAULT 0,
            invited_by  INTEGER,
            claimed     INTEGER DEFAULT 0,
            claim_time  INTEGER DEFAULT 0,
            handled_by  INTEGER DEFAULT 0,
            gift_type   TEXT    DEFAULT '',
            gift_cost   INTEGER DEFAULT 0
        )
    """)
    cur.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in cur.fetchall()}
    for col, ddl in [
        ("full_name", "ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''"),
        ("handled_by", "ALTER TABLE users ADD COLUMN handled_by INTEGER DEFAULT 0"),
        ("gift_type", "ALTER TABLE users ADD COLUMN gift_type TEXT DEFAULT ''"),
        ("gift_cost", "ALTER TABLE users ADD COLUMN gift_cost INTEGER DEFAULT 0"),
    ]:
        if col not in cols:
            cur.execute(ddl)
    conn.commit()
    conn.close()


def get_user(uid):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, username, coins, invited_by, claimed, claim_time, "
        "full_name, handled_by, gift_type, gift_cost FROM users WHERE user_id = ?",
        (uid,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def create_user(uid, username, full_name="", invited_by=None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, full_name, coins, invited_by, claimed)
        VALUES (?, ?, ?, 0, ?, 0)
    """, (uid, username, full_name, invited_by))
    conn.commit()
    conn.close()


def add_coins(uid, amount):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, uid))
    conn.commit()
    conn.close()


def deduct_coins(uid, amount):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET coins = coins - ? WHERE user_id = ? AND coins >= ?",
        (amount, uid, amount)
    )
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def set_claim(uid, status, gift_type="", gift_cost=0, admin_id=0):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET claimed = ?, claim_time = ?, gift_type = ?, "
        "gift_cost = ?, handled_by = ? WHERE user_id = ?",
        (status, int(time.time()), gift_type, gift_cost, admin_id, uid)
    )
    conn.commit()
    conn.close()


def list_pending():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, username, full_name, claim_time, gift_type, gift_cost "
        "FROM users WHERE claimed = 1 ORDER BY claim_time ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def count_all_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    n = cur.fetchone()[0]
    conn.close()
    return n


def count_done_claims():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE claimed = 2")
    n = cur.fetchone()[0]
    conn.close()
    return n


# ---------- PHẦN 2.4: TIỆN ÍCH ----------
def is_admin(uid):
    return uid in ADMIN_IDS


async def is_member(bot, uid):
    try:
        m = await bot.get_chat_member(GROUP_ID, uid)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def notify_admins(context, text, reply_markup=None):
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id, text=text,
                reply_markup=reply_markup, parse_mode="HTML",
            )
        except Exception as e:
            log.warning("Không gửi được admin %s: %s", admin_id, e)


def user_label(uid, username, full_name):
    name = full_name or "(không tên)"
    uname = f"@{username}" if username else "(no username)"
    return f"{name} | {uname} | ID: <code>{uid}</code>"


def gift_label(key):
    g = GIFTS.get(key)
    return f"{g['emoji']} {g['name']}" if g else "(không rõ)"


def build_gift_menu():
    rows = [
        [InlineKeyboardButton(
            f"{g['emoji']} {g['name']} — {g['cost']} xu",
            callback_data=f"gift:{key}"
        )]
        for key, g in GIFTS.items()
    ]
    rows.append([InlineKeyboardButton("⬅️ Đóng", callback_data="close_menu")])
    return InlineKeyboardMarkup(rows)


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Tham gia Group", url=GROUP_LINK)],
        [InlineKeyboardButton("🔍 Kiểm tra", callback_data="check_join")],
        [InlineKeyboardButton("👥 Link mời bạn", callback_data="ref")],
        [InlineKeyboardButton("💰 Số xu", callback_data="coins")],
        [InlineKeyboardButton("🎁 Đổi quà", callback_data="gift_menu")],
    ])


# ---------- PHẦN 2.5: USER HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    invited_by = None
    if context.args:
        try:
            ref = int(context.args[0])
            if ref != uid:
                invited_by = ref
        except ValueError:
            pass

    old = get_user(uid)
    if old is None:
        create_user(uid, user.username or "", user.full_name or "", invited_by)
        if invited_by and get_user(invited_by):
            add_coins(invited_by, COINS_PER_REF)
            try:
                await context.bot.send_message(
                    chat_id=invited_by,
                    text=f"🎉 Có người mời thành công!\n💰 +{COINS_PER_REF} xu",
                )
            except Exception:
                pass

    gift_lines = "\n".join(
        f"  {g['emoji']} {g['name']} — <b>{g['cost']} xu</b>"
        for g in GIFTS.values()
    )

    await update.message.reply_text(
        "🎁 <b>QUÀ TẶNG MIGUEL FF</b> 🎁\n\n"
        f"👥 Mời 1 bạn = +{COINS_PER_REF} xu\n\n"
        f"📦 <b>Danh sách quà:</b>\n{gift_lines}\n\n"
        "⚠️ Bạn cần tham gia group trước.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_member(context.bot, q.from_user.id):
        await q.message.reply_text(
            "✅ Bạn đã tham gia group!\n\n"
            f"👥 Mời 1 bạn = +{COINS_PER_REF} xu\n"
            "🎁 Bấm <b>Đổi quà</b> để xem phần thưởng.",
            parse_mode="HTML",
        )
    else:
        kb = [[InlineKeyboardButton("📢 Tham gia Group", url=GROUP_LINK)]]
        await q.message.reply_text(
            "❌ Bạn chưa tham gia group!\nVui lòng join rồi bấm lại.",
            reply_markup=InlineKeyboardMarkup(kb),
        )


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={q.from_user.id}"
    await q.message.reply_text(
        "👥 <b>LINK MỜI BẠN</b>\n\n"
        f"{link}\n\n"
        f"🎁 Mời 1 bạn = +{COINS_PER_REF} xu",
        parse_mode="HTML",
    )


async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    row = get_user(q.from_user.id)
    coin = row[2] if row else 0

    lines = []
    for key, g in GIFTS.items():
        can = "✅" if coin >= g["cost"] else "❌"
        lines.append(f"  {can} {g['emoji']} {g['name']} — {g['cost']} xu")

    await q.message.reply_text(
        f"💰 <b>SỐ XU CỦA BẠN</b>\n\n"
        f"🪙 Xu hiện tại: <b>{coin}</b>\n\n"
        f"📦 <b>Có thể đổi:</b>\n" + "\n".join(lines),
        parse_mode="HTML",
    )


async def gift_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    row = get_user(q.from_user.id)
    coin = row[2] if row else 0
    await q.message.reply_text(
        f"🎁 <b>CHỌN LOẠI QUÀ</b>\n\n🪙 Xu: <b>{coin}</b>",
        reply_markup=build_gift_menu(),
        parse_mode="HTML",
    )


async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        await q.message.delete()
    except Exception:
        pass


async def gift_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, key = q.data.split(":", 1)
    if key not in GIFTS:
        return
    g = GIFTS[key]
    row = get_user(q.from_user.id)
    coin, claimed = (row[2], row[4]) if row else (0, 0)

    if claimed == 1:
        await q.message.reply_text("⏳ Bạn đang chờ admin xử lý.")
        return
    if claimed == 2:
        await q.message.reply_text("✅ Bạn đã nhận quà rồi.")
        return
    if coin < g["cost"]:
        await q.message.reply_text(
            f"❌ Chưa đủ xu!\n\n"
            f"🎁 {g['emoji']} {g['name']} — cần <b>{g['cost']} xu</b>\n"
            f"💰 Bạn có: <b>{coin} xu</b>\n"
            f"📩 Cần mời thêm <b>{g['cost'] - coin}</b> người.",
            parse_mode="HTML",
        )
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm:{key}"),
        InlineKeyboardButton("❌ Hủy", callback_data="close_menu"),
    ]])
    await q.message.reply_text(
        f"⚠️ <b>XÁC NHẬN ĐỔI QUÀ</b>\n\n"
        f"🎁 {g['emoji']} <b>{g['name']}</b>\n"
        f"💰 Giá: <b>{g['cost']} xu</b>\n"
        f"🪙 Còn lại: <b>{coin - g['cost']} xu</b>\n\n"
        f"📝 {g['desc']}\n\nBạn chắc chắn?",
        reply_markup=kb,
        parse_mode="HTML",
    )


async def gift_do_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, key = q.data.split(":", 1)
    if key not in GIFTS:
        return

    user = q.from_user
    uid = user.id
    g = GIFTS[key]
    cost = g["cost"]

    row = get_user(uid)
    coin, claimed = (row[2], row[4]) if row else (0, 0)

    if claimed == 1:
        await q.message.reply_text("⏳ Đang chờ xử lý.")
        return
    if claimed == 2:
        await q.message.reply_text("✅ Bạn đã nhận quà rồi.")
        return
    if coin < cost:
        await q.message.reply_text("❌ Không đủ xu.")
        return
    if not deduct_coins(uid, cost):
        await q.message.reply_text("❌ Lỗi trừ xu.")
        return

    set_claim(uid, 1, key, cost)

    await q.message.reply_text(
        f"🎉 <b>ĐỔI QUÀ THÀNH CÔNG!</b>\n\n"
        f"🎁 {g['emoji']} <b>{g['name']}</b>\n"
        f"💰 Đã trừ: <b>{cost} xu</b>\n"
        f"🪙 Còn: <b>{coin - cost} xu</b>\n\n"
        "⏳ Admin sẽ gửi quà sớm. Vui lòng chờ.",
        parse_mode="HTML",
    )

    label = user_label(uid, user.username, user.full_name or "")
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Đã gửi quà", callback_data=f"approve:{uid}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"reject:{uid}"),
        ],
        [InlineKeyboardButton("💬 Nhắn cho user", url=f"tg://user?id={uid}")],
    ])
    await notify_admins(
        context,
        "🎁 <b>YÊU CẦU ĐỔI QUÀ MỚI</b>\n\n"
        f"👤 {label}\n"
        f"🎁 {g['emoji']} <b>{g['name']}</b>\n"
        f"💰 Đã trừ: <b>{cost} xu</b>\n"
        f"🕒 {time.strftime('%H:%M:%S %d/%m/%Y')}",
        reply_markup=admin_kb,
    )


# ---------- PHẦN 2.6: ADMIN HANDLERS ----------
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    admin_id = q.from_user.id

    if not is_admin(admin_id):
        await q.answer("⛔ Không có quyền.", show_alert=True)
        return

    try:
        action, uid_str = q.data.split(":")
        uid = int(uid_str)
    except Exception:
        await q.answer("Lỗi dữ liệu.", show_alert=True)
        return

    row = get_user(uid)
    if row is None:
        await q.answer("Không tìm thấy user.", show_alert=True)
        return

    claimed = row[4]
    gkey = row[8] or ""
    cost = row[9] or 0
    g = GIFTS.get(gkey)
    g_name = g["name"] if g else "?"

    if action == "approve":
        if claimed == 2:
            await q.answer("Đã duyệt rồi.", show_alert=True)
            return
        set_claim(uid, 2, gkey, cost, admin_id)
        try:
            await q.edit_message_text(
                (q.message.text or "") +
                f"\n\n✅ <b>ĐÃ GỬI</b> bởi <code>{admin_id}</code>\n"
                f"🕒 {time.strftime('%H:%M:%S %d/%m/%Y')}",
                parse_mode="HTML",
            )
        except Exception:
            pass
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    f"🎉 <b>QUÀ ĐÃ GỬI!</b>\n\n"
                    f"🎁 {g['emoji']} <b>{g_name}</b>\n\n"
                    "Kiểm tra tin nhắn từ admin nhé!"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            log.warning("Không nhắn được user: %s", e)
        await q.answer("✅ Đã duyệt.")
        return

    if action == "reject":
        if claimed != 1:
            await q.answer("Không ở trạng thái chờ.", show_alert=True)
            return
        refund_msg = ""
        if REFUND_ON_REJECT:
            add_coins(uid, cost)
            refund_msg = f"\n💰 Đã hoàn <b>{cost} xu</b>."
        set_claim(uid, 0, "", 0, admin_id)
        try:
            await q.edit_message_text(
                (q.message.text or "") +
                f"\n\n❌ <b>TỪ CHỐI</b> bởi <code>{admin_id}</code>{refund_msg}\n"
                f"🕒 {time.strftime('%H:%M:%S %d/%m/%Y')}",
                parse_mode="HTML",
            )
        except Exception:
            pass
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    f"❌ <b>Yêu cầu bị từ chối.</b>\n\n"
                    f"🎁 {g['emoji']} {g_name}\n"
                    + (f"💰 Đã hoàn <b>{cost} xu</b>.\n" if REFUND_ON_REJECT else "")
                    + "Liên hệ admin nếu thắc mắc."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            log.warning("Không nhắn được user: %s", e)
        await q.answer("❌ Đã từ chối." + (" Hoàn xu." if REFUND_ON_REJECT else ""))


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    rows = list_pending()
    if not rows:
        await update.message.reply_text("✅ Không có yêu cầu nào chờ.")
        return
    now = int(time.time())
    lines = ["📋 <b>DANH SÁCH CHỜ GỬI</b>\n"]
    for uid, uname, fname, t, gkey, gcost in rows:
        lines.append(
            f"• {user_label(uid, uname, fname)}\n"
            f"   🎁 {gift_label(gkey)} ({gcost} xu)\n"
            f"   ⏳ {now - t}s trước"
        )
    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Cú pháp: /done <user_id>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user_id phải là số.")
        return
    row = get_user(uid)
    if row is None or row[4] != 1:
        await update.message.reply_text("User không ở trạng thái chờ.")
        return
    set_claim(uid, 2, row[8] or "", row[9] or 0, update.effective_user.id)
    await update.message.reply_text(f"✅ Đã duyệt user {uid}.")
    try:
        await context.bot.send_message(chat_id=uid, text="🎉 Quà đã gửi!")
    except Exception:
        pass


async def cmd_addcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Cú pháp: /addcoin <user_id> <số_xu>")
        return
    try:
        uid = int(context.args[0]); amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Tham số phải là số.")
        return
    if get_user(uid) is None:
        create_user(uid, "")
    add_coins(uid, amount)
    await update.message.reply_text(f"✅ Đã cộng {amount} xu cho {uid}.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "📊 <b>THỐNG KÊ</b>\n\n"
        f"👥 Tổng user: <b>{count_all_users()}</b>\n"
        f"⏳ Đang chờ: <b>{len(list_pending())}</b>\n"
        f"✅ Đã gửi quà: <b>{count_done_claims()}</b>",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gift_lines = "\n".join(
        f"  {g['emoji']} {g['name']} — <b>{g['cost']} xu</b>"
        for g in GIFTS.values()
    )
    await update.message.reply_text(
        "📖 <b>HƯỚNG DẪN</b>\n\n"
        "/start — Bắt đầu\n"
        "/doi_qua — Đổi quà\n"
        "/help — Trợ giúp\n\n"
        f"👥 Mời 1 bạn = +{COINS_PER_REF} xu\n\n"
        f"📦 <b>Quà hiện có:</b>\n{gift_lines}",
        parse_mode="HTML",
    )


async def cmd_doi_qua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = get_user(update.effective_user.id)
    coin = row[2] if row else 0
    await update.message.reply_text(
        f"🎁 <b>CHỌN LOẠI QUÀ</b>\n\n🪙 Xu hiện tại: <b>{coin}</b>",
        reply_markup=build_gift_menu(),
        parse_mode="HTML",
    )


# ---------- PHẦN 2.7: MAIN ----------
def main():
    if not TOKEN:
        print("❌ Chưa có BOT_TOKEN.")
        return
    init_db()
    log.info("Admin: %s", ADMIN_IDS)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("doi_qua", cmd_doi_qua))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("addcoin", cmd_addcoin))
    app.add_handler(CommandHandler("stats", cmd_stats))

    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(referral, pattern="^ref$"))
    app.add_handler(CallbackQueryHandler(coins, pattern="^coins$"))
    app.add_handler(CallbackQueryHandler(gift_menu, pattern="^gift_menu$"))
    app.add_handler(CallbackQueryHandler(gift_confirm, pattern=r"^gift:[a-zA-Z0-9_]+$"))
    app.add_handler(CallbackQueryHandler(gift_do_claim, pattern=r"^confirm:[a-zA-Z0-9_]+$"))
    app.add_handler(CallbackQueryHandler(close_menu, pattern="^close_menu$"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern=r"^(approve|reject):\d+$"))

    print("🤖 Bot đang chạy...")
    app.run_polling()


if __name__ == "__main__":
    main()
