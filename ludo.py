import telebot
import json
import os
from flask import Flask
import threading

TOKEN = '9121568976:AAFoPvMkR_jhOmn6CH1sv-FrzDVPeCysOpI'
bot = telebot.TeleBot(TOKEN)

DB_FILE = "usuarios_ludo.json"

def cargar_bd():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except:
            return {}
    return {}

def guardar_bd():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios_db, f, ensure_ascii=False, indent=4)

usuarios_db = cargar_bd()
mesas_activas = {}

@bot.message_handler(commands=['lanzar'])
def lanzar(message):
    chat_id = message.chat.id
    if message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message, "🎲 ¡Desplegando las 3 mesas de juego!")
        
        # Mesa 1vs1
        m1 = bot.send_message(chat_id, "🎲 **1vs1 - Mesa #1**\n\n💰 Apuesta: 1.700 Bs\n🏆 Premio: 2.900 Bs\n\n👥 **Jugadores:**\n1. ---\n2. ---\n\n¿QUIÉN JUEGA?", reply_markup=crear_botones("1vs1"), parse_mode="Markdown")
        mesas_activas[m1.message_id] = {"tipo": "1vs1", "jugadores": [], "max": 2}
        
        # Mesa 4P
        m2 = bot.send_message(chat_id, "🎲 **Clásica 4P - Mesa #1**\n\n💰 Apuesta: 1.000 Bs\n🥇 1er: 2.500 Bs | 🥈 2do: 1.000 Bs\n\n👥 **Jugadores:**\n1. ---\n2. ---\n3. ---\n4. ---\n\n¿QUIÉN JUEGA?", reply_markup=crear_botones("4p"), parse_mode="Markdown")
        mesas_activas[m2.message_id] = {"tipo": "4p", "jugadores": [], "max": 4}

        # Mesa 2vs2
        m3 = bot.send_message(chat_id, "🎲 **2vs2 Dupla - Mesa #1**\n\n💰 Apuesta: 1.900 Bs\n🏆 Premio: 7.100 Bs\n\n👥 **Pareja 1:**\n1. ---\n2. ---\n👥 **Pareja 2:**\n1. ---\n2. ---\n\n¿QUIÉN JUEGA?", reply_markup=crear_botones("2vs2"), parse_mode="Markdown")
        mesas_activas[m3.message_id] = {"tipo": "2vs2", "p1": [], "p2": []}

def crear_botones(tipo):
    markup = telebot.types.InlineKeyboardMarkup()
    if tipo == "2vs2":
        markup.add(
            telebot.types.InlineKeyboardButton("👥 Pareja 1", callback_data="unirse_p1"),
            telebot.types.InlineKeyboardButton("👥 Pareja 2", callback_data="unirse_p2")
        )
        markup.add(telebot.types.InlineKeyboardButton("🚪 Salirse", callback_data="salirse"))
    else:
        markup.add(
            telebot.types.InlineKeyboardButton("✅ Unirme", callback_data="unirse"),
            telebot.types.InlineKeyboardButton("🚪 Salirse", callback_data="salirse")
        )
    return markup

@bot.message_handler(commands=['start', 'saldo'])
def saldo(message):
    uid = message.from_user.id
    uname = message.from_user.username or "Jugador"
    if uid not in usuarios_db:
        usuarios_db[uid] = {"username": uname, "saldo": 10000}
        guardar_bd()
    bot.reply_to(message, f"💰 Tu saldo actual es: {usuarios_db[uid]['saldo']}Bs")

