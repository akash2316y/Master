#7889947993
import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPrivileges
from pyrogram.enums import ChatMemberStatus, ChatType

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ.get("OWNER_ID", 7889947993))

CHAT_FILE = "admin_chats.txt"

app = Client("multi-admin-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# --- Helper: Save chat id ---
def save_chat(chat_id: int):
    with open(CHAT_FILE, "a+") as f:
        f.seek(0)
        chats = f.read().splitlines()
        if str(chat_id) not in chats:
            f.write(f"{chat_id}\n")


# --- Trigger when bot added to a group/channel ---
@app.on_message(filters.new_chat_members)
async def when_added(client, message: Message):
    for member in message.new_chat_members:
        if member.is_self:
            save_chat(message.chat.id)


# --- Trigger when bot promoted as admin ---
@app.on_chat_member_updated()
async def track_admin(client, event):
    if event.new_chat_member and event.new_chat_member.user.is_self:
        if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            save_chat(event.chat.id)


# --- List admin chats ---
@app.on_message(filters.command("my_chats") & filters.user(OWNER_ID))
async def my_chats(_, m: Message):
    if not os.path.exists(CHAT_FILE):
        await m.reply_text("⚠️ Bot kahin bhi admin nahi hai.")
        return

    out = []
    with open(CHAT_FILE, "r") as f:
        chat_ids = f.read().splitlines()

    for cid in chat_ids:
        try:
            chat = await app.get_chat(int(cid))
            me = await app.get_me()
            member = await app.get_chat_member(int(cid), me.id)
            rights = []
            if member.privileges and member.privileges.can_promote_members:
                rights.append("👑 promote_members")
            if member.privileges and member.privileges.can_delete_messages:
                rights.append("🗑 delete_messages")
            if member.privileges and member.privileges.can_manage_chat:
                rights.append("⚙ manage_chat")

            out.append(
                f"**{chat.title or chat.id}** (`{cid}`)\n"
                f"Rights: {', '.join(rights) if rights else '❌ None'}"
            )
        except Exception:
            continue

    if out:
        await m.reply_text("📋 **Bot Admin Chats:**\n\n" + "\n\n".join(out), parse_mode="markdown")
    else:
        await m.reply_text("⚠️ Bot kahin bhi admin nahi hai.")


# --- Promote command ---
@app.on_message(filters.command("promote") & filters.user(OWNER_ID))
async def promote(_, m: Message):
    parts = m.text.split()
    if len(parts) < 3:
        await m.reply_text("Usage: /promote user_id chat_id", parse_mode="none")
        return

    user_ref = parts[1]
    chat_id = int(parts[2])

    try:
        # Resolve user
        if user_ref.startswith("@"):
            user = await app.get_users(user_ref)
        else:
            user = await app.get_users(int(user_ref))

        me = await app.get_me()
        bot_member = await app.get_chat_member(chat_id, me.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await m.reply_text("❌ Bot admin nahi hai.")
            return
        if not bot_member.privileges.can_promote_members:
            await m.reply_text("❌ Bot ke paas promote_members right nahi hai.")
            return

        # Promote
        new_privs = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_invite_users=True,
            can_pin_messages=True,
        )

        await app.promote_chat_member(chat_id, user.id, new_privs)
        await m.reply_text(f"✅ {user.mention} ko admin banaya gaya chat `{chat_id}` me.", parse_mode="none")

    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}", parse_mode="none")


@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text(
        "👋 Multi Admin Bot Ready!\n\n"
        "• /my_chats — Admin chats list kare (sirf owner)\n"
        "• /promote <user_id|@username> <chat_id> — Promote user (sirf owner)",
        parse_mode="none"
    )


if __name__ == "__main__":
    print("Bot started...")
    app.run()

