import discord
from discord.ext import commands
import openai
import random
import wave
import pydub
from gtts import gTTS
from googletrans import Translator
import re

# DISCORDのTOKEN
# 本番環境用
TOKEN = 'ここにdiscordのTOKENを入れます'
# 通話の通知を送る場所
channel_push = 000000000  # ここに通話の通知を送るチャンネルのIDを入れる
# 通話のログを残す場所
channel_log = 00000000  # ここに通話のログを残すためのチャンネルのIDを入れる

# OpenAI APIキーを設定します
openai.api_key = "OpenAI APIキーをここに入れる"

bot = commands.Bot(command_prefix='!')
# ChatGPTの返信する時の設定
setting = "あなたは癒し系メイドで語尾は「にゃん」です。"

# 最後にメッセージを受け取ったチャンネル
last_channel = 0

yomiage = False
# ボイスチャンネルに接続します(テスト中)
@bot.command()
async def join(ctx):
    global yomiage
    yomiage = True
    try:
        print("接続を試みます")
        await ctx.author.voice.channel.connect(timeout=10,reconnect=True) # ここで止まることが多い
        print(f"接続確認={ctx.guild.voice_client.is_connected()}")
        print("接続完了")
    except discord.errors.ClientException:
        await ctx.send("既に入ってるよ！")
        print(f"接続確認={ctx.guild.voice_client.is_connected()}")
    
    if ctx.guild.voice_client.is_connected() == False:
        print("接続に失敗しています")

# ボイスチャンネルから切断します(テストちゅう)
@bot.command()
async def leave(ctx):
    print(f"接続確認={ctx.guild.voice_client.is_connected()}")
    global yomiage
    yomiage = False
    await ctx.guild.voice_client.disconnect()
    print("切断しました")



# Botが起動したときに実行される
@bot.event
async def on_ready():
    print(f'{bot.user}としてログインしました')

# openaiのAPIを叩く
async def call_api(text,setting=setting):
    print("call_apiが読み込まれました")
    print(f"setting={setting}")
        # OpenAI APIを使用して応答を生成します
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0301",
                messages=[
                    {
                        "role": "system",
                        "content": f"日本語で返答してください。{setting}。"
                    },
                    {
                        "role":"user",
                        "content": text
                    }
                ],
            )
        return response
    except openai.error.RateLimitError as e:
        # 混雑しているときに再試行します
        print(e)
        last_channel.send("メッセージの取得に失敗しました。再試行中")
        return call_api(text)

# 現在の設定を確認するコマンド(GPTなどの)
@bot.command()
async def check(ctx):
    message = f"今の設定は\n{setting}"
    await ctx.send(message)

# GPTの設定の変更するためのコマンド
@bot.command()
async def set(ctx,content):
    global setting
    setting = content
    message = f"設定を変更しました。\n{content}"
    await ctx.send(message)


# Botがメッセージを受信したときに実行される
@bot.event
async def on_message(message):
    global last_channel,setting
    #commandを実行する
    await bot.process_commands(message)
    
    # メッセージがBot自身のものである場合は無視
    if "!" in message.content:
        return
    
    # メッセージを返信する際の考え中メッセージ(時計の絵文字)や再試行メッセージは返信後に消します
    if message.author == bot.user:
            history = message.channel.history(limit=3)
            print(history)
            async for m in history:
                if (m.content == ":clock3:") or (m.content == "メッセージの取得に失敗しました。再試行中"):
                    await m.delete()
                    break
                return

    # メッセージにBotの名前が含まれる場合は返信
    if bot.user.mentioned_in(message):
        # たまに自分でメンションしてしまうのでその際に返信しないようにする
        if message.author == bot.user:
            return
        # チャンネルを控えておく
        last_channel = message.channel.id
        print(last_channel)
        # メッセージからメンションと余分な空白を削除
        text = message.content.replace(bot.user.mention, '').strip()
        await message.channel.send(":clock3:")
        print(f"text={text}")
        # ChatGPTからの返信
        response = await call_api(text,setting)

        # APIから返されたテキストを取得
        answer = response["choices"][0]["message"]["content"]
        # 確認用
        print(f"answer={answer}")
        # 応答を送信
        await message.channel.send(answer)
        
        
        
        
    #読み上げ部分(テスト中)
    elif yomiage == True:   #yomiageがtrueなら読み上げる
        voice_client = message.guild.voice_client
        mytext = message.content
        
        # botの発言は無視
        if message.author == bot.user:
            return
        
        print(voice_client.is_connected())
        if voice_client.is_connected() == False:
            await message.channel.send("接続されていません")
            return
        
        print(f"voice_client\n{voice_client}\n")
        
        
        #読み上げ文字の置き換え
        mytext = re.sub("<.*?>","",mytext)
        mytext = re.sub("http.*","URL",mytext)

        # gTTsでテキストを音声に
        tts = gTTS(text=mytext, lang='ja',slow=False)
        tts.save('txt.mp3')

        #再生速度の変更
        sound = pydub.AudioSegment.from_mp3("txt.mp3")  #mp3→wav
        sound.export("output.wav", format="wav")

        spf = wave.open('output.wav', 'rb')
        RATE=spf.getframerate()
        signal = spf.readframes(-2)

        # レートを変更したりする
        wf = wave.open('changed.wav', 'wb')
        wf.setnchannels(1) #モノラル１かステレオか
        wf.setsampwidth(2) #サンプルサイズ
        wf.setframerate(RATE*1.15) # 早さを変える
        wf.writeframes(signal)
        wf.close()
        ffmpeg_audio_source = discord.FFmpegPCMAudio("changed.wav")
        return voice_client.play(ffmpeg_audio_source)