@bot.callback_query_handler(func=lambda call: True)
def botones(call):
    mid = call.message.message_id
    uid = call.from_user.id
    uname = call.from_user.username or "Jugador"

    if uid not in usuarios_db:
        usuarios_db[uid] = {"username": uname, "saldo": 10000}
        guardar_bd()

    if mid not in mesas_activas:
        bot.answer_callback_query(call.id, "Mesa expirada. Usa /lanzar", show_alert=True)
        return

    mesa = mesas_activas[mid]
    tipo = mesa["tipo"]
    
    if tipo == "2vs2":
        costo = 1900
        p1 = mesa["p1"]
        p2 = mesa["p2"]
        
        if call.data == "unirse_p1":
            if uname in p1 or uname in p2:
                bot.answer_callback_query(call.id, "Ya estás anotado.", show_alert=True)
            elif usuarios_db[uid]["saldo"] < costo:
                bot.answer_callback_query(call.id, "Saldo insuficiente (1.900Bs).", show_alert=True)
            elif len(p1) < 2:
                usuarios_db[uid]["saldo"] -= costo
                guardar_bd()
                p1.append(uname)
                actualizar_mesa_2vs2(call)
                bot.answer_callback_query(call.id, "¡Te uniste a Pareja 1!")
        elif call.data == "unirse_p2":
            if uname in p1 or uname in p2:
                bot.answer_callback_query(call.id, "Ya estás anotado.", show_alert=True)
            elif usuarios_db[uid]["saldo"] < costo:
                bot.answer_callback_query(call.id, "Saldo insuficiente (1.900Bs).", show_alert=True)
            elif len(p2) < 2:
                usuarios_db[uid]["saldo"] -= costo
                guardar_bd()
                p2.append(uname)
                actualizar_mesa_2vs2(call)
                bot.answer_callback_query(call.id, "¡Te uniste a Pareja 2!")
        elif call.data == "salirse":
            if uname in p1:
                p1.remove(uname)
                usuarios_db[uid]["saldo"] += costo
                guardar_bd()
                actualizar_mesa_2vs2(call)
                bot.answer_callback_query(call.id, "Saliste. Reembolsado.")
            elif uname in p2:
                p2.remove(uname)
                usuarios_db[uid]["saldo"] += costo
                guardar_bd()
                actualizar_mesa_2vs2(call)
                bot.answer_callback_query(call.id, "Saliste. Reembolsado.")
            else:
                bot.answer_callback_query(call.id, "No estás en esta mesa.", show_alert=True)
    else:
        costo = 1700 if tipo == "1vs1" else 1000
        jugadores = mesa["jugadores"]
        max_j = mesa["max"]
        
        if call.data == "unirse":
            if uname in jugadores:
                bot.answer_callback_query(call.id, "Ya estás anotado.", show_alert=True)
            elif usuarios_db[uid]["saldo"] < costo:
                bot.answer_callback_query(call.id, f"Saldo insuficiente ({costo}Bs).", show_alert=True)
            elif len(jugadores) < max_j:
                usuarios_db[uid]["saldo"] -= costo
                guardar_bd()
                jugadores.append(uname)
                actualizar_mesa_normal(call, tipo, jugadores, max_j)
                bot.answer_callback_query(call.id, "¡Te uniste con éxito!")
        elif call.data == "salirse":
            if uname in jugadores:
                jugadores.remove(uname)
                usuarios_db[uid]["saldo"] += costo
                guardar_bd()
                actualizar_mesa_normal(call, tipo, jugadores, max_j)
                bot.answer_callback_query(call.id, "Saliste. Reembolsado.")
            else:
                bot.answer_callback_query(call.id, "No estás en esta mesa.", show_alert=True)

def actualizar_mesa_2vs2(call):
    mid = call.message.message_id
    mesa = mesas_activas[mid]
    p1 = mesa["p1"]
    p2 = mesa["p2"]
    s1_1 = f"@{p1[0]}" if len(p1) > 0 else "---"
    s1_2 = f"@{p1[1]}" if len(p1) > 1 else "---"
    s2_1 = f"@{p2[0]}" if len(p2) > 0 else "---"
    s2_2 = f"@{p2[1]}" if len(p2) > 1 else "---"
    
    completa = (len(p1) == 2 and len(p2) == 2)
    texto = f"🎲 **2vs2 Dupla - Mesa #1**\n\n💰 Apuesta: 1.900 Bs\n🏆 Premio: 7.100 Bs\n\n👥 **Pareja 1:**\n1. {s1_1}\n2. {s1_2}\n👥 **Pareja 2:**\n1. {s2_1}\n2. {s2_2}\n\n"
    texto += "✅ **(COMPLETA)**" if completa else "¿QUIÉN JUEGA?"
    markup = None if completa else call.message.reply_markup
    bot.edit_message_text(texto, call.message.chat.id, mid, reply_markup=markup, parse_mode="Markdown")

def actualizar_mesa_normal(call, tipo, jugadores, max_j):
    mid = call.message.message_id
    titulo = "1vs1 - Mesa #1" if tipo == "1vs1" else "Clásica 4P - Mesa #1"
    apuesta = "1.700 Bs" if tipo == "1vs1" else "1.000 Bs"
    premio = "2.900 Bs" if tipo == "1vs1" else "1er: 2.500 Bs | 2do: 1.000 Bs"
    
    slots = [f"@{jugadores[i]}" if i < len(jugadores) else "---" for i in range(max_j)]
    completa = len(jugadores) == max_j
    
    texto = f"🎲 **{titulo}**\n\n💰 Apuesta: {apuesta}\n🏆 Premio: {premio}\n\n👥 **Jugadores:**\n"
    for i, s in enumerate(slots, 1):
        texto += f"{i}. {s}\n"
    texto += "\n" + ("✅ **(COMPLETA)**" if completa else "¿QUIÉN JUEGA?")
    markup = None if completa else call.message.reply_markup
    bot.edit_message_text(texto, call.message.chat.id, mid, reply_markup=markup, parse_mode="Markdown")

# Servidor web integrado para la nube (Flask)
app = Flask('')

@app.route('/')
def home():
    return "Bot de Ludo Activo 24/7"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.start()
    
    print("Iniciando bot de Telegram en la nube...")
    bot.infinity_polling(none_stop=True)
