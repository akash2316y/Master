import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPrivileges
from pyrogram.enums import ChatMemberStatus

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ.get("OWNER_ID", 7889947993))  # <-- Apna TG ID yahan daalo

app = Client("multi-admin-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# --------- List All Admin Chats ---------
@app.on_message(filters.command("my_chats") & filters.user(OWNER_ID))
async def my_chats(_, m: Message):
    out = []
    async for dialog in app.get_dialogs():
        chat = dialog.chat
        try:
            member = await app.get_chat_member(chat.id, (await app.get_me()).id)
            if member.status == ChatMemberStatus.ADMINISTRATOR:
                rights = []
                if member.privileges.can_promote_members:
                    rights.append("👑 promote_members")
                if member.privileges.can_delete_messages:
                    rights.append("🗑 delete_messages")
                if member.privileges.can_manage_chat:
                    rights.append("⚙ manage_chat")
                if member.privileges.can_invite_users:
                    rights.append("➕ invite_users")
                if member.privileges.can_pin_messages:
                    rights.append("📌 pin_messages")

                out.append(
                    f"**{chat.title or chat.first_name}** (`{chat.id}`)\n"
                    f"Status: {member.status}\n"
                    f"Rights: {', '.join(rights) if rights else '❌ None'}"
                )
        except Exception:
            continue

    if not out:
        await m.reply_text("⚠️ Bot kahin bhi admin nahi hai.")
    else:
        await m.reply_text("📋 **Bot Admin Chats:**\n\n" + "\n\n".join(out))


# --------- Promote Command (Only Owner) ---------
@app.on_message(filters.command("promote") & filters.user(OWNER_ID))
async def promote(_, m: Message):
    """
    Usage: /promote <user_id|@username> <chat_id>
    Example: /promote @username -1001234567890
    """
    parts = m.text.split()
    if len(parts) < 3:
        await m.reply_text("Usage: `/promote <user_id|@username> <chat_id>`")
        return

    user_ref = parts[1]
    chat_id = int(parts[2])

    try:
        # Resolve user
        if user_ref.startswith("@"):
            user = await app.get_users(user_ref)
        else:
            user = await app.get_users(int(user_ref))

        # Check bot privileges
        me = await app.get_me()
        bot_member = await app.get_chat_member(chat_id, me.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await m.reply_text("❌ Bot admin nahi hai is chat me.")
            return
        if not bot_member.privileges.can_promote_members:
            await m.reply_text("❌ Bot ke paas 'promote_members' right nahi hai.")
            return

        # Promote with default safe privileges
        new_privs = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_invite_users=True,
            can_pin_messages=True,
        )

        await app.promote_chat_member(chat_id, user.id, new_privs)
        await m.reply_text(
            f"✅ {user.mention} ko admin banaya gaya chat `{chat_id}` me."
        )

    except Exception as e:
        await m.reply_text(f"⚠️ Error: `{e}`")


# --------- Start/Help ---------
@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text(
        "👋 Multi Admin Bot Ready!\n\n"
        "• /my_chats — Bot ke sabhi admin chats list karega (sirf owner)\n"
        "• /promote <user_id|@username> <chat_id> — Owner se admin promotion"
    )


if __name__ == "__main__":
    print("Bot started...")
    app.run()
