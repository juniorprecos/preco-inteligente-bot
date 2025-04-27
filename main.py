import os
import json
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

# Configurações iniciais
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ['BOT_TOKEN']
ARQUIVO_PRODUTOS = 'produtos.json'
usuarios_premium = set()

# Funções para manipular produtos

def carregar_produtos():
    if not os.path.exists(ARQUIVO_PRODUTOS):
        return {}
    with open(ARQUIVO_PRODUTOS, 'r') as f:
        return json.load(f)

def salvar_produtos(produtos):
    with open(ARQUIVO_PRODUTOS, 'w') as f:
        json.dump(produtos, f)

# Função para iniciar navegador invisível

def iniciar_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    return driver

# Função para extrair preço

def extrair_preco(url):
    driver = iniciar_driver()
    try:
        driver.get(url)
        time.sleep(3)  # esperar a página carregar

        if 'mercadolivre.com' in url:
            elementos = driver.find_elements(By.CSS_SELECTOR, '[data-testid="price-value"]')
            if elementos:
                preco_texto = elementos[0].text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                return float(preco_texto)

        elif 'amazon' in url:
            try:
                preco_elemento = driver.find_element(By.ID, 'priceblock_ourprice')
            except:
                try:
                    preco_elemento = driver.find_element(By.ID, 'priceblock_dealprice')
                except:
                    preco_elemento = None
            if preco_elemento:
                preco_texto = preco_elemento.text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                return float(preco_texto)

        return None
    except Exception as e:
        print(f"Erro ao extrair preço: {e}")
        return None
    finally:
        driver.quit()

# Comandos do bot

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔔 Olá! Comandos disponíveis:\n"
        "/monitorar <link> <preço>\n"
        "/meusprodutos\n"
        "/remover <link>\n"
        "/limpar\n"
        "/meuid\n"
        "/verificaragora (forçar verificação)"
    )

def monitorar(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    produtos = carregar_produtos()
    if user_id not in produtos:
        produtos[user_id] = []

    if len(produtos[user_id]) >= 3 and user_id not in usuarios_premium:
        update.message.reply_text(
            "⚡ Limite gratuito atingido!\n\n"
            "Para monitorar mais produtos:\n"
            "✅ Pix: 61343395399\n"
            "✅ Banco: Nubank\n"
            "✅ Nome: Inácio Pereira\n"
            "✅ Valor: R$14,90\n"
            "📸 Envie o comprovante para liberar o Premium!"
        )
        return

    if len(context.args) < 2:
        update.message.reply_text("❌ Use: /monitorar <link> <preço>")
        return

    link = context.args[0]
    preco_alvo = float(context.args[1])
    produtos[user_id].append({'link': link, 'preco_alvo': preco_alvo})
    salvar_produtos(produtos)
    update.message.reply_text(f"✅ Produto salvo: {link}\n🎯 Preço alvo: R$ {preco_alvo:.2f}")

def meusprodutos(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    produtos = carregar_produtos()
    if user_id not in produtos or not produtos[user_id]:
        update.message.reply_text("Você não está monitorando nenhum produto.")
        return
    mensagem = "📋 Seus produtos monitorados:\n"
    for p in produtos[user_id]:
        mensagem += f"{p['link']} - R$ {p['preco_alvo']:.2f}\n"
    update.message.reply_text(mensagem)

def remover(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    produtos = carregar_produtos()
    if user_id not in produtos:
        update.message.reply_text("Você não tem produtos salvos.")
        return
    if len(context.args) == 0:
        update.message.reply_text("Envie o link que deseja remover.")
        return
    link = context.args[0]
    produtos[user_id] = [p for p in produtos[user_id] if p['link'] != link]
    salvar_produtos(produtos)
    update.message.reply_text("✅ Produto removido!")

def limpar(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    produtos = carregar_produtos()
    produtos[user_id] = []
    salvar_produtos(produtos)
    update.message.reply_text("🗑️ Todos os seus produtos foram apagados!")

def meuid(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    update.message.reply_text(f"🆔 Seu ID de usuário é: {user_id}")

def liberar(update: Update, context: CallbackContext):
    try:
        admin_id = 7789100233
        quem_mandou = update.message.chat_id
        if quem_mandou != admin_id:
            update.message.reply_text("Você não tem permissão para isso!")
            return
        if len(context.args) == 0:
            update.message.reply_text("Envie o ID do usuário para liberar.")
            return
        liberar_id = int(context.args[0])
        usuarios_premium.add(str(liberar_id))
        update.message.reply_text(f"✅ Usuário {liberar_id} foi liberado como Premium!")
    except:
        update.message.reply_text("Erro ao tentar liberar o usuário.")

def verificaragora(update: Update, context: CallbackContext):
    checar_precos()
    update.message.reply_text("🔎 Verificação concluída!")

def checar_precos():
    produtos = carregar_produtos()
    for user_id, lista in produtos.items():
        for produto in lista.copy():
            preco_atual = extrair_preco(produto['link'])
            if preco_atual is not None and preco_atual <= produto['preco_alvo']:
                try:
                    updater.bot.send_message(chat_id=int(user_id),
                        text=f"🎯 O preço caiu!\n{produto['link']}\nPreço atual: R$ {preco_atual:.2f}")
                    lista.remove(produto)
                except Exception as e:
                    print(f"Erro enviando mensagem: {e}")
    salvar_produtos(produtos)

# Inicializar o bot
updater = Updater(TOKEN)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("monitorar", monitorar))
dp.add_handler(CommandHandler("meusprodutos", meusprodutos))
dp.add_handler(CommandHandler("remover", remover))
dp.add_handler(CommandHandler("limpar", limpar))
dp.add_handler(CommandHandler("meuid", meuid))
dp.add_handler(CommandHandler("liberar", liberar))
dp.add_handler(CommandHandler("verificaragora", verificaragora))

scheduler = BackgroundScheduler()
scheduler.add_job(checar_precos, 'interval', hours=1)
scheduler.start()

print("Bot iniciado com sucesso!")
updater.start_polling()
updater.idle()
