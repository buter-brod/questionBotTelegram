# -*- coding: utf-8 -*-
import ast

import config
import telebot
import re

bot = telebot.TeleBot(config.token)

class Filenames: pass
Filenames.questions = "questions"
Filenames.strings = "strings"
Filenames.known_users = "known_users"
Filenames.userPassword = "user_password"
Filenames.admin = "admin"


class Strings: pass
Strings.gameover = "gameover"
Strings.intro = "intro"
Strings.hiadmin = "hiadmin"
Strings.passwordChangedTxt = "passwordChangedTxt"
Strings.askPassword = "password"
Strings.restart = "restart"
Strings.wrongpass = "wrongpass"
Strings.restarted = "restarted"


class Commands: pass
Commands.setPassword = "password"
Commands.restart = "restart"


class Info: pass
info = Info()


class Question:
    def __init__(self, id, text):
        self.id = id
        self.text = text
        self.answers = {}


class Answer:
    def __init__(self, questionId, letter, nextQuestionId, text, replyTxt=None):
        self.letter = letter
        self.questionId = questionId
        self.nextQuestionId = nextQuestionId
        self.text = text
        self.replyTxt = replyTxt


def loadFromFile(filename):
    try:
        f = open(filename, "r", encoding="utf-8")
        contents = f.read()
        f.close()
        return contents
    except FileNotFoundError:
        f = open(filename, "w+")
        f.close()
        return ""


def writeToFile(filename, what):
    f = open(filename, "w+", encoding="utf-8")

    if isinstance(what, list):
        strList = [str(val) for val in what]
        f.writelines(strList)
    else:
        f.write(str(what))

    f.close()


def parseStrings():

    strings = loadFromFile(Filenames.strings)
    lines = strings.splitlines()

    for line in lines:
        colonPos = line.find(':')

        if 0 < colonPos < len(line) - 1:
            id = line[:colonPos]
            text = line[colonPos + 1:]
            info.strings[id] = text


def loadUsers():
    info.userPassword = loadFromFile(Filenames.userPassword)
    adminId = loadFromFile(Filenames.admin)
    info.adminId = int(adminId) if adminId != "" else 0

    known_usersIds = loadFromFile(Filenames.known_users)
    if known_usersIds != "":
        known_usersIds = known_usersIds.split(',')
        info.known_usersIds = [int(id) for id in known_usersIds]


def parseQuestions():
    qContents = loadFromFile(Filenames.questions)
    lines = qContents.splitlines()

    for line in lines:
        dotInd = line.find('.')
        lastInd = len(line) - 1

        if dotInd == -1 or dotInd == lastInd or dotInd == 0:
            continue

        prefix = line[:dotInd]

        matchQuestion = re.match("^[0-9]+$", prefix)
        matchAnswer = re.match('^([0-9]+)([a-z]?)([0-9]*)$', prefix)

        if not matchQuestion and not matchAnswer:
            continue

        text = line[dotInd + 1:lastInd + 1]

        if matchQuestion:
            qId = prefix
            question = Question(qId, text)
            info.questions[qId] = question
        else:
            sqBracketPos1 = line.find('[')
            sqBracketPos2 = line.find(']')
            postfix = ""
            if sqBracketPos1 != -1 and sqBracketPos1 != lastInd and sqBracketPos2 > sqBracketPos1 + 1:
                postfix = line[sqBracketPos1 + 1:sqBracketPos2]
                text = line[dotInd + 1:sqBracketPos1]

            qId = matchAnswer.group(1)
            letter = matchAnswer.group(2)
            nextQId = matchAnswer.group(3)

            question = info.questions.get(qId)
            if question is None:
                continue

            answer = Answer(qId, letter, nextQId, text, postfix)
            question.answers[letter] = answer


def sendRawTxt(chatId, text, kb):
    if kb:
        bot.send_message(chatId, text, reply_markup=kb)
    else:
        bot.send_message(chatId, text)


def sendString(chatId, strId, subst = {}, kb = None):

    finalStr = info.strings.get(strId)

    if finalStr is None:
        return

    if subst:
        finalStr = finalStr.format(**subst)

    sendRawTxt(chatId, finalStr, kb)


def gameOver(chatId):

    restartTxt = info.strings.get(Strings.restart)
    if restartTxt is None:
        restartTxt = Strings.restart

    keyboard = telebot.types.InlineKeyboardMarkup()
    callback_btn = telebot.types.InlineKeyboardButton(text=restartTxt, callback_data="restart")
    keyboard.add(callback_btn)

    sendString(chatId, Strings.gameover, kb=keyboard)