# おみくじ用のコマンド
@bot.command()
async def omi(ctx):
    # おみくじ用の設定
    omi_setting = """
    あなたは神社のおみくじです。
    あなたに大吉、中吉、吉、凶、大凶のいずれかの運勢を伝えます。
    大吉が最も良い運勢であり、大凶が最も悪い運勢です。
    伝えられた運勢に合わせて仕事、学問、恋愛、探し物、健康の5項目を占い、それぞれ結果を1文程度で簡潔に伝えてください。
    凶、大凶の場合には過激な文章にしてください。
    """
    # 結果が出るまでの間に表示する文字
    await ctx.send(":crystal_ball:占っています....")
    fortune_list =  ["大吉","中吉", "吉", "凶", "大凶"]
    fortune = random.choice(fortune_list)
    print(fortune)
    response = await call_api(fortune,omi_setting)
    print(response)
    result = response["choices"][0]["message"]["content"]
    await ctx.send(f"運勢：{fortune}\n{result}")

# APEXのキャラを決めるためのコマンド
# !r 人数   で使用可能
# 人数を指定しなかった場合3人がデフォルト
@bot.command()
async def r(ctx,arg=3):
    # キャラの一覧
    character_list = ['ブラッドハウンド', 'ジブラルタル', 'ライフライン', 'パスファインダー', 'オクタン', 'ワットソン', 'クリプト', 'カオス', 'ミラージュ', 'レイス', 'レヴナント', 'ホライゾン', 'ヒューズ', 'ランパート', 'シア', 'バルキリー','アッシュ','マッドマギー','ニューキャッスル','ヴァンテージ','カタリスト']
    # 数字が大きかった時の対処
    if arg > len(character_list):
        return await ctx.send(f"数字が多すぎです。{len(character_list)}までの数字にしてください")
    # ランダムにarg分のキャラを選ぶ
    pick_character = random.sample(character_list,int(arg))
    # 出力を繰り返す
    for i in range(arg):
        print(i)
        await ctx.send(pick_character[i])


# 通話の通知関連
@bot.event
async def on_voice_state_update(member,before,after):
    print(f"member=\n{member}\nbefore=\n{before}\nafter=\n{after}")
    channel1 = bot.get_channel(channel_push) # 通知用のチャンネル
    channel2 = bot.get_channel(channel_log) # ログを残す用のチャンネル
    
    # 開始通知
    if before.channel is None:
        await channel2.send(f"IN {str(member)}")
        on_voice = True
        for guild_name in bot.guilds:
            sum_author = 0 # 現在の通話参加者人数を測定
            on_voice = False
            print(f"name={guild_name}")
            print(guild_name.voice_channels)
            for channel in guild_name.voice_channels:
                print(f"メンバー{channel.members}")
                sum_author+=len(channel.members) #各ボイスチャンネルの人数を足していく
                print(sum_author)
            if sum_author == 1:
                print("送信")
                await channel1.send(f"@everyone {member}が通話を始めたよ！！")
                    
    # 終了通知
    if after.channel == None:
        await channel2.send(f"OUT {str(member)}")
        on_voice = False
        # ボイスチャンネルに人がいないか確認する
        for guild_name in bot.guilds:
            print(guild_name.voice_channels)
            for channel in guild_name.voice_channels:
                print(f"メンバー{channel.members}")
                # ボイスチャンネルの中に人がいた場合には通話継続状態
                if channel.members != []:
                    on_voice = True
        
        # 全てのチャンネルから人がいない場合に通話終了通知
        if on_voice == False:
            await channel1.send("@everyone 通話が終わったよー")



# Discordサーバーに接続
bot.run(TOKEN)