def ask(chatId, qID):
    question = info.questions.get(qID)
    if question is None:
        return

    answers = question.answers
    keyboard = None

    if answers:
        keyboard = telebot.types.InlineKeyboardMarkup()
        for _, answer in answers.items():
            idWithLetter = {'qId': answer.questionId, 'letter': answer.letter}
            callback_btn = telebot.types.InlineKeyboardButton(text=answer.text, callback_data=str(idWithLetter))
            keyboard.add(callback_btn)

    sendRawTxt(chatId, question.text, keyboard)

    if not answers:
        gameOver(chatId)


def setCurrentQuestionForChat(chatId, qID):

    info.currQuestionForChat[chatId] = qID
    ask(chatId, qID)


def ask_password(chatId):
    sendString(chatId, Strings.askPassword)


def send_welcome(chatId):
    sendString(chatId, Strings.intro)
    setCurrentQuestionForChat(chatId, "1")


def checkPassword(chatId, password):

    if password == config.admin_password:
        info.adminId = chatId
        writeToFile(Filenames.admin, info.adminId)
        return True

    elif password == info.userPassword:
        info.known_usersIds.append(chatId)
        writeToFile(Filenames.known_users, info.known_usersIds)
        return True

    return False


def setUserPassword(password):
    writeToFile(Filenames.userPassword, password)


def forgetUser(userId):
    if userId in info.known_usersIds:
        info.known_usersIds.remove(userId)
        writeToFile(Filenames.known_users, info.known_usersIds)

    if userId == info.adminId:
        info.adminId = 0
        writeToFile(Filenames.admin, info.adminId)


def isAdmin(id):
    return id == info.adminId


def isUser(id):
    return id in info.known_usersIds


def isUserOrAdmin(id):
    return isUser(id) or isAdmin(id)


def launchBot():

    info.strings = {}
    info.questions = {}

    info.currQuestionForChat = {}

    info.known_usersIds = []
    info.adminId = 0
    info.userPassword = ""

    loadUsers()
    parseQuestions()
    parseStrings()

    info.currQuestionForChat = {}


def greetAdmin(chatId):
    sendString(chatId, Strings.hiadmin)


def onUserStartBot(chatId):
    if isUserOrAdmin(chatId):
        if isAdmin(chatId):
            greetAdmin(chatId)

        send_welcome(chatId)
    else:
        ask_password(chatId)


def checkSetPasswordCommand(chatId, text):

    pInd = text.find(Commands.setPassword)
    if pInd == 0 and len(text) > len(Commands.setPassword) + 1:
        newPassword = text[len(Commands.setPassword) + 1:]
        info.userPassword = newPassword
        setUserPassword(newPassword)
        sendString(chatId, Strings.passwordChangedTxt, {'pass': newPassword})
        return True

    return False


def onTextMessage(chatId, text):

    if text == "forget":
        forgetUser(chatId)
        ask_password(chatId)
        return

    needPassword = not isUserOrAdmin(chatId)

    if isAdmin(chatId):
        checkSetPasswordCommand(chatId, text)

    if needPassword:
        passOk = checkPassword(chatId, text)

        if not passOk:
            sendString(chatId, Strings.wrongpass)
            ask_password(chatId)
        else:
            if isAdmin(chatId):
                greetAdmin(chatId)

            send_welcome(chatId)


def onButtonPress(chatId, callData):

    if not info.currQuestionForChat:
        sendString(chatId, Strings.restarted)

        needPassword = not isUserOrAdmin(chatId)

        if needPassword:
            ask_password(chatId)
        else:
            send_welcome(chatId)
        return

    if callData == Commands.restart:
        send_welcome(chatId)
        return


    idWithLetterDict = ast.literal_eval(callData)
    qIdFromMsg = idWithLetterDict['qId']
    letterFromMsg = idWithLetterDict['letter']

    questionIDRemembered = info.currQuestionForChat.get(chatId)

    if qIdFromMsg != questionIDRemembered:
        return

    currQuestion = info.questions.get(qIdFromMsg)
    answer = currQuestion.answers.get(letterFromMsg)

    if len(answer.replyTxt) > 0:
        bot.send_message(chatId, answer.replyTxt)

    setCurrentQuestionForChat(chatId, answer.nextQuestionId)


@bot.message_handler(commands=['start'])
def onStart(message):
    onUserStartBot(message.chat.id)


@bot.message_handler(content_types=["text"])
def onMessage(message):
    onTextMessage(message.chat.id, message.text)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    onButtonPress(call.message.chat.id, call.data)


if __name__ == '__main__':
    launchBot()
    bot.infinity_polling()
    print("done")